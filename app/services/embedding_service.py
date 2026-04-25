import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
from app.config import settings

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT_SECONDS = 60.0

# Gemini batchEmbedContents accepts up to 100 items per request
BATCH_SIZE = 100

# Retry config for transient errors (429, 503, timeouts)
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


def _build_batch_payload(texts: list[str], task_type: str) -> dict:
    """Build the payload for the batchEmbedContents API."""
    return {
        "requests": [
            {
                "model": f"models/{EMBEDDING_MODEL}",
                "content": {"parts": [{"text": text}]},
                "taskType": task_type,
                "outputDimensionality": EMBEDDING_DIMENSIONS,
            }
            for text in texts
        ]
    }


def _batch_embed_sync(texts: list[str], task_type: str) -> list[list[float]]:
    """Embed a batch of up to 100 texts in a single HTTP call (sync)."""
    url = f"{BASE_URL}/{EMBEDDING_MODEL}:batchEmbedContents?key={settings.GEMINI_API_KEY}"
    payload = _build_batch_payload(texts, task_type)

    for attempt in range(MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                return [e["values"] for e in response.json()["embeddings"]]
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            # Retry on 429 (rate limit) or 5xx server errors
            is_retryable = isinstance(exc, httpx.RequestError) or (
                isinstance(exc, httpx.HTTPStatusError)
                and exc.response.status_code in (429, 500, 503)
            )
            if is_retryable and attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                time.sleep(delay)
                continue
            raise


async def _batch_embed_async(texts: list[str], task_type: str) -> list[list[float]]:
    """Embed a batch of up to 100 texts in a single HTTP call (async)."""
    url = f"{BASE_URL}/{EMBEDDING_MODEL}:batchEmbedContents?key={settings.GEMINI_API_KEY}"
    payload = _build_batch_payload(texts, task_type)

    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return [e["values"] for e in response.json()["embeddings"]]
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            is_retryable = isinstance(exc, httpx.RequestError) or (
                isinstance(exc, httpx.HTTPStatusError)
                and exc.response.status_code in (429, 500, 503)
            )
            if is_retryable and attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                await asyncio.sleep(delay)
                continue
            raise


# ── Public API (unchanged signatures) ─────────────────────────────────────────


async def get_embedding(text: str) -> list[float]:
    """Get embedding for a single query text (used by the search/query route)."""
    results = await _batch_embed_async([text], "RETRIEVAL_QUERY")
    return results[0]


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Get embeddings for multiple texts using batchEmbedContents.

    Splits into sub-batches of BATCH_SIZE (100) and fires them concurrently
    with asyncio.gather for maximum throughput.

    162 chunks → 2 HTTP calls instead of 162.
    """
    if not texts:
        return []

    # Split into sub-batches of BATCH_SIZE
    sub_batches = [texts[i : i + BATCH_SIZE] for i in range(0, len(texts), BATCH_SIZE)]

    # Fire all sub-batch requests concurrently
    results = await asyncio.gather(
        *[_batch_embed_async(batch, "RETRIEVAL_DOCUMENT") for batch in sub_batches]
    )

    # Flatten: [[emb1, emb2, ...], [emb101, emb102, ...]] → [emb1, emb2, ..., emb101, ...]
    return [emb for batch_result in results for emb in batch_result]


def get_embeddings_batch_sync(texts: list[str]) -> list[list[float]]:
    """Sync version for Celery workers — uses batchEmbedContents with
    ThreadPoolExecutor for concurrent sub-batch requests.

    162 chunks → 2 HTTP calls fired in parallel threads.
    """
    if not texts:
        return []

    sub_batches = [texts[i : i + BATCH_SIZE] for i in range(0, len(texts), BATCH_SIZE)]

    if len(sub_batches) == 1:
        # Single batch — no thread overhead needed
        return _batch_embed_sync(sub_batches[0], "RETRIEVAL_DOCUMENT")

    # Multiple sub-batches — fire them in parallel threads
    all_results: list[list[list[float]]] = [[] for _ in sub_batches]

    def _embed_batch(idx: int, batch: list[str]) -> tuple[int, list[list[float]]]:
        return idx, _batch_embed_sync(batch, "RETRIEVAL_DOCUMENT")

    with ThreadPoolExecutor(max_workers=len(sub_batches)) as pool:
        futures = [pool.submit(_embed_batch, i, b) for i, b in enumerate(sub_batches)]
        for future in futures:
            idx, result = future.result()
            all_results[idx] = result

    return [emb for batch_result in all_results for emb in batch_result]
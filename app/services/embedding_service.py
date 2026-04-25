import asyncio
import logging
import time

import httpx
from app.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT_SECONDS = 60.0

# ── Tuned for Gemini free tier (1500 RPM, but tight token-per-minute caps) ────
# Smaller batches avoid 429s; sequential dispatch with a pause between batches
# keeps us well within rate limits while still being ~8x faster than one-by-one.
BATCH_SIZE = 20
PAUSE_BETWEEN_BATCHES = 0.5  # seconds — gentle pacing to avoid 429s

# Retry config — longer waits for 429 to let the quota window reset
MAX_RETRIES = 5
RETRY_BASE_DELAY = 2.0  # seconds; doubles each attempt: 2s, 4s, 8s, 16s, 32s


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
    """Embed a batch of texts in a single HTTP call (sync).
    Retries with exponential backoff on 429 / 5xx / network errors.
    """
    url = f"{BASE_URL}/{EMBEDDING_MODEL}:batchEmbedContents?key={settings.GEMINI_API_KEY}"
    payload = _build_batch_payload(texts, task_type)

    for attempt in range(MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                return [e["values"] for e in response.json()["embeddings"]]
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            is_retryable = isinstance(exc, httpx.RequestError) or (
                isinstance(exc, httpx.HTTPStatusError)
                and exc.response.status_code in (429, 500, 503)
            )
            if is_retryable and attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Batch embed attempt %d/%d failed (%s), retrying in %.1fs",
                    attempt + 1, MAX_RETRIES, type(exc).__name__, delay,
                )
                time.sleep(delay)
                continue
            raise


async def _batch_embed_async(texts: list[str], task_type: str) -> list[list[float]]:
    """Embed a batch of texts in a single HTTP call (async).
    Retries with exponential backoff on 429 / 5xx / network errors.
    """
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
                logger.warning(
                    "Batch embed attempt %d/%d failed (%s), retrying in %.1fs",
                    attempt + 1, MAX_RETRIES, type(exc).__name__, delay,
                )
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

    Sends sub-batches sequentially with a small pause between each to
    stay within Gemini free-tier rate limits.

    162 chunks → 9 HTTP calls (batches of 20) instead of 162 individual calls.
    """
    if not texts:
        return []

    sub_batches = [texts[i : i + BATCH_SIZE] for i in range(0, len(texts), BATCH_SIZE)]
    all_embeddings: list[list[float]] = []

    for i, batch in enumerate(sub_batches):
        result = await _batch_embed_async(batch, "RETRIEVAL_DOCUMENT")
        all_embeddings.extend(result)
        # Pause between batches (skip after the last one)
        if i < len(sub_batches) - 1:
            await asyncio.sleep(PAUSE_BETWEEN_BATCHES)

    return all_embeddings


def get_embeddings_batch_sync(texts: list[str]) -> list[list[float]]:
    """Sync version for Celery workers — uses batchEmbedContents.

    Sends sub-batches sequentially with a pause between each to respect
    Gemini free-tier rate limits.

    162 chunks → 9 HTTP calls (batches of 20) instead of 162 individual calls.
    """
    if not texts:
        return []

    sub_batches = [texts[i : i + BATCH_SIZE] for i in range(0, len(texts), BATCH_SIZE)]
    all_embeddings: list[list[float]] = []

    for i, batch in enumerate(sub_batches):
        result = _batch_embed_sync(batch, "RETRIEVAL_DOCUMENT")
        all_embeddings.extend(result)
        logger.info("Embedded batch %d/%d (%d texts)", i + 1, len(sub_batches), len(batch))
        # Pause between batches (skip after the last one)
        if i < len(sub_batches) - 1:
            time.sleep(PAUSE_BETWEEN_BATCHES)

    return all_embeddings
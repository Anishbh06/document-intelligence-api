import httpx
from app.config import settings

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT_SECONDS = 30.0


async def _get_embedding_rest(text: str, task_type: str) -> list[float]:
    url = f"{BASE_URL}/{EMBEDDING_MODEL}:embedContent?key={settings.GEMINI_API_KEY}"
    payload = {
        "model": f"models/{EMBEDDING_MODEL}",
        "content": {"parts": [{"text": text}]},
        "taskType": task_type,
        "outputDimensionality": EMBEDDING_DIMENSIONS,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()["embedding"]["values"]


def _get_embedding_rest_sync(text: str, task_type: str) -> list[float]:
    url = f"{BASE_URL}/{EMBEDDING_MODEL}:embedContent?key={settings.GEMINI_API_KEY}"
    payload = {
        "model": f"models/{EMBEDDING_MODEL}",
        "content": {"parts": [{"text": text}]},
        "taskType": task_type,
        "outputDimensionality": EMBEDDING_DIMENSIONS,
    }
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        return response.json()["embedding"]["values"]


async def get_embedding(text: str) -> list[float]:
    return await _get_embedding_rest(text, "RETRIEVAL_QUERY")


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    embeddings = []
    for text in texts:
        embedding = await _get_embedding_rest(text, "RETRIEVAL_DOCUMENT")
        embeddings.append(embedding)
    return embeddings


def get_embeddings_batch_sync(texts: list[str]) -> list[list[float]]:
    embeddings = []
    for text in texts:
        embeddings.append(_get_embedding_rest_sync(text, "RETRIEVAL_DOCUMENT"))
    return embeddings
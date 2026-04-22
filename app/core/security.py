import secrets

from fastapi import Header

from app.config import settings
from app.core.exceptions import APIError


async def require_api_key(x_api_key: str = Header(default="")) -> None:
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.GEMINI_API_KEY):
        raise APIError(status_code=401, code="unauthorized", message="Invalid API key")

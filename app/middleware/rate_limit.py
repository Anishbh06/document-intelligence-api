import asyncio
import time

import redis.asyncio as aioredis
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings

EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/api/v1/auth/login", "/api/v1/auth/register"}


def _make_redis_client() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-backed sliding-window rate limiter.
    Falls back to in-process deque if Redis is unavailable so the API keeps
    running even when the cache layer is down.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self._redis: aioredis.Redis | None = None
        self._fallback: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = _make_redis_client()
        return self._redis

    async def _check_redis(self, key: str) -> tuple[bool, int]:
        """Returns (is_limited, retry_after_seconds). Uses atomic INCR + EXPIRE."""
        r = self._get_redis()
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        count, ttl = await pipe.execute()

        if count == 1 or ttl == -1:
            await r.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS)
            ttl = settings.RATE_LIMIT_WINDOW_SECONDS

        limited = count > settings.RATE_LIMIT_REQUESTS
        return limited, max(int(ttl), 1)

    async def _check_fallback(self, key: str) -> tuple[bool, int]:
        """In-memory sliding window used when Redis is down."""
        async with self._lock:
            now = time.time()
            window = settings.RATE_LIMIT_WINDOW_SECONDS
            history = self._fallback.setdefault(key, [])
            self._fallback[key] = [t for t in history if t > now - window]
            self._fallback[key].append(now)
            limited = len(self._fallback[key]) > settings.RATE_LIMIT_REQUESTS
            return limited, window

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"rate:{client_ip}"

        try:
            limited, retry_after = await self._check_redis(key)
        except Exception:
            limited, retry_after = await self._check_fallback(key)

        if limited:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limited", "message": "Too many requests. Slow down."}},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)

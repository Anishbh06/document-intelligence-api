import asyncio
import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in {"/health", "/docs", "/openapi.json", "/redoc"}:
            return await call_next(request)

        now = time.time()
        key = f"{request.client.host if request.client else 'unknown'}:{request.url.path}"
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        limit = settings.RATE_LIMIT_REQUESTS

        async with self._lock:
            history = self._requests[key]
            while history and history[0] <= now - window:
                history.popleft()
            if len(history) >= limit:
                return JSONResponse(
                    status_code=429,
                    content={"error": {"code": "rate_limited", "message": "Too many requests"}},
                )
            history.append(now)

        return await call_next(request)

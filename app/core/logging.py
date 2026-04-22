import json
import logging
import time
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(message)s",
    )


def log_event(logger_name: str, event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logging.getLogger(logger_name).info(json.dumps(payload, default=str))


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log_event(
            "api.request",
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else "unknown",
        )
        return response

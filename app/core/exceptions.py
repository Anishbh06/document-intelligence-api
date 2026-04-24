from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import log_event


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        """Convert Pydantic 422 detail list → our standard {"error": {...}} format."""
        messages = []
        for error in exc.errors():
            msg = error.get("msg", "Validation error")
            # Strip passlib/pydantic prefix like "Value error, "
            msg = msg.removeprefix("Value error, ")
            field = " → ".join(str(loc) for loc in error.get("loc", []) if loc != "body")
            messages.append(f"{field}: {msg}" if field else msg)
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": "; ".join(messages)}},
        )

    @app.exception_handler(APIError)
    async def api_error_handler(_: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        log_event(
            "api.error",
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "Internal server error"}},
        )


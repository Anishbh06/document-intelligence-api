from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import jobs, query, upload
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.db.init_db import init_db
from app.middleware.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await init_db()
    yield


app = FastAPI(
    title="Document Intelligence API",
    description="RAG-powered document Q&A API - async processing with Celery and Redis",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)

app.include_router(upload.router, prefix="/api/v1", tags=["Documents"])
app.include_router(query.router, prefix="/api/v1", tags=["Query"])
app.include_router(jobs.router, prefix="/api/v1", tags=["Jobs"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}
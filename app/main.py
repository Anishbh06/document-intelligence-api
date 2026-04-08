from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import upload, query
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Document Intelligence API",
    description="RAG-powered document Q&A API using FastAPI and pgvector",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(upload.router, prefix="/api/v1", tags=["Documents"])
app.include_router(query.router, prefix="/api/v1", tags=["Query"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
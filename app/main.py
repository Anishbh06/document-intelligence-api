import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import jobs, query, upload, auth
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
    description="RAG-powered document Q&A API — async processing with Celery, Redis, and JWT auth",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
# ALLOWED_ORIGINS env var: comma-separated list of origins.
# e.g.  ALLOWED_ORIGINS=https://my-app.vercel.app,https://custom-domain.com
# Falls back to localhost only when not set (safe default).
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)

app.include_router(auth.router,   prefix="/api/v1", tags=["Auth"])
app.include_router(upload.router, prefix="/api/v1", tags=["Documents"])
app.include_router(query.router,  prefix="/api/v1", tags=["Query"])
app.include_router(jobs.router,   prefix="/api/v1", tags=["Jobs"])


@app.on_event("startup")
async def on_startup():
    from app.db.session import engine
    from app.models.user import User
    from sqlalchemy import inspect
    import logging

    logger = logging.getLogger(__name__)
    
    # Force a check if tables exist
    def check_and_create():
        inspector = inspect(engine.sync_engine)
        if not inspector.has_table("users"):
            logger.warning("🚀 Table 'users' missing! Forcing creation...")
            from app.db.base import Base
            Base.metadata.create_all(bind=engine.sync_engine)
            logger.info("✅ Database tables created successfully.")
        else:
            logger.info("✅ Database tables verified.")

    from anyio import to_thread
    await to_thread.run_sync(check_and_create)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "3.0.0"}
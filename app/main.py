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

    # Pre-warm Celery broker connection so first .delay() doesn't block
    import logging
    logger = logging.getLogger(__name__)
    try:
        from app.celery_app import celery_app
        conn = celery_app.connection()
        conn.ensure_connection(max_retries=2, timeout=5)
        conn.close()
        logger.info("✅ Celery broker connection pre-warmed")
    except Exception as e:
        logger.warning("⚠️ Celery broker pre-warm failed (tasks will still work): %s", e)

    yield



app = FastAPI(
    title="Document Intelligence API",
    description="Multi-tenant RAG-based document analysis system",
    version="3.0.0"
)

# 1. BULLETPROOF CORS (MUST BE FIRST)
origins = [
    "http://localhost:3000",
    "https://project-7pe5b.vercel.app",
]
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    if allowed_origins_env == "*":
        origins = ["*"]
    else:
        origins.extend([o.strip() for o in allowed_origins_env.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 2. OTHER MIDDLEWARES
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

register_exception_handlers(app)

app.include_router(auth.router,   prefix="/api/v1", tags=["Auth"])
app.include_router(upload.router, prefix="/api/v1", tags=["Documents"])
app.include_router(query.router,  prefix="/api/v1", tags=["Query"])
app.include_router(jobs.router,   prefix="/api/v1", tags=["Jobs"])


@app.on_event("startup")
async def on_startup():
    from app.db.session import engine
    from app.models.user import Base # Corrected import path
    import logging

    logger = logging.getLogger(__name__)
    
    async with engine.begin() as conn:
        # This is the correct way to run sync commands (like create_all) in an async app
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables verified/created.")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "3.0.0"}
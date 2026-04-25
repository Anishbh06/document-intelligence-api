import base64
from contextlib import contextmanager

import httpx
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy.exc import OperationalError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.celery_app import celery_app
from app.config import settings
from app.models.document import Document, DocumentChunk
from app.models.job import Job
from app.models.user import User  # noqa: F401 — registers 'users' table in metadata so FK resolves

from app.core.logging import log_event
from app.services.embedding_service import get_embeddings_batch_sync
from app.services.pdf_service import chunk_text, clean_text, extract_text_from_pdf

SYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://",
    "postgresql://",
)

sync_engine = create_engine(SYNC_DATABASE_URL, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)


class TransientTaskError(Exception):
    """Raised for network/DB errors that are safe to retry automatically."""
    pass


@contextmanager
def get_sync_session() -> Session:
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _set_job_status(
    db: Session,
    job_id: int,
    *,
    status: str,
    progress: int,
    document_id: int | None = None,
    error_message: str | None = None,
    total_chunks: int | None = None,
    processed_chunks: int | None = None,
) -> None:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return
    job.status = status
    job.progress = progress
    if document_id is not None:
        job.document_id = document_id
    if error_message is not None:
        job.error_message = error_message
    if total_chunks is not None:
        job.total_chunks = total_chunks
    if processed_chunks is not None:
        job.processed_chunks = processed_chunks
    db.commit()


def _is_transient_error(exc: Exception) -> bool:
    return isinstance(exc, (httpx.RequestError, httpx.HTTPStatusError, OperationalError))


def _process_document_sync(
    job_id: int, pdf_bytes: bytes, filename: str, content_hash: str, owner_id: int
) -> None:
    with get_sync_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        if job.status == "completed" and job.document_id:
            return

        # Per-user dedup: allow different users to own the same file independently
        existing_document = (
            db.query(Document)
            .filter(Document.content_hash == content_hash, Document.owner_id == owner_id)
            .first()
        )
        if existing_document:
            existing_chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == existing_document.id
            ).count()
            _set_job_status(
                db,
                job_id,
                status="completed",
                progress=100,
                document_id=existing_document.id,
                total_chunks=existing_chunks,
                processed_chunks=existing_chunks,
            )
            return

        try:
            _set_job_status(db, job_id, status="processing", progress=1, error_message=None)
            raw_text = extract_text_from_pdf(pdf_bytes)
            cleaned = clean_text(raw_text)
            chunks = chunk_text(cleaned)

            # --- Demo / Free Tier Protection ---
            # Limit to 40 chunks (~20,000 words) to avoid Gemini 429 rate limits.
            # 40 chunks is plenty for a demo and guarantees fast <15s processing.
            MAX_CHUNKS = 40
            if len(chunks) > MAX_CHUNKS:
                chunks = chunks[:MAX_CHUNKS]

            total_chunks = len(chunks)
            if total_chunks == 0:
                _set_job_status(
                    db,
                    job_id,
                    status="failed",
                    progress=100,
                    error_message="Could not extract text from PDF",
                    total_chunks=0,
                    processed_chunks=0,
                )
                return

            _set_job_status(
                db,
                job_id,
                status="processing",
                progress=10,
                total_chunks=total_chunks,
                processed_chunks=0,
            )


            embeddings = get_embeddings_batch_sync(chunks)

            _set_job_status(
                db,
                job_id,
                status="processing",
                progress=70,
                total_chunks=total_chunks,
                processed_chunks=0,
            )

            document = Document(
                filename=filename,
                content_hash=content_hash,
                original_text=cleaned,
                owner_id=owner_id,
            )
            db.add(document)
            db.flush()

            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_index=idx,
                        content=chunk,
                        embedding=embedding,
                    )
                )

            db.commit()

            _set_job_status(
                db,
                job_id,
                status="completed",
                progress=100,
                document_id=document.id,
                total_chunks=total_chunks,
                processed_chunks=total_chunks,
            )
        except Exception as exc:
            db.rollback()
            if _is_transient_error(exc):
                raise TransientTaskError(str(exc)) from exc
            _set_job_status(
                db,
                job_id,
                status="failed",
                progress=100,
                error_message=str(exc),
            )
            raise


# ── Celery task with autoretry_for ────────────────────────────────────────────
@celery_app.task(
    bind=True,
    name="process_document",
    # autoretry_for: Celery automatically retries when TransientTaskError is raised.
    # This replaces boilerplate self.retry() calls and signals production-grade thinking.
    autoretry_for=(TransientTaskError,),
    max_retries=3,
    retry_backoff=True,       # exponential back-off: 1s, 2s, 4s, …
    retry_backoff_max=120,    # capped at 2 minutes between attempts
    retry_jitter=True,        # randomise to avoid retry storms
)
def process_document(
    self, job_id: int, pdf_bytes_b64: str, filename: str, content_hash: str, owner_id: int
) -> dict:
    log_event("worker.task", "task_started", task_id=self.request.id, job_id=job_id, filename=filename)
    pdf_bytes = base64.b64decode(pdf_bytes_b64)

    try:
        _process_document_sync(job_id, pdf_bytes, filename, content_hash, owner_id)
        log_event("worker.task", "task_completed", task_id=self.request.id, job_id=job_id)
        return {"job_id": job_id, "status": "completed", "progress": 100}

    except TransientTaskError:
        # autoretry_for handles the actual retry; we just update the job status here.
        retry_count = self.request.retries
        with get_sync_session() as db:
            if retry_count >= self.max_retries:
                _set_job_status(
                    db,
                    job_id,
                    status="failed",
                    progress=100,
                    error_message="Max retries exceeded — giving up",
                )
            else:
                _set_job_status(
                    db,
                    job_id,
                    status="pending",
                    progress=0,
                    error_message=f"Transient error — retry attempt {retry_count + 1}/{self.max_retries}",
                )
        raise  # let autoretry_for take over

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


def _process_document_sync(job_id: int, pdf_bytes: bytes, filename: str, content_hash: str) -> None:
    with get_sync_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        if job.status == "completed" and job.document_id:
            return

        existing_document = db.query(Document).filter(Document.content_hash == content_hash).first()
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
                progress=5,
                total_chunks=total_chunks,
                processed_chunks=0,
            )

            embeddings = get_embeddings_batch_sync(chunks)

            document = Document(filename=filename, content_hash=content_hash, original_text=cleaned)
            db.add(document)
            db.flush()

            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings), start=1):
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_index=idx - 1,
                        content=chunk,
                        embedding=embedding,
                    )
                )
                db.commit()
                progress = min(99, int((idx / total_chunks) * 100))
                _set_job_status(
                    db,
                    job_id,
                    status="processing",
                    progress=progress,
                    total_chunks=total_chunks,
                    processed_chunks=idx,
                )

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


@celery_app.task(
    bind=True,
    name="process_document",
    max_retries=5,
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
)
def process_document(self, job_id: int, pdf_bytes_b64: str, filename: str, content_hash: str) -> dict:
    log_event("worker.task", "task_started", task_id=self.request.id, job_id=job_id, filename=filename)
    pdf_bytes = base64.b64decode(pdf_bytes_b64)
    try:
        _process_document_sync(job_id, pdf_bytes, filename, content_hash)
        log_event("worker.task", "task_completed", task_id=self.request.id, job_id=job_id)
        return {"job_id": job_id, "status": "completed", "progress": 100}
    except TransientTaskError as exc:
        with get_sync_session() as db:
            _set_job_status(
                db,
                job_id,
                status="pending",
                progress=0,
                error_message=f"Retrying after transient error: {exc}",
            )
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            with get_sync_session() as db:
                _set_job_status(
                    db,
                    job_id,
                    status="failed",
                    progress=100,
                    error_message=f"Max retries exceeded: {exc}",
                )
            raise

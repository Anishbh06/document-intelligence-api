import base64
import hashlib

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import APIError
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.document_repo import DocumentRepository
from app.repositories.job_repo import JobRepository
from app.schemas.document import DocumentResponse
from app.schemas.job import JobResponse, UploadJobResponse
from app.tasks.document_tasks import process_document

router = APIRouter()


@router.post("/upload", response_model=UploadJobResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise APIError(status_code=400, code="invalid_file_type", message="Only PDF files are accepted")

    if file.size and file.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise APIError(
            status_code=400,
            code="file_too_large",
            message=f"File size must be under {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    file_bytes = await file.read()
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise APIError(
            status_code=400,
            code="file_too_large",
            message=f"File size must be under {settings.MAX_UPLOAD_SIZE_MB}MB",
        )
    if not file_bytes.startswith(b"%PDF"):
        raise APIError(status_code=400, code="invalid_pdf_content", message="Uploaded file is not a valid PDF")

    content_hash = hashlib.sha256(file_bytes).hexdigest()

    job_repo = JobRepository(db)
    document_repo = DocumentRepository(db)

    existing_job = await job_repo.get_latest_by_content_hash(content_hash)
    if existing_job and existing_job.status in {"pending", "processing", "completed"}:
        return UploadJobResponse(
            message="Duplicate document detected. Returning existing job.",
            job=JobResponse.model_validate(existing_job),
        )

    # Dedup is per-user — two different users can own the same file independently
    existing_document = await document_repo.get_document_by_hash(content_hash, owner_id=current_user.id)
    if existing_document:
        job = await job_repo.create_job(filename=filename, content_hash=content_hash)
        job.status = "completed"
        job.progress = 100
        job.document_id = existing_document.id
        job.total_chunks = await document_repo.get_chunk_count(existing_document.id)
        job.processed_chunks = job.total_chunks
        return UploadJobResponse(
            message="Document already processed.",
            job=JobResponse.model_validate(job),
        )

    job = await job_repo.create_job(filename=filename, content_hash=content_hash)

    pdf_bytes_b64 = base64.b64encode(file_bytes).decode("utf-8")
    # Pass owner_id so the Celery worker can stamp the document with the right owner
    process_document.delay(job.id, pdf_bytes_b64, filename, content_hash, current_user.id)

    return UploadJobResponse(
        message="Document upload received. Processing in background.",
        job=JobResponse(
            id=job.id,
            status=job.status,
            progress=job.progress,
            total_chunks=job.total_chunks,
            processed_chunks=job.processed_chunks,
            filename=job.filename,
            document_id=job.document_id,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        ),
    )


@router.get("/documents", response_model=dict)
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = DocumentRepository(db)
    documents = await repo.get_all_documents(owner_id=current_user.id)

    document_responses = []
    for doc in documents:
        chunk_count = await repo.get_chunk_count(doc.id)
        document_responses.append(
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                created_at=doc.created_at,
                chunk_count=chunk_count,
            )
        )

    return {"documents": document_responses, "total": len(document_responses)}


@router.delete("/documents/{document_id}", response_model=dict)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    document_repo = DocumentRepository(db)
    job_repo = JobRepository(db)

    await job_repo.delete_jobs_by_document_id(document_id)
    # owner_id check ensures users can only delete their own documents
    success = await document_repo.delete_document(document_id, owner_id=current_user.id)

    if not success:
        raise APIError(
            status_code=404,
            code="document_not_found",
            message="Document not found",
        )

    return {"message": "Document and associated data deleted successfully"}
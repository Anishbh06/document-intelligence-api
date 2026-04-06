from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.document import UploadResponse, DocumentResponse
from app.services.pdf_service import process_pdf
from app.services.embedding_service import get_embeddings_batch
from app.repositories.document_repo import DocumentRepository

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be under 10MB")

    cleaned_text, chunks = await process_pdf(file)

    if not chunks:
        raise HTTPException(status_code=422, detail="Could not extract text from PDF")

    embeddings = await get_embeddings_batch(chunks)

    repo = DocumentRepository(db)

    document = await repo.create_document(
        filename=file.filename,
        original_text=cleaned_text,
    )

    await repo.create_chunks(
        document_id=document.id,
        chunks=chunks,
        embeddings=embeddings,
    )

    chunk_count = await repo.get_chunk_count(document.id)

    return UploadResponse(
        message="Document uploaded and processed successfully",
        document=DocumentResponse(
            id=document.id,
            filename=document.filename,
            created_at=document.created_at,
            chunk_count=chunk_count,
        )
    )
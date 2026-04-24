from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.document import QueryRequest, QueryResponse, DocumentChunkResponse
from app.services.embedding_service import get_embedding
from app.services.rag_service import generate_answer
from app.repositories.document_repo import DocumentRepository

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_document(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = DocumentRepository(db)

    # owner_id scope: returns None if doc exists but belongs to a different user
    # (returns 404 rather than 403 to avoid leaking existence of other users' docs)
    document = await repo.get_document(request.document_id, owner_id=current_user.id)
    if not document:
        raise APIError(status_code=404, code="document_not_found", message="Document not found")


    query_embedding = await get_embedding(request.question)

    similar_chunks = await repo.search_similar_chunks(
        document_id=request.document_id,
        query_embedding=query_embedding,
        top_k=5,
    )

    if not similar_chunks:
        raise APIError(
            status_code=404,
            code="no_document_content",
            message="No content found in document",
        )

    answer = await generate_answer(request.question, similar_chunks)

    return QueryResponse(
        answer=answer,
        citations=[
            DocumentChunkResponse(
                id=chunk.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
            )
            for chunk in similar_chunks
        ]
    )
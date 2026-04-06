from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.document import QueryRequest, QueryResponse, DocumentChunkResponse
from app.services.embedding_service import get_embedding
from app.services.rag_service import generate_answer
from app.repositories.document_repo import DocumentRepository

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_document(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = DocumentRepository(db)

    document = await repo.get_document(request.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    query_embedding = await get_embedding(request.question)

    similar_chunks = await repo.search_similar_chunks(
        document_id=request.document_id,
        query_embedding=query_embedding,
        top_k=5,
    )

    if not similar_chunks:
        raise HTTPException(status_code=404, detail="No content found in document")

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
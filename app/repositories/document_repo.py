from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.document import Document, DocumentChunk


class DocumentRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_document(
        self,
        filename: str,
        original_text: str,
    ) -> Document:
        document = Document(
            filename=filename,
            original_text=original_text,
        )
        self.db.add(document)
        await self.db.flush()
        return document

    async def create_chunks(
        self,
        document_id: int,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> list[DocumentChunk]:
        chunk_objects = [
            DocumentChunk(
                document_id=document_id,
                chunk_index=i,
                content=chunk,
                embedding=embedding,
            )
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]
        self.db.add_all(chunk_objects)
        await self.db.flush()
        return chunk_objects

    async def get_document(self, document_id: int) -> Document | None:
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_chunk_count(self, document_id: int) -> int:
        result = await self.db.execute(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.document_id == document_id
            )
        )
        return result.scalar_one()

    async def search_similar_chunks(
        self,
        document_id: int,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        return result.scalars().all()

        async def get_all_documents(self) -> list[Document]:
    result = await self.db.execute(
        select(Document).order_by(Document.created_at.desc())
    )
    return result.scalars().all()
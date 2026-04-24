from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.document import Document, DocumentChunk


class DocumentRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_document(
        self,
        filename: str,
        content_hash: str,
        original_text: str,
        owner_id: int,
    ) -> Document:
        document = Document(
            filename=filename,
            content_hash=content_hash,
            original_text=original_text,
            owner_id=owner_id,
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

    async def get_document(self, document_id: int, owner_id: int | None = None) -> Document | None:
        """Fetch a document, optionally scoped to a specific owner."""
        query = select(Document).where(Document.id == document_id)
        if owner_id is not None:
            query = query.where(Document.owner_id == owner_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_document_by_hash(
        self, content_hash: str, owner_id: int | None = None
    ) -> Document | None:
        """Find a document by hash, scoped to an owner so different users can own the same file."""
        query = select(Document).where(Document.content_hash == content_hash)
        if owner_id is not None:
            query = query.where(Document.owner_id == owner_id)
        result = await self.db.execute(query)
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

    async def get_all_documents(self, owner_id: int) -> list[Document]:
        """Return only documents owned by the given user."""
        result = await self.db.execute(
            select(Document)
            .where(Document.owner_id == owner_id)
            .order_by(Document.created_at.desc())
        )
        return result.scalars().all()

    async def delete_document(self, document_id: int, owner_id: int) -> bool:
        """Delete a document only if it belongs to the given owner."""
        document = await self.get_document(document_id, owner_id=owner_id)
        if document:
            await self.db.delete(document)
            await self.db.flush()
            return True
        return False
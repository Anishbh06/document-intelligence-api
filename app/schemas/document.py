from datetime import datetime
from pydantic import BaseModel


class DocumentChunkResponse(BaseModel):
    id: int
    chunk_index: int
    content: str

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: int
    filename: str
    created_at: datetime
    chunk_count: int

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    message: str
    document: DocumentResponse


class QueryRequest(BaseModel):
    document_id: int
    question: str


class QueryResponse(BaseModel):
    answer: str
    citations: list[DocumentChunkResponse]
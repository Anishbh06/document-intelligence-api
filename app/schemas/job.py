from datetime import datetime

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: int
    status: str
    progress: int
    total_chunks: int
    processed_chunks: int
    filename: str
    document_id: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UploadJobResponse(BaseModel):
    message: str
    job: JobResponse

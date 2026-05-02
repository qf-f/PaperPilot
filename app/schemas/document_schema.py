from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    id: UUID
    project_id: UUID
    original_filename: str
    stored_filename: str
    file_path: str
    file_type: str
    file_size: int
    parse_status: str
    chunk_count: int
    error_message: str | None = None
    index_status: str
    indexed_at: datetime | None = None
    index_error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    task_id: UUID
    rq_job_id: str | None
    parse_status: str

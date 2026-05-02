from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    project_id: str = Field(min_length=1)
    session_id: str | None = None
    user_id: str = "00000000-0000-0000-0000-000000000001"
    query: str = Field(min_length=1)
    document_ids: list[str] | None = None
    top_k: int | None = Field(default=None, ge=1, le=50)
    similarity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class CitationItem(BaseModel):
    index: int
    document_id: str
    file_name: str
    page_number: int | None = None
    section_title: str = ""
    chunk_index: int
    score: float


class RetrievedChunkPreview(BaseModel):
    chunk_id: str
    document_id: str
    file_name: str
    page_number: int | None = None
    section_title: str = ""
    chunk_index: int
    content_preview: str
    score: float


class ChatResponse(BaseModel):
    session_id: UUID
    agent_run_id: UUID
    answer: str
    citations: list[CitationItem]
    retrieved_chunks: list[RetrievedChunkPreview]
    uncertainty_flag: bool

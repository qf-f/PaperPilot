from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


SummaryType = Literal["quick", "standard", "detailed"]


class PaperSummaryRequest(BaseModel):
    project_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    session_id: str | None = None
    user_id: str = "00000000-0000-0000-0000-000000000001"
    summary_type: SummaryType = "standard"
    project_topic: str | None = None


class PaperSummaryResponse(BaseModel):
    output_id: str
    document_id: str
    summary_type: SummaryType
    summary_markdown: str
    summary_json: dict[str, Any]
    citations: list[dict[str, Any]]
    created_at: datetime


class GeneratedOutputItem(BaseModel):
    id: UUID
    project_id: UUID
    document_id: UUID | None = None
    session_id: UUID | None = None
    output_type: str
    title: str | None = None
    status: str
    model_name: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GeneratedOutputDetail(GeneratedOutputItem):
    content_markdown: str | None = None
    content_json: dict[str, Any]
    citations: list[dict[str, Any]]


class GeneratedOutputListResponse(BaseModel):
    items: list[GeneratedOutputItem]
    total: int
    page: int
    page_size: int

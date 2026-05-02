from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


SectionType = Literal[
    "abstract",
    "introduction",
    "related_work",
    "method",
    "system_design",
    "experiment",
    "conclusion",
    "custom",
]
ExecutionMode = Literal["sync", "async"]


class WritingRequest(BaseModel):
    project_id: str = Field(min_length=1)
    user_id: str = "demo-user"
    section_type: SectionType
    section_title: str = Field(min_length=1)
    topic: str | None = None
    plan_output_id: str | None = None
    requirements: str | None = None
    mode: ExecutionMode = "sync"
    run_id: str | None = None


class WritingResponse(BaseModel):
    output_id: str
    section_type: SectionType
    section_title: str
    section_markdown: str
    section_json: dict[str, Any]
    citations: list[dict[str, Any]]
    warnings: list[str]
    created_at: datetime


class DraftItem(BaseModel):
    id: UUID
    project_id: UUID
    output_type: str
    title: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DraftDetail(DraftItem):
    content_markdown: str | None = None
    content_json: dict[str, Any] = Field(default_factory=dict)
    citations: list[dict[str, Any]] = Field(default_factory=list)

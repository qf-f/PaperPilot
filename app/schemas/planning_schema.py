from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


PaperType = Literal["thesis", "course_paper", "journal_paper", "conference_paper", "proposal", "small_paper"]
ExecutionMode = Literal["sync", "async"]


class PlanningRequest(BaseModel):
    project_id: str = Field(min_length=1)
    user_id: str = "demo-user"
    topic: str | None = None
    paper_type: PaperType = "thesis"
    research_direction: str | None = None
    requirements: str | None = None
    mode: ExecutionMode = "sync"
    run_id: str | None = None


class PlanningResponse(BaseModel):
    output_id: str
    topic: str
    paper_type: PaperType
    final_markdown: str
    final_json: dict[str, Any]
    created_at: datetime


class PlanItem(BaseModel):
    id: UUID
    project_id: UUID
    output_type: str
    title: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlanDetail(PlanItem):
    content_markdown: str | None = None
    content_json: dict[str, Any] = Field(default_factory=dict)
    citations: list[dict[str, Any]] = Field(default_factory=list)

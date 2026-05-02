from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


ReviewType = Literal["full", "structure", "citation", "experiment", "writing_quality", "ai_style"]
ExecutionMode = Literal["sync", "async"]
IssueSeverity = Literal["must_fix", "should_fix", "nice_to_have"]
IssueType = Literal[
    "structure",
    "citation",
    "experiment_support",
    "logic",
    "writing_quality",
    "ai_style",
    "overclaim",
    "missing_evidence",
    "formatting",
]


class ReviewRequest(BaseModel):
    project_id: str = Field(min_length=1)
    user_id: str = "demo-user"
    target_output_id: str | None = None
    document_id: str | None = None
    review_type: ReviewType = "full"
    requirements: str | None = None
    mode: ExecutionMode = "sync"
    run_id: str | None = None

    @model_validator(mode="after")
    def require_target(self) -> "ReviewRequest":
        if not self.target_output_id and not self.document_id:
            raise ValueError("target_output_id or document_id is required")
        return self


class ReviewIssueItem(BaseModel):
    issue_type: IssueType
    severity: IssueSeverity
    location: str = ""
    original_text: str = ""
    problem: str
    suggestion: str
    revised_text: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)


class ReviewResponse(BaseModel):
    output_id: str
    review_type: ReviewType | str
    target_type: str
    target_id: str
    summary: str
    score: int = Field(ge=0, le=100)
    issues: list[ReviewIssueItem] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    review_markdown: str
    created_at: datetime


class ReviewItem(BaseModel):
    id: UUID
    project_id: UUID
    output_type: str
    title: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewDetail(ReviewItem):
    content_markdown: str | None = None
    content_json: dict[str, Any] = Field(default_factory=dict)
    citations: list[dict[str, Any]] = Field(default_factory=list)


class CitationCheckRequest(BaseModel):
    project_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    section_type: str | None = None


class CitationCheckResponse(BaseModel):
    issues: list[ReviewIssueItem] = Field(default_factory=list)
    citation_count: int = 0
    valid_count: int = 0
    invalid_count: int = 0

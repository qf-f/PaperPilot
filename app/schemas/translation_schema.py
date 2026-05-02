from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


TranslationMode = Literal["faithful", "polished"]
OutputStyle = Literal["chinese_only", "bilingual"]
RangeType = Literal["full", "pages", "chunks"]
ExecutionMode = Literal["sync", "async"]


class TranslationRequest(BaseModel):
    project_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    user_id: str = "demo-user"
    translation_mode: TranslationMode = "faithful"
    output_style: OutputStyle = "bilingual"
    range_type: RangeType = "full"
    page_from: int | None = Field(default=None, ge=1)
    page_to: int | None = Field(default=None, ge=1)
    chunk_from: int | None = Field(default=None, ge=0)
    chunk_to: int | None = Field(default=None, ge=0)
    requirements: str | None = None
    mode: ExecutionMode = "sync"
    run_id: str | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "TranslationRequest":
        if self.range_type == "pages":
            if self.page_from is None or self.page_to is None:
                raise ValueError("page_from and page_to are required when range_type=pages")
            if self.page_from > self.page_to:
                raise ValueError("page_from must be less than or equal to page_to")
        if self.range_type == "chunks":
            if self.chunk_from is None or self.chunk_to is None:
                raise ValueError("chunk_from and chunk_to are required when range_type=chunks")
            if self.chunk_from > self.chunk_to:
                raise ValueError("chunk_from must be less than or equal to chunk_to")
        return self


class TerminologyItem(BaseModel):
    id: UUID | None = None
    project_id: UUID | None = None
    document_id: UUID | None = None
    source_term: str
    target_term: str
    explanation: str | None = ""
    category: str = "general"
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    source: str = "extracted"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TranslationResponse(BaseModel):
    output_id: str
    project_id: str
    document_id: str
    translation_mode: TranslationMode | str
    output_style: OutputStyle | str
    translated_markdown: str
    terminologies: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime


class TranslationItem(BaseModel):
    id: UUID
    project_id: UUID
    document_id: UUID | None = None
    output_type: str
    title: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TranslationDetail(TranslationItem):
    content_markdown: str | None = None
    content_json: dict[str, Any] = Field(default_factory=dict)
    citations: list[dict[str, Any]] = Field(default_factory=list)


class TerminologyUpsertRequest(BaseModel):
    source_term: str = Field(min_length=1)
    target_term: str = Field(min_length=1)
    category: str = "general"
    explanation: str | None = ""
    confidence_score: float | None = Field(default=1.0, ge=0, le=1)


class TerminologyUpsertResponse(BaseModel):
    terminology: TerminologyItem

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


ReferenceStyle = Literal["gb_t_7714", "ieee", "apa", "bibtex"]


class ReferenceExtractRequest(BaseModel):
    project_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    user_id: str = "demo-user"


class ReferenceItem(BaseModel):
    id: str | None = None
    title: str = ""
    authors: list[dict[str, Any]] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    doi: str = ""
    url: str = ""
    source_type: str = "uploaded_document"
    confidence_score: float | None = None
    raw_text: str | None = None


class ReferenceExtractResponse(BaseModel):
    project_id: str
    document_id: str
    extracted_count: int
    saved_count: int
    references: list[ReferenceItem] = Field(default_factory=list)


class ReferenceFormatRequest(BaseModel):
    project_id: str = Field(min_length=1)
    style: ReferenceStyle = "gb_t_7714"


class ReferenceFormatResponse(BaseModel):
    style: ReferenceStyle
    content: str


class ReferenceRecommendRequest(BaseModel):
    project_id: str = Field(min_length=1)
    user_id: str = "demo-user"


class ReferenceRecommendResponse(BaseModel):
    recommendations: list[dict[str, Any]] = Field(default_factory=list)


class ReferenceRead(BaseModel):
    id: UUID
    project_id: UUID
    document_id: UUID | None = None
    source_type: str
    raw_text: str
    title: str | None = None
    authors: list[dict[str, Any]] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    citation_key: str | None = None
    reference_format: str
    gb_t_7714: str | None = None
    ieee: str | None = None
    apa: str | None = None
    bibtex: str | None = None
    confidence_score: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("authors", mode="before")
    @classmethod
    def none_to_list(cls, value):
        return [] if value is None else value

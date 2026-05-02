from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


SearchMode = Literal["recent", "classic", "survey", "baseline", "general"]


class LiteratureSearchRequest(BaseModel):
    project_id: str = Field(min_length=1)
    user_id: str = "demo-user"
    query: str | None = None
    search_mode: SearchMode = "general"
    max_results: int = Field(default=10, ge=1, le=50)
    generate_review_material: bool = False


class LiteratureItem(BaseModel):
    id: str
    title: str
    authors: list[dict[str, Any]] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    doi: str = ""
    url: str = ""
    pdf_url: str = ""
    source_provider: str
    relevance_score: float | None = None
    recommendation_reason: str = ""


class LiteratureSearchResponse(BaseModel):
    project_id: str
    queries: list[str] = Field(default_factory=list)
    literatures: list[LiteratureItem] = Field(default_factory=list)
    total: int
    review_material_output_id: str | None = None


class LiteratureDetail(BaseModel):
    id: UUID
    project_id: UUID
    source_provider: str
    external_id: str | None = None
    title: str
    abstract: str | None = None
    authors: list[dict[str, Any]] = Field(default_factory=list)
    year: int | None = None
    published_date: date | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    categories: list[Any] = Field(default_factory=list)
    keywords: list[Any] = Field(default_factory=list)
    citation_count: int | None = None
    influential_citation_count: int | None = None
    relevance_score: float | None = None
    recommendation_reason: str | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("authors", "categories", "keywords", mode="before")
    @classmethod
    def none_to_list(cls, value):
        return [] if value is None else value

    @field_validator("raw_data", mode="before")
    @classmethod
    def none_to_dict(cls, value):
        return {} if value is None else value


class LiteratureReviewMaterialRequest(BaseModel):
    project_id: str = Field(min_length=1)
    user_id: str = "demo-user"
    literature_ids: list[str] | None = None
    topic: str | None = None


class LiteratureReviewMaterialResponse(BaseModel):
    output_id: str
    content_markdown: str

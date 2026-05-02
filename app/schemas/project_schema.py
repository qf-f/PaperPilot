from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


def default_user_id() -> UUID:
    return UUID("00000000-0000-0000-0000-000000000001")


class ProjectCreate(BaseModel):
    user_id: UUID = Field(default_factory=default_user_id)
    title: str = Field(min_length=1, max_length=255)
    research_direction: str | None = None
    keywords: list[str] | None = None
    description: str | None = None


class ProjectRead(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    research_direction: str | None = None
    keywords: list[str] | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

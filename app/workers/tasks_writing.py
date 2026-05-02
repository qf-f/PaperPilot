from __future__ import annotations

from app.db.session import SessionLocal
from app.schemas.writing_schema import WritingRequest
from app.services.writing_service import WritingService


def generate_section_draft_task(payload: dict) -> dict:
    with SessionLocal() as db:
        response = WritingService(db).generate_section(WritingRequest(**payload))
        return response.model_dump(mode="json")

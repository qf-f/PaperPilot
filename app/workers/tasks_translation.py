from __future__ import annotations

from app.db.session import SessionLocal
from app.schemas.translation_schema import TranslationRequest
from app.services.translation_service import TranslationService


def translation_task(payload: dict) -> dict:
    with SessionLocal() as db:
        response = TranslationService(db).translate_document(TranslationRequest(**payload))
        return response.model_dump(mode="json")

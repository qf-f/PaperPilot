from __future__ import annotations

from app.db.session import SessionLocal
from app.schemas.reference_schema import ReferenceExtractRequest, ReferenceFormatRequest, ReferenceRecommendRequest
from app.services.reference_service import ReferenceService


def reference_extract_task(payload: dict) -> dict:
    with SessionLocal() as db:
        request = ReferenceExtractRequest(**payload)
        response = ReferenceService(db).extract_references(
            project_id=request.project_id,
            document_id=request.document_id,
            user_id=request.user_id,
        )
        return response.model_dump(mode="json")


def reference_format_task(payload: dict) -> dict:
    with SessionLocal() as db:
        request = ReferenceFormatRequest(**payload)
        response = ReferenceService(db).format_references(project_id=request.project_id, style=request.style)
        return response.model_dump(mode="json")


def reference_recommend_task(payload: dict) -> dict:
    with SessionLocal() as db:
        request = ReferenceRecommendRequest(**payload)
        response = ReferenceService(db).recommend_references(project_id=request.project_id, user_id=request.user_id)
        return response.model_dump(mode="json")

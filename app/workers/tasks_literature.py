from __future__ import annotations

from app.db.session import SessionLocal
from app.schemas.literature_schema import LiteratureSearchRequest, LiteratureReviewMaterialRequest
from app.services.literature_search_service import LiteratureSearchService


def literature_search_task(payload: dict) -> dict:
    with SessionLocal() as db:
        response = LiteratureSearchService(db).search(LiteratureSearchRequest(**payload))
        return response.model_dump(mode="json")


def literature_review_material_task(payload: dict) -> dict:
    with SessionLocal() as db:
        response = LiteratureSearchService(db).generate_review_material(LiteratureReviewMaterialRequest(**payload))
        return response.model_dump(mode="json")

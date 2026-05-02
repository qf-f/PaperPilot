from __future__ import annotations

from app.db.session import SessionLocal
from app.schemas.review_schema import ReviewRequest
from app.services.review_service import ReviewService


def review_task(payload: dict) -> dict:
    with SessionLocal() as db:
        response = ReviewService(db).review(ReviewRequest(**payload))
        return response.model_dump(mode="json")

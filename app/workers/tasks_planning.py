from __future__ import annotations

from app.db.session import SessionLocal
from app.schemas.planning_schema import PlanningRequest
from app.services.planning_service import PlanningService


def generate_planning_task(payload: dict) -> dict:
    with SessionLocal() as db:
        response = PlanningService(db).generate_plan(PlanningRequest(**payload))
        return response.model_dump(mode="json")

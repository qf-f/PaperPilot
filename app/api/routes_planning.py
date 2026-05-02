from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.run_schema import AgentRunAcceptedResponse
from app.schemas.planning_schema import PlanDetail, PlanItem, PlanningRequest, PlanningResponse
from app.services.planning_service import PlanningService


router = APIRouter(tags=["planning"])


@router.post("/api/planning/topic", response_model=PlanningResponse | AgentRunAcceptedResponse)
def generate_topic_plan(request: PlanningRequest, db: Session = Depends(get_db)) -> PlanningResponse | AgentRunAcceptedResponse:
    return PlanningService(db).generate_plan(request)


@router.get("/api/projects/{project_id}/plans", response_model=list[PlanItem])
def list_project_plans(project_id: str, db: Session = Depends(get_db)) -> list[PlanItem]:
    plans = PlanningService(db).list_plans(project_id)
    return [PlanItem.model_validate(plan) for plan in plans]


@router.get("/api/plans/{output_id}", response_model=PlanDetail)
def get_plan(output_id: str, db: Session = Depends(get_db)) -> PlanDetail:
    plan = PlanningService(db).get_plan(output_id)
    return PlanDetail.model_validate(plan)

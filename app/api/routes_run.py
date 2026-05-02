from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.run_schema import AgentRunDetail
from app.services.run_service import RunService


router = APIRouter(tags=["runs"])


@router.get("/api/runs/{run_id}", response_model=AgentRunDetail)
def get_agent_run(run_id: str, db: Session = Depends(get_db)) -> AgentRunDetail:
    return RunService(db).get_run(run_id)

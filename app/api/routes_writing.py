from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.run_schema import AgentRunAcceptedResponse
from app.schemas.writing_schema import DraftDetail, DraftItem, WritingRequest, WritingResponse
from app.services.writing_service import WritingService


router = APIRouter(tags=["writing"])


@router.post("/api/writing/section", response_model=WritingResponse | AgentRunAcceptedResponse)
def generate_section_draft(request: WritingRequest, db: Session = Depends(get_db)) -> WritingResponse | AgentRunAcceptedResponse:
    return WritingService(db).generate_section(request)


@router.get("/api/projects/{project_id}/drafts", response_model=list[DraftItem])
def list_project_drafts(project_id: str, db: Session = Depends(get_db)) -> list[DraftItem]:
    drafts = WritingService(db).list_drafts(project_id)
    return [DraftItem.model_validate(draft) for draft in drafts]


@router.get("/api/drafts/{output_id}", response_model=DraftDetail)
def get_draft(output_id: str, db: Session = Depends(get_db)) -> DraftDetail:
    draft = WritingService(db).get_draft(output_id)
    return DraftDetail.model_validate(draft)

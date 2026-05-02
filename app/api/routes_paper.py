from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.paper_summary_schema import (
    GeneratedOutputDetail,
    GeneratedOutputItem,
    GeneratedOutputListResponse,
    PaperSummaryRequest,
    PaperSummaryResponse,
)
from app.services import generated_output_service
from app.services.paper_summary_service import PaperSummaryService


router = APIRouter(tags=["paper"])


@router.post("/api/paper/summary", response_model=PaperSummaryResponse)
def generate_paper_summary(
    request: PaperSummaryRequest,
    db: Session = Depends(get_db),
) -> PaperSummaryResponse:
    return PaperSummaryService(db).generate_summary(request)


@router.get("/api/projects/{project_id}/outputs", response_model=GeneratedOutputListResponse)
def list_project_outputs(
    project_id: str,
    output_type: str | None = Query(default=None),
    document_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
) -> GeneratedOutputListResponse:
    outputs, total = generated_output_service.list_project_outputs_paginated(
        db=db,
        project_id=project_id,
        output_type=output_type,
        document_id=document_id,
        page=page,
        page_size=page_size,
        sort_order=sort_order,
    )
    return GeneratedOutputListResponse(
        items=[GeneratedOutputItem.model_validate(output) for output in outputs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/api/outputs/{output_id}", response_model=GeneratedOutputDetail)
def get_output(output_id: str, db: Session = Depends(get_db)) -> GeneratedOutputDetail:
    output = generated_output_service.get_output(db, output_id)
    return GeneratedOutputDetail.model_validate(output)

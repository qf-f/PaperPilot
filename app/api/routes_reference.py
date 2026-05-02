from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.reference_schema import (
    ReferenceExtractRequest,
    ReferenceExtractResponse,
    ReferenceFormatRequest,
    ReferenceFormatResponse,
    ReferenceRead,
    ReferenceRecommendRequest,
    ReferenceRecommendResponse,
)
from app.services.reference_service import ReferenceService


router = APIRouter(tags=["references"])


@router.post("/api/references/extract", response_model=ReferenceExtractResponse)
def extract_references(
    request: ReferenceExtractRequest,
    db: Session = Depends(get_db),
) -> ReferenceExtractResponse:
    return ReferenceService(db).extract_references(
        project_id=request.project_id,
        document_id=request.document_id,
        user_id=request.user_id,
    )


@router.get("/api/projects/{project_id}/references", response_model=list[ReferenceRead])
def list_project_references(
    project_id: str,
    document_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ReferenceRead]:
    refs = ReferenceService(db).list_references(project_id=project_id, document_id=document_id)
    return [ReferenceRead.model_validate(ref) for ref in refs]


@router.post("/api/references/format", response_model=ReferenceFormatResponse)
def format_references(
    request: ReferenceFormatRequest,
    db: Session = Depends(get_db),
) -> ReferenceFormatResponse:
    return ReferenceService(db).format_references(project_id=request.project_id, style=request.style)


@router.post("/api/references/recommend", response_model=ReferenceRecommendResponse)
def recommend_references(
    request: ReferenceRecommendRequest,
    db: Session = Depends(get_db),
) -> ReferenceRecommendResponse:
    return ReferenceService(db).recommend_references(project_id=request.project_id, user_id=request.user_id)

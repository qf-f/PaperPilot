from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.run_schema import AgentRunAcceptedResponse
from app.schemas.review_schema import (
    CitationCheckRequest,
    CitationCheckResponse,
    ReviewDetail,
    ReviewItem,
    ReviewRequest,
    ReviewResponse,
)
from app.services.citation_check_service import CitationCheckService
from app.services.review_service import ReviewService


router = APIRouter(tags=["review"])


@router.post("/api/review", response_model=ReviewResponse | AgentRunAcceptedResponse)
def review_target(request: ReviewRequest, db: Session = Depends(get_db)) -> ReviewResponse | AgentRunAcceptedResponse:
    return ReviewService(db).review(request)


@router.get("/api/projects/{project_id}/reviews", response_model=list[ReviewItem])
def list_project_reviews(project_id: str, db: Session = Depends(get_db)) -> list[ReviewItem]:
    reviews = ReviewService(db).list_reviews(project_id)
    return [ReviewItem.model_validate(review) for review in reviews]


@router.get("/api/reviews/{output_id}", response_model=ReviewDetail)
def get_review(output_id: str, db: Session = Depends(get_db)) -> ReviewDetail:
    review = ReviewService(db).get_review(output_id)
    return ReviewDetail.model_validate(review)


@router.post("/api/review/citations/check", response_model=CitationCheckResponse)
def check_citations(request: CitationCheckRequest, db: Session = Depends(get_db)) -> CitationCheckResponse:
    result = CitationCheckService(db).check_text_citations(
        project_id=request.project_id,
        text=request.text,
        section_type=request.section_type,
    )
    return CitationCheckResponse(**result)

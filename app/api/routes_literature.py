from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.literature.formatter import literature_to_api_item
from app.schemas.literature_schema import (
    LiteratureDetail,
    LiteratureItem,
    LiteratureReviewMaterialRequest,
    LiteratureReviewMaterialResponse,
    LiteratureSearchRequest,
    LiteratureSearchResponse,
)
from app.services.literature_search_service import LiteratureSearchService


router = APIRouter(tags=["literature"])


@router.post("/api/literature/search", response_model=LiteratureSearchResponse)
def search_literature(
    request: LiteratureSearchRequest,
    db: Session = Depends(get_db),
) -> LiteratureSearchResponse:
    return LiteratureSearchService(db).search(request)


@router.get("/api/projects/{project_id}/literatures", response_model=list[LiteratureItem])
def list_project_literatures(
    project_id: str,
    year_from: int | None = Query(default=None),
    year_to: int | None = Query(default=None),
    source_provider: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[LiteratureItem]:
    items = LiteratureSearchService(db).list_literatures(
        project_id=project_id,
        year_from=year_from,
        year_to=year_to,
        source_provider=source_provider,
        keyword=keyword,
        limit=limit,
    )
    return [LiteratureItem(**literature_to_api_item(item)) for item in items]


@router.get("/api/literatures/{literature_id}", response_model=LiteratureDetail)
def get_literature(literature_id: str, db: Session = Depends(get_db)) -> LiteratureDetail:
    item = LiteratureSearchService(db).get_literature(literature_id)
    return LiteratureDetail.model_validate(item)


@router.post("/api/literature/review-material", response_model=LiteratureReviewMaterialResponse)
def generate_review_material(
    request: LiteratureReviewMaterialRequest,
    db: Session = Depends(get_db),
) -> LiteratureReviewMaterialResponse:
    return LiteratureSearchService(db).generate_review_material(request)

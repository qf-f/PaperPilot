from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.literature_graph import run_literature_search_graph
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.models.literature import Literature
from app.db.models.project import PaperProject
from app.literature.formatter import literature_to_api_item
from app.schemas.literature_schema import (
    LiteratureItem,
    LiteratureReviewMaterialRequest,
    LiteratureReviewMaterialResponse,
    LiteratureSearchRequest,
    LiteratureSearchResponse,
)
from app.services.literature_review_material_service import LiteratureReviewMaterialService


class LiteratureSearchService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def search(self, request: LiteratureSearchRequest) -> LiteratureSearchResponse:
        final_state = run_literature_search_graph(
            {
                "user_id": request.user_id,
                "project_id": request.project_id,
                "query": request.query,
                "search_mode": request.search_mode,
                "max_results": request.max_results,
                "recent_years": self.settings.literature_search_recent_years,
                "trace": [],
            }
        )

        review_output_id = None
        saved = final_state.get("saved_literatures", [])
        if request.generate_review_material and saved:
            output, _ = LiteratureReviewMaterialService(self.db).generate(
                project_id=request.project_id,
                user_id=request.user_id,
                literature_ids=[item["id"] for item in saved],
                topic=request.query,
            )
            review_output_id = str(output.id)

        return LiteratureSearchResponse(
            project_id=request.project_id,
            queries=final_state.get("generated_queries", []),
            literatures=[LiteratureItem(**item) for item in saved],
            total=len(saved),
            review_material_output_id=review_output_id,
        )

    def list_literatures(
        self,
        project_id: str,
        year_from: int | None = None,
        year_to: int | None = None,
        source_provider: str | None = None,
        keyword: str | None = None,
        limit: int = 20,
    ) -> list[Literature]:
        project_uuid = self._parse_uuid(project_id, "project_id")
        if self.db.get(PaperProject, project_uuid) is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)
        stmt = select(Literature).where(Literature.project_id == project_uuid)
        if year_from:
            stmt = stmt.where(Literature.year >= year_from)
        if year_to:
            stmt = stmt.where(Literature.year <= year_to)
        if source_provider:
            stmt = stmt.where(Literature.source_provider == source_provider)
        if keyword:
            stmt = stmt.where(Literature.title.ilike(f"%{keyword}%"))
        stmt = stmt.order_by(Literature.relevance_score.desc().nullslast()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def get_literature(self, literature_id: str) -> Literature:
        literature = self.db.get(Literature, self._parse_uuid(literature_id, "literature_id"))
        if literature is None:
            raise AppError("Literature not found", status.HTTP_404_NOT_FOUND)
        return literature

    def generate_review_material(self, request: LiteratureReviewMaterialRequest) -> LiteratureReviewMaterialResponse:
        output, markdown = LiteratureReviewMaterialService(self.db).generate(
            project_id=request.project_id,
            user_id=request.user_id,
            literature_ids=request.literature_ids,
            topic=request.topic,
        )
        return LiteratureReviewMaterialResponse(output_id=str(output.id), content_markdown=markdown)

    @staticmethod
    def _parse_uuid(value: str, field_name: str) -> UUID:
        try:
            return UUID(str(value))
        except ValueError as exc:
            raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.reference_graph import run_reference_graph
from app.core.exceptions import AppError
from app.db.models.literature import Literature
from app.db.models.project import PaperProject
from app.db.models.reference import PaperReference
from app.references.formatter import format_reference
from app.references.recommender import recommend_references
from app.schemas.reference_schema import (
    ReferenceExtractResponse,
    ReferenceFormatResponse,
    ReferenceItem,
    ReferenceRecommendResponse,
)


class ReferenceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def extract_references(self, project_id: str, document_id: str, user_id: str) -> ReferenceExtractResponse:
        final_state = run_reference_graph(
            {
                "user_id": user_id,
                "project_id": project_id,
                "document_id": document_id,
                "trace": [],
            }
        )
        parsed = final_state.get("parsed_references", [])
        saved = final_state.get("saved_references", [])
        return ReferenceExtractResponse(
            project_id=project_id,
            document_id=document_id,
            extracted_count=len(parsed),
            saved_count=len(saved),
            references=[ReferenceItem(**item) for item in saved],
        )

    def list_references(self, project_id: str, document_id: str | None = None) -> list[PaperReference]:
        project_uuid = self._parse_uuid(project_id, "project_id")
        if self.db.get(PaperProject, project_uuid) is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)
        stmt = select(PaperReference).where(PaperReference.project_id == project_uuid)
        if document_id:
            stmt = stmt.where(PaperReference.document_id == self._parse_uuid(document_id, "document_id"))
        return list(self.db.execute(stmt.order_by(PaperReference.created_at.desc())).scalars().all())

    def format_references(self, project_id: str, style: str) -> ReferenceFormatResponse:
        refs = self.list_references(project_id)
        try:
            lines = [
                f"[{index}] {format_reference(_reference_to_dict(ref), style)}"
                for index, ref in enumerate(refs, start=1)
            ]
        except Exception as exc:
            raise AppError(f"Reference formatting failed: {exc}", status.HTTP_500_INTERNAL_SERVER_ERROR) from exc
        content = "\n\n".join(lines) if lines else "当前项目暂无参考文献。"
        return ReferenceFormatResponse(style=style, content=content)

    def recommend_references(self, project_id: str, user_id: str) -> ReferenceRecommendResponse:
        project_uuid = self._parse_uuid(project_id, "project_id")
        project = self.db.get(PaperProject, project_uuid)
        if project is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)
        topic = " ".join([project.title or "", project.research_direction or "", " ".join(project.keywords or [])])
        literatures = list(
            self.db.execute(
                select(Literature)
                .where(Literature.project_id == project_uuid)
                .order_by(Literature.relevance_score.desc().nullslast())
                .limit(50)
            ).scalars().all()
        )
        refs = list(self.db.execute(select(PaperReference).where(PaperReference.project_id == project_uuid)).scalars().all())
        recommendations = recommend_references(topic=topic, literatures=literatures, existing_references=refs)
        return ReferenceRecommendResponse(recommendations=recommendations)

    @staticmethod
    def _parse_uuid(value: str, field_name: str) -> UUID:
        try:
            return UUID(str(value))
        except ValueError as exc:
            raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc


def _reference_to_dict(ref: PaperReference) -> dict:
    return {
        "raw_text": ref.raw_text,
        "title": ref.title,
        "authors": ref.authors or [],
        "year": ref.year,
        "venue": ref.venue,
        "doi": ref.doi,
        "url": ref.url,
        "citation_key": ref.citation_key,
    }

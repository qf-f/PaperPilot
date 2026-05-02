from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.models.literature import Literature
from app.db.models.project import PaperProject
from app.db.models.reference import PaperReference
from app.review.citation_checker import check_citations, extract_citation_numbers


class CitationCheckService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_existing_citations(self, project_id: str) -> list[dict]:
        project_uuid = self._parse_uuid(project_id, "project_id")
        if self.db.get(PaperProject, project_uuid) is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)

        literatures = list(
            self.db.execute(
                select(Literature)
                .where(Literature.project_id == project_uuid)
                .order_by(Literature.relevance_score.desc().nullslast(), Literature.created_at.desc())
                .limit(100)
            )
            .scalars()
            .all()
        )
        references = list(
            self.db.execute(
                select(PaperReference)
                .where(PaperReference.project_id == project_uuid)
                .order_by(PaperReference.created_at.desc())
                .limit(100)
            )
            .scalars()
            .all()
        )

        citations: list[dict] = []
        for item in literatures:
            citations.append(
                {
                    "index": len(citations) + 1,
                    "source_type": "literature",
                    "id": str(item.id),
                    "title": item.title,
                    "authors": item.authors or [],
                    "year": item.year,
                    "venue": item.venue or "",
                    "doi": item.doi or "",
                    "url": item.url or "",
                }
            )
        for item in references:
            citations.append(
                {
                    "index": len(citations) + 1,
                    "source_type": "paper_reference",
                    "id": str(item.id),
                    "title": item.title or "",
                    "authors": item.authors or [],
                    "year": item.year,
                    "venue": item.venue or "",
                    "doi": item.doi or "",
                    "url": item.url or "",
                }
            )
        return citations

    def check_text_citations(self, project_id: str, text: str, section_type: str | None = None) -> dict:
        existing_citations = self.get_existing_citations(project_id)
        numeric_refs = extract_citation_numbers(text or "")
        issues = check_citations(text or "", existing_citations, section_type=section_type)
        existing_count = len(existing_citations)
        valid_count = sum(1 for number in numeric_refs if 1 <= number <= existing_count)
        invalid_count = len(numeric_refs) - valid_count

        return {
            "issues": [issue.model_dump() for issue in issues],
            "citation_count": len(numeric_refs),
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "existing_citation_count": existing_count,
        }

    @staticmethod
    def _parse_uuid(value: str | None, field_name: str) -> UUID:
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

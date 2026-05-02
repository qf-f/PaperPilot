from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.models.document import Document
from app.db.models.project import PaperProject
from app.db.models.terminology import Terminology
from app.translation.terminology_store import build_term_map, deduplicate_terms, normalize_source_term, source_key
from app.translation.translation_checker import detect_inconsistent_terms


class TerminologyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_terms(self, project_id: str, document_id: str | None = None) -> list[Terminology]:
        project_uuid = self._parse_uuid(project_id, "project_id")
        if self.db.get(PaperProject, project_uuid) is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)

        stmt = select(Terminology).where(Terminology.project_id == project_uuid)
        if document_id:
            stmt = stmt.where(Terminology.document_id == self._parse_uuid(document_id, "document_id"))
        stmt = stmt.order_by(Terminology.category.asc(), Terminology.source_term.asc())
        return list(self.db.execute(stmt).scalars().all())

    def upsert_terms(
        self,
        project_id: str,
        document_id: str | None,
        terms: list[dict[str, Any]],
        overwrite_target: bool = False,
    ) -> list[Terminology]:
        project_uuid = self._parse_uuid(project_id, "project_id")
        if self.db.get(PaperProject, project_uuid) is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)

        document_uuid = self._parse_uuid(document_id, "document_id") if document_id else None
        if document_uuid:
            document = self.db.get(Document, document_uuid)
            if document is None:
                raise AppError("Document not found", status.HTTP_404_NOT_FOUND)
            if document.project_id != project_uuid:
                raise AppError("Document does not belong to this project", status.HTTP_409_CONFLICT)

        saved: list[Terminology] = []
        for item in deduplicate_terms(terms):
            source_term = normalize_source_term(item.get("source_term", ""))
            target_term = str(item.get("target_term") or "").strip()
            if not source_term or not target_term:
                continue
            existing = self._find_by_source(project_uuid, source_term)
            if existing is None:
                existing = Terminology(
                    project_id=project_uuid,
                    document_id=document_uuid,
                    source_term=source_term,
                    target_term=target_term,
                    explanation=item.get("explanation") or "",
                    category=item.get("category") or "general",
                    confidence_score=item.get("confidence_score"),
                    source=item.get("source") or "extracted",
                )
                self.db.add(existing)
            else:
                if overwrite_target or not existing.target_term:
                    existing.target_term = target_term
                incoming_conf = item.get("confidence_score")
                if incoming_conf is not None and (existing.confidence_score is None or incoming_conf > existing.confidence_score):
                    existing.confidence_score = incoming_conf
                    existing.explanation = item.get("explanation") or existing.explanation
                    existing.category = item.get("category") or existing.category
                if document_uuid and existing.document_id is None:
                    existing.document_id = document_uuid
            saved.append(existing)
        self.db.commit()
        for item in saved:
            self.db.refresh(item)
        return saved

    def get_term_map(self, project_id: str) -> dict[str, str]:
        rows = self.list_terms(project_id)
        return build_term_map([self.to_dict(row) for row in rows])

    def apply_term_map(self, text: str, term_map: dict[str, str]) -> str:
        result = text
        for source_term, target_term in sorted(term_map.items(), key=lambda item: len(item[0]), reverse=True):
            if source_term and target_term:
                result = result.replace(source_term, f"{source_term}（{target_term}）")
        return result

    def detect_inconsistent_terms(
        self,
        translated_segments: list[dict[str, Any]],
        term_map: dict[str, str],
    ) -> list[str]:
        return detect_inconsistent_terms(translated_segments, term_map)

    def to_dict(self, term: Terminology) -> dict[str, Any]:
        return {
            "id": str(term.id),
            "project_id": str(term.project_id),
            "document_id": str(term.document_id) if term.document_id else None,
            "source_term": term.source_term,
            "target_term": term.target_term,
            "explanation": term.explanation or "",
            "category": term.category,
            "confidence_score": term.confidence_score,
            "source": term.source,
            "created_at": term.created_at.isoformat() if term.created_at else None,
            "updated_at": term.updated_at.isoformat() if term.updated_at else None,
        }

    def _find_by_source(self, project_id: UUID, source_term: str) -> Terminology | None:
        key = source_key(source_term)
        return self.db.execute(
            select(Terminology).where(
                Terminology.project_id == project_id,
                func.lower(Terminology.source_term) == key,
            )
        ).scalar_one_or_none()

    @staticmethod
    def _parse_uuid(value: str | None, field_name: str) -> UUID:
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

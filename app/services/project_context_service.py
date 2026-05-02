from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.models.chat import ChatMessage
from app.db.models.generated_output import GeneratedOutput
from app.db.models.literature import Literature
from app.db.models.project import PaperProject
from app.db.models.reference import PaperReference
from app.planning.context_builder import compact_generated_output, compact_literature, compact_reference


class ProjectContextService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build_context(self, project_id: str) -> dict:
        project_uuid = self._parse_uuid(project_id, "project_id")
        project = self.db.get(PaperProject, project_uuid)
        if project is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)

        output_types = ["paper_summary", "literature_review", "topic_plan", "paper_outline", "experiment_design"]
        outputs_by_type = {
            output_type: self._latest_outputs(project_uuid, output_type, limit=3)
            for output_type in output_types
        }
        literatures = self._literatures(project_uuid)
        references = self._references(project_uuid)
        recent_messages = self._recent_messages(project_uuid)

        current_year = datetime.now(UTC).year
        return {
            "project": {
                "id": str(project.id),
                "title": project.title,
                "research_direction": project.research_direction,
                "keywords": project.keywords or [],
                "description": project.description,
            },
            "paper_summaries": outputs_by_type["paper_summary"],
            "literature_reviews": outputs_by_type["literature_review"],
            "existing_plans": outputs_by_type["topic_plan"],
            "paper_outlines": outputs_by_type["paper_outline"],
            "experiment_designs": outputs_by_type["experiment_design"],
            "literatures": literatures,
            "recent_literatures": [item for item in literatures if item.get("year") and item["year"] >= current_year - 2],
            "survey_literatures": [
                item for item in literatures if "survey" in item.get("title", "").lower() or "review" in item.get("title", "").lower()
            ],
            "baseline_literatures": [
                item for item in literatures if "baseline" in item.get("title", "").lower() or "benchmark" in item.get("title", "").lower()
            ],
            "references": references,
            "recent_messages": recent_messages,
        }

    def _latest_outputs(self, project_id: UUID, output_type: str, limit: int) -> list[dict]:
        rows = list(
            self.db.execute(
                select(GeneratedOutput)
                .where(
                    GeneratedOutput.project_id == project_id,
                    GeneratedOutput.output_type == output_type,
                    GeneratedOutput.status == "finished",
                )
                .order_by(GeneratedOutput.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return [compact_generated_output(row) for row in rows]

    def _literatures(self, project_id: UUID) -> list[dict]:
        rows = list(
            self.db.execute(
                select(Literature)
                .where(Literature.project_id == project_id)
                .order_by(Literature.relevance_score.desc().nullslast(), Literature.created_at.desc())
                .limit(20)
            )
            .scalars()
            .all()
        )
        return [compact_literature(row, index) for index, row in enumerate(rows, start=1)]

    def _references(self, project_id: UUID) -> list[dict]:
        rows = list(
            self.db.execute(
                select(PaperReference)
                .where(PaperReference.project_id == project_id)
                .order_by(PaperReference.created_at.desc())
                .limit(20)
            )
            .scalars()
            .all()
        )
        return [compact_reference(row, index) for index, row in enumerate(rows, start=1)]

    def _recent_messages(self, project_id: UUID) -> list[dict]:
        rows = list(
            self.db.execute(
                select(ChatMessage)
                .where(ChatMessage.project_id == project_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(10)
            )
            .scalars()
            .all()
        )
        return [
            {"role": row.role, "content": (row.content or "")[:500], "created_at": row.created_at.isoformat()}
            for row in rows
        ]

    @staticmethod
    def _parse_uuid(value: str, field_name: str) -> UUID:
        try:
            return UUID(str(value))
        except ValueError as exc:
            raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

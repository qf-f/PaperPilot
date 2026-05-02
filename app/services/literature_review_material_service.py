from __future__ import annotations

import json
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.prompts.literature_search_prompt import LITERATURE_REVIEW_MATERIAL_PROMPT
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.models.generated_output import GeneratedOutput
from app.db.models.literature import Literature
from app.db.models.project import PaperProject
from app.services.llm_service import LLMService, LLMServiceError


class LiteratureReviewMaterialService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def generate(
        self,
        project_id: str,
        user_id: str = "demo-user",
        literature_ids: list[str] | None = None,
        topic: str | None = None,
    ) -> tuple[GeneratedOutput, str]:
        project_uuid = self._parse_uuid(project_id, "project_id")
        project = self.db.get(PaperProject, project_uuid)
        if project is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)

        stmt = select(Literature).where(Literature.project_id == project_uuid)
        if literature_ids:
            ids = [self._parse_uuid(value, "literature_id") for value in literature_ids]
            stmt = stmt.where(Literature.id.in_(ids))
        stmt = stmt.order_by(Literature.relevance_score.desc().nullslast()).limit(self.settings.literature_review_max_items)
        literatures = list(self.db.execute(stmt).scalars().all())
        if not literatures:
            raise AppError("No literatures available for review material generation", status.HTTP_404_NOT_FOUND)

        payload = {
            "topic": topic or project.title,
            "literatures": [
                {
                    "index": index,
                    "title": item.title,
                    "authors": item.authors,
                    "year": item.year,
                    "venue": item.venue,
                    "abstract": item.abstract,
                    "doi": item.doi,
                    "url": item.url,
                    "recommendation_reason": item.recommendation_reason,
                }
                for index, item in enumerate(literatures, start=1)
            ],
        }

        try:
            markdown = LLMService().generate(
                system_prompt=LITERATURE_REVIEW_MATERIAL_PROMPT,
                user_prompt=json.dumps(payload, ensure_ascii=False),
            )
        except LLMServiceError as exc:
            raise AppError(str(exc), status.HTTP_502_BAD_GATEWAY) from exc

        output = GeneratedOutput(
            project_id=project_uuid,
            document_id=None,
            session_id=None,
            output_type="literature_review",
            title=f"文献综述素材 - {topic or project.title}",
            content_markdown=markdown,
            content_json=payload,
            citations=[],
            model_name=self.settings.chat_model,
            status="finished",
        )
        self.db.add(output)
        self.db.commit()
        self.db.refresh(output)
        return output, markdown

    @staticmethod
    def _parse_uuid(value: str, field_name: str) -> UUID:
        try:
            return UUID(str(value))
        except ValueError as exc:
            raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

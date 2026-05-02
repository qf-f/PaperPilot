from __future__ import annotations

import logging
from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session

from app.agents.summary_graph import run_paper_summary_graph
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.models.document import Document
from app.db.models.generated_output import GeneratedOutput
from app.db.models.project import PaperProject
from app.schemas.paper_summary_schema import PaperSummaryRequest, PaperSummaryResponse


logger = logging.getLogger(__name__)


class PaperSummaryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def generate_summary(self, request: PaperSummaryRequest) -> PaperSummaryResponse:
        project_id = self._parse_uuid(request.project_id, "project_id")
        document_id = self._parse_uuid(request.document_id, "document_id")
        session_id = self._parse_uuid(request.session_id, "session_id") if request.session_id else None

        project = self.db.get(PaperProject, project_id)
        if project is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)

        document = self.db.get(Document, document_id)
        if document is None:
            raise AppError("Document not found", status.HTTP_404_NOT_FOUND)
        if document.project_id != project_id:
            raise AppError("Document does not belong to this project", status.HTTP_409_CONFLICT)
        if document.parse_status != "parsed":
            raise AppError(
                f"Document is not parsed yet, current parse_status={document.parse_status}",
                status.HTTP_409_CONFLICT,
            )

        output = GeneratedOutput(
            project_id=project_id,
            document_id=document_id,
            session_id=session_id,
            output_type="paper_summary",
            title=f"论文总结 - {document.original_filename}",
            content_markdown="",
            content_json={},
            citations=[],
            model_name=self.settings.chat_model,
            status="generating",
        )
        self.db.add(output)
        self.db.commit()
        self.db.refresh(output)

        logger.info(
            "paper summary start output_id=%s project_id=%s document_id=%s summary_type=%s",
            output.id,
            project_id,
            document_id,
            request.summary_type,
        )

        try:
            final_state = run_paper_summary_graph(
                {
                    "user_id": request.user_id,
                    "project_id": str(project_id),
                    "document_id": str(document_id),
                    "session_id": str(session_id) if session_id else None,
                    "summary_type": request.summary_type,
                    "project_topic": request.project_topic,
                    "output_id": str(output.id),
                    "trace": [],
                }
            )
            self.db.refresh(output)
            logger.info(
                "paper summary finished output_id=%s document_id=%s",
                output.id,
                document_id,
            )

            return PaperSummaryResponse(
                output_id=str(output.id),
                document_id=str(document_id),
                summary_type=request.summary_type,
                summary_markdown=output.content_markdown or final_state.get("final_summary_markdown", ""),
                summary_json=output.content_json or final_state.get("final_summary_json", {}),
                citations=output.citations or final_state.get("citations", []),
                created_at=output.created_at,
            )
        except AppError as exc:
            self._mark_output_failed(output, exc.message)
            raise
        except Exception as exc:
            self._mark_output_failed(output, str(exc))
            logger.exception("paper summary failed output_id=%s error=%s", output.id, exc)
            raise AppError(f"Paper summary failed: {exc}", status.HTTP_500_INTERNAL_SERVER_ERROR) from exc

    def _mark_output_failed(self, output: GeneratedOutput, message: str) -> None:
        output.status = "failed"
        output.error_message = message
        self.db.commit()

    @staticmethod
    def _parse_uuid(value: str | None, field_name: str) -> UUID:
        try:
            return UUID(str(value))
        except ValueError as exc:
            raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

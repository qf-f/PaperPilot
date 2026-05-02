from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.review_graph import build_review_graph
from app.agents.runner import AgentRunner
from app.core.exceptions import AppError
from app.db.models.document import Document
from app.db.models.generated_output import GeneratedOutput
from app.db.models.project import PaperProject
from app.schemas.review_schema import ReviewRequest, ReviewResponse
from app.schemas.run_schema import AgentRunAcceptedResponse
from app.workers.queue import get_document_queue


class ReviewService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def review(self, request: ReviewRequest) -> ReviewResponse | AgentRunAcceptedResponse:
        project_id = self._parse_uuid(request.project_id, "project_id")
        if self.db.get(PaperProject, project_id) is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)

        if request.target_output_id:
            output = self.db.get(GeneratedOutput, self._parse_uuid(request.target_output_id, "target_output_id"))
            if output is None:
                raise AppError("Target output not found", status.HTTP_404_NOT_FOUND)
            if output.project_id != project_id:
                raise AppError("Target output does not belong to the project", status.HTTP_400_BAD_REQUEST)
        elif request.document_id:
            document = self.db.get(Document, self._parse_uuid(request.document_id, "document_id"))
            if document is None:
                raise AppError("Document not found", status.HTTP_404_NOT_FOUND)
            if document.project_id != project_id:
                raise AppError("Document does not belong to the project", status.HTTP_400_BAD_REQUEST)
            if document.parse_status != "parsed":
                raise AppError("Document has not been parsed yet", status.HTTP_400_BAD_REQUEST)
        else:
            raise AppError("target_output_id or document_id is required", status.HTTP_400_BAD_REQUEST)

        if request.mode == "async":
            run = AgentRunner(self.db).create_run(
                str(project_id),
                "review",
                request.target_output_id or request.document_id or "review",
                status_value="queued",
            )
            payload = request.model_dump()
            payload.update({"mode": "sync", "run_id": str(run.id)})
            from app.workers.tasks_review import review_task

            get_document_queue().enqueue(review_task, payload, job_timeout="30m")
            return AgentRunAcceptedResponse(run_id=str(run.id))

        final_state, _ = AgentRunner(self.db).run_sync(
            graph=build_review_graph(),
            project_id=str(project_id),
            intent="review",
            user_query=request.target_output_id or request.document_id or "review",
            run_id=request.run_id,
            input_state=
            {
                "user_id": request.user_id,
                "project_id": str(project_id),
                "target_output_id": request.target_output_id,
                "document_id": request.document_id,
                "review_type": request.review_type,
                "requirements": request.requirements,
                "trace": [],
            },
        )
        output_id = final_state.get("output_id")
        output = self.db.get(GeneratedOutput, self._parse_uuid(output_id, "output_id")) if output_id else None
        if output is None:
            raise AppError("Review output was not saved", status.HTTP_500_INTERNAL_SERVER_ERROR)
        return self._to_response(output)

    def list_reviews(self, project_id: str) -> list[GeneratedOutput]:
        project_uuid = self._parse_uuid(project_id, "project_id")
        if self.db.get(PaperProject, project_uuid) is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)
        return list(
            self.db.execute(
                select(GeneratedOutput)
                .where(GeneratedOutput.project_id == project_uuid, GeneratedOutput.output_type == "review_report")
                .order_by(GeneratedOutput.created_at.desc())
            )
            .scalars()
            .all()
        )

    def get_review(self, output_id: str) -> GeneratedOutput:
        output = self.db.get(GeneratedOutput, self._parse_uuid(output_id, "output_id"))
        if output is None or output.output_type != "review_report":
            raise AppError("Review report not found", status.HTTP_404_NOT_FOUND)
        return output

    @staticmethod
    def _to_response(output: GeneratedOutput) -> ReviewResponse:
        content_json = output.content_json or {}
        return ReviewResponse(
            output_id=str(output.id),
            review_type=content_json.get("review_type", "full"),
            target_type=content_json.get("target_type", ""),
            target_id=content_json.get("target_id", ""),
            summary=content_json.get("summary", ""),
            score=int(content_json.get("score", 0)),
            issues=content_json.get("issues", []),
            strengths=content_json.get("strengths", []),
            risks=content_json.get("risks", []),
            next_actions=content_json.get("next_actions", []),
            review_markdown=output.content_markdown or "",
            created_at=output.created_at,
        )

    @staticmethod
    def _parse_uuid(value: str | None, field_name: str) -> UUID:
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

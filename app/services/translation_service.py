from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.runner import AgentRunner
from app.agents.translation_graph import build_translation_graph
from app.core.exceptions import AppError
from app.db.models.document import Document
from app.db.models.generated_output import GeneratedOutput
from app.db.models.project import PaperProject
from app.schemas.translation_schema import TranslationRequest, TranslationResponse
from app.schemas.run_schema import AgentRunAcceptedResponse
from app.workers.queue import get_document_queue


class TranslationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def translate_document(self, request: TranslationRequest) -> TranslationResponse | AgentRunAcceptedResponse:
        project_id = self._parse_uuid(request.project_id, "project_id")
        document_id = self._parse_uuid(request.document_id, "document_id")

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
        if document.chunk_count <= 0:
            raise AppError("Document has no chunks to translate", status.HTTP_409_CONFLICT)

        if request.mode == "async":
            run = AgentRunner(self.db).create_run(str(project_id), "translation", document.original_filename, status_value="queued")
            payload = request.model_dump()
            payload.update({"mode": "sync", "run_id": str(run.id)})
            from app.workers.tasks_translation import translation_task

            get_document_queue().enqueue(translation_task, payload, job_timeout="60m")
            return AgentRunAcceptedResponse(run_id=str(run.id))

        final_state, _ = AgentRunner(self.db).run_sync(
            graph=build_translation_graph(),
            project_id=str(project_id),
            intent="translation",
            user_query=document.original_filename,
            run_id=request.run_id,
            input_state=
            {
                "user_id": request.user_id,
                "project_id": str(project_id),
                "document_id": str(document_id),
                "translation_mode": request.translation_mode,
                "output_style": request.output_style,
                "range_type": request.range_type,
                "page_from": request.page_from,
                "page_to": request.page_to,
                "chunk_from": request.chunk_from,
                "chunk_to": request.chunk_to,
                "requirements": request.requirements,
                "trace": [],
            },
        )
        output_id = final_state.get("output_id")
        output = self.db.get(GeneratedOutput, self._parse_uuid(output_id, "output_id")) if output_id else None
        if output is None:
            raise AppError("Translation output was not saved", status.HTTP_500_INTERNAL_SERVER_ERROR)
        return self._to_response(output)

    def list_translations(self, project_id: str) -> list[GeneratedOutput]:
        project_uuid = self._parse_uuid(project_id, "project_id")
        if self.db.get(PaperProject, project_uuid) is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)
        return list(
            self.db.execute(
                select(GeneratedOutput)
                .where(GeneratedOutput.project_id == project_uuid, GeneratedOutput.output_type == "translation")
                .order_by(GeneratedOutput.created_at.desc())
            )
            .scalars()
            .all()
        )

    def get_translation(self, output_id: str) -> GeneratedOutput:
        output = self.db.get(GeneratedOutput, self._parse_uuid(output_id, "output_id"))
        if output is None or output.output_type != "translation":
            raise AppError("Translation output not found", status.HTTP_404_NOT_FOUND)
        return output

    @staticmethod
    def _to_response(output: GeneratedOutput) -> TranslationResponse:
        content_json = output.content_json or {}
        return TranslationResponse(
            output_id=str(output.id),
            project_id=str(output.project_id),
            document_id=str(output.document_id) if output.document_id else "",
            translation_mode=content_json.get("translation_mode", "faithful"),
            output_style=content_json.get("output_style", "bilingual"),
            translated_markdown=output.content_markdown or "",
            terminologies=content_json.get("terminologies", []),
            warnings=content_json.get("warnings", []),
            created_at=output.created_at,
        )

    @staticmethod
    def _parse_uuid(value: str | None, field_name: str) -> UUID:
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

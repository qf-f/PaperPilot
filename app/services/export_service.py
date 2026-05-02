from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.models.export_task import ExportTask
from app.db.models.generated_output import GeneratedOutput
from app.exporters.markdown_exporter import export_markdown, safe_filename
from app.exporters.word_exporter import export_word_from_markdown
from app.schemas.export_schema import ExportRequest, ExportResponse


logger = logging.getLogger(__name__)


class ExportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def export_output(self, output_id: str, request: ExportRequest) -> ExportResponse:
        output = self.db.get(GeneratedOutput, self._parse_uuid(output_id, "output_id"))
        if output is None:
            raise AppError("Generated output not found", status.HTTP_404_NOT_FOUND)
        if output.status != "finished":
            raise AppError(
                f"Generated output is not finished, current status={output.status}",
                status.HTTP_409_CONFLICT,
            )
        if not output.content_markdown:
            raise AppError("Generated output has no Markdown content to export", status.HTTP_409_CONFLICT)

        export_task = ExportTask(
            project_id=output.project_id,
            output_id=output.id,
            export_type=request.export_type,
            status="pending",
        )
        self.db.add(export_task)
        self.db.commit()
        self.db.refresh(export_task)

        try:
            export_task.status = "exporting"
            self.db.commit()

            base_name = safe_filename(output.title or f"{output.output_type}-{output.id}")
            suffix = ".md" if request.export_type == "markdown" else ".docx"
            file_name = f"{base_name}{suffix}"
            file_path = Path(self.settings.export_dir) / str(output.project_id) / file_name

            if request.export_type == "markdown":
                final_path = export_markdown(output.content_markdown, str(file_path))
            elif request.export_type == "word":
                final_path = export_word_from_markdown(
                    markdown_content=output.content_markdown,
                    file_path=str(file_path),
                    title=output.title,
                )
            else:
                raise AppError(f"Unsupported export_type: {request.export_type}", status.HTTP_400_BAD_REQUEST)

            export_task.status = "finished"
            export_task.file_path = final_path
            export_task.file_name = Path(final_path).name
            export_task.error_message = None
            self.db.commit()
            self.db.refresh(export_task)

            logger.info(
                "export finished output_id=%s export_type=%s file_path=%s",
                output.id,
                request.export_type,
                final_path,
            )

            return ExportResponse(
                export_task_id=str(export_task.id),
                output_id=str(output.id),
                export_type=request.export_type,
                file_name=export_task.file_name or file_name,
                file_path=export_task.file_path or final_path,
                status=export_task.status,
            )
        except AppError as exc:
            self._mark_failed(export_task, exc.message)
            raise
        except Exception as exc:
            self._mark_failed(export_task, str(exc))
            logger.exception("export failed output_id=%s error=%s", output.id, exc)
            raise AppError(f"Export failed: {exc}", status.HTTP_500_INTERNAL_SERVER_ERROR) from exc

    def get_export_task(self, export_task_id: str) -> ExportTask:
        task = self.db.get(ExportTask, self._parse_uuid(export_task_id, "export_task_id"))
        if task is None:
            raise AppError("Export task not found", status.HTTP_404_NOT_FOUND)
        return task

    def _mark_failed(self, export_task: ExportTask, message: str) -> None:
        export_task.status = "failed"
        export_task.error_message = message
        self.db.commit()

    @staticmethod
    def _parse_uuid(value: str, field_name: str) -> UUID:
        try:
            return UUID(str(value))
        except ValueError as exc:
            raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

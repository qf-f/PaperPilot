from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.core.config import get_settings
from app.db.models.export_task import ExportTask
from app.db.models.generated_output import GeneratedOutput
from app.db.session import SessionLocal
from app.exporters.markdown_exporter import export_markdown, safe_filename
from app.exporters.word_exporter import export_word_from_markdown


def export_output_task(export_task_id: str) -> dict[str, str]:
    parsed_task_id = UUID(export_task_id)
    settings = get_settings()

    with SessionLocal() as db:
        task = db.get(ExportTask, parsed_task_id)
        if task is None:
            raise ValueError(f"Export task not found: {export_task_id}")

        output = db.get(GeneratedOutput, task.output_id)
        if output is None:
            task.status = "failed"
            task.error_message = "Generated output not found"
            db.commit()
            return {"export_task_id": export_task_id, "status": "failed"}

        try:
            task.status = "exporting"
            db.commit()

            base_name = safe_filename(output.title or f"{output.output_type}-{output.id}")
            suffix = ".md" if task.export_type == "markdown" else ".docx"
            file_path = Path(settings.export_dir) / str(output.project_id) / f"{base_name}{suffix}"

            if task.export_type == "markdown":
                final_path = export_markdown(output.content_markdown or "", str(file_path))
            elif task.export_type == "word":
                final_path = export_word_from_markdown(
                    markdown_content=output.content_markdown or "",
                    file_path=str(file_path),
                    title=output.title,
                )
            else:
                raise ValueError(f"Unsupported export_type: {task.export_type}")

            task.file_path = final_path
            task.file_name = Path(final_path).name
            task.status = "finished"
            task.error_message = None
            db.commit()
            return {"export_task_id": export_task_id, "status": "finished"}
        except Exception as exc:
            task.status = "failed"
            task.error_message = str(exc)
            db.commit()
            raise

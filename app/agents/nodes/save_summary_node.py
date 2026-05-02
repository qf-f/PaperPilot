from __future__ import annotations

from time import perf_counter
from uuid import UUID

from fastapi import status

from app.agents.state import PaperSummaryState
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.models.generated_output import GeneratedOutput
from app.db.session import SessionLocal


def save_summary_node(state: PaperSummaryState) -> PaperSummaryState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    output_id = state.get("output_id")
    if not output_id:
        raise AppError("Missing output_id for summary save", status.HTTP_500_INTERNAL_SERVER_ERROR)

    with SessionLocal() as db:
        output = db.get(GeneratedOutput, UUID(str(output_id)))
        if output is None:
            raise AppError("Generated output placeholder not found", status.HTTP_404_NOT_FOUND)

        summary_json = state.get("final_summary_json", {})
        document_info = state.get("document_info", {})
        output.title = summary_json.get("title") or f"论文总结 - {document_info.get('file_name', '')}"
        output.content_markdown = state.get("final_summary_markdown", "")
        output.content_json = summary_json
        output.citations = state.get("citations", [])
        output.model_name = get_settings().chat_model
        output.status = "finished"
        output.error_message = None
        db.commit()

    elapsed_ms = int((perf_counter() - started_at) * 1000)
    trace.append(
        {
            "tool_name": "save_summary",
            "input": {"output_id": output_id},
            "output": {"status": "finished"},
            "latency_ms": elapsed_ms,
            "status": "success",
            "error_message": None,
        }
    )

    updated = dict(state)
    updated["trace"] = trace
    return updated

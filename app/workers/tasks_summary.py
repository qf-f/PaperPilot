from __future__ import annotations

from uuid import UUID

from app.agents.summary_graph import run_paper_summary_graph
from app.db.models.generated_output import GeneratedOutput
from app.db.session import SessionLocal


def generate_paper_summary_task(output_id: str) -> dict[str, str]:
    """Reserved RQ entry point for async paper summary generation.

    Future async API can create a generated_outputs row with
    content_json.summary_request, then enqueue this task.
    """

    parsed_output_id = UUID(output_id)
    with SessionLocal() as db:
        output = db.get(GeneratedOutput, parsed_output_id)
        if output is None:
            raise ValueError(f"Generated output not found: {output_id}")

        request_payload = (output.content_json or {}).get("summary_request")
        if not request_payload:
            output.status = "failed"
            output.error_message = "Async summary task requires content_json.summary_request metadata"
            db.commit()
            return {"output_id": output_id, "status": "failed"}

        output.status = "generating"
        output.error_message = None
        db.commit()

    try:
        run_paper_summary_graph(
            {
                "user_id": request_payload.get("user_id", "async-user"),
                "project_id": str(output.project_id),
                "document_id": str(output.document_id),
                "session_id": str(output.session_id) if output.session_id else None,
                "summary_type": request_payload.get("summary_type", "standard"),
                "project_topic": request_payload.get("project_topic"),
                "output_id": str(output.id),
                "trace": [],
            }
        )
        return {"output_id": output_id, "status": "finished"}
    except Exception as exc:
        with SessionLocal() as db:
            failed_output = db.get(GeneratedOutput, parsed_output_id)
            if failed_output is not None:
                failed_output.status = "failed"
                failed_output.error_message = str(exc)
                db.commit()
        raise

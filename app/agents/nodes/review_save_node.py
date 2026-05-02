from __future__ import annotations

from uuid import UUID

from app.agents.state import ReviewState
from app.core.config import get_settings
from app.db.models.generated_output import GeneratedOutput
from app.db.session import SessionLocal


def review_save_node(state: ReviewState) -> ReviewState:
    with SessionLocal() as db:
        output = GeneratedOutput(
            project_id=UUID(str(state["project_id"])),
            document_id=UUID(str(state["document_id"])) if state.get("target_type") == "uploaded_document" and state.get("document_id") else None,
            session_id=None,
            output_type="review_report",
            title=f"审查报告 - {state.get('target_title') or state.get('target_id')}",
            content_markdown=state.get("review_markdown", ""),
            content_json=state.get("review_json", {}),
            citations=[],
            model_name=get_settings().chat_model,
            status="finished",
        )
        db.add(output)
        db.commit()
        db.refresh(output)
    updated = dict(state)
    updated["output_id"] = str(output.id)
    return updated

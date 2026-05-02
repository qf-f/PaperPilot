from __future__ import annotations

from time import perf_counter
from uuid import UUID

from app.agents.state import WritingState
from app.core.config import get_settings
from app.db.models.generated_output import GeneratedOutput
from app.db.session import SessionLocal


def writing_save_node(state: WritingState) -> WritingState:
    started_at = perf_counter()
    with SessionLocal() as db:
        output = GeneratedOutput(
            project_id=UUID(str(state["project_id"])),
            document_id=None,
            session_id=None,
            output_type="section_draft",
            title=f"{state['section_title']} - 章节草稿",
            content_markdown=state.get("section_markdown", ""),
            content_json=state.get("section_json", {}),
            citations=state.get("citations", []),
            model_name=get_settings().chat_model,
            status="finished",
        )
        db.add(output)
        db.commit()
        db.refresh(output)

    trace = list(state.get("trace", []))
    trace.append({"tool_name": "writing_save", "latency_ms": int((perf_counter() - started_at) * 1000), "status": "success"})
    updated = dict(state)
    updated.update({"output_id": str(output.id), "trace": trace})
    return updated

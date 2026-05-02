from __future__ import annotations

from time import perf_counter
from uuid import UUID

from app.agents.state import TranslationState
from app.core.config import get_settings
from app.db.models.generated_output import GeneratedOutput
from app.db.session import SessionLocal


def translation_save_node(state: TranslationState) -> TranslationState:
    started_at = perf_counter()
    document_name = state.get("document_info", {}).get("original_filename", state.get("document_id", "document"))
    with SessionLocal() as db:
        output = GeneratedOutput(
            project_id=UUID(str(state["project_id"])),
            document_id=UUID(str(state["document_id"])),
            session_id=None,
            output_type="translation",
            title=f"论文翻译 - {document_name}",
            content_markdown=state.get("translated_markdown", ""),
            content_json=state.get("content_json", {}),
            citations=[],
            model_name=get_settings().chat_model,
            status="finished",
        )
        db.add(output)
        db.commit()
        db.refresh(output)

    trace = list(state.get("trace", []))
    trace.append(
        {
            "tool_name": "translation_save",
            "output": {"output_id": str(output.id)},
            "latency_ms": int((perf_counter() - started_at) * 1000),
            "status": "success",
        }
    )
    updated = dict(state)
    updated.update({"output_id": str(output.id), "trace": trace})
    return updated

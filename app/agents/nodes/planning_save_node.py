from __future__ import annotations

from time import perf_counter
from uuid import UUID

from app.agents.state import PlanningState
from app.core.config import get_settings
from app.db.models.generated_output import GeneratedOutput
from app.db.session import SessionLocal


def planning_save_node(state: PlanningState) -> PlanningState:
    started_at = perf_counter()
    with SessionLocal() as db:
        output = GeneratedOutput(
            project_id=UUID(str(state["project_id"])),
            document_id=None,
            session_id=None,
            output_type="topic_plan",
            title=f"论文规划 - {state['topic']}",
            content_markdown=state.get("final_markdown", ""),
            content_json=state.get("final_json", {}),
            citations=[],
            model_name=get_settings().chat_model,
            status="finished",
        )
        db.add(output)
        db.commit()
        db.refresh(output)

    trace = list(state.get("trace", []))
    trace.append({"tool_name": "planning_save", "latency_ms": int((perf_counter() - started_at) * 1000), "status": "success"})
    updated = dict(state)
    updated.update({"output_id": str(output.id), "trace": trace})
    return updated

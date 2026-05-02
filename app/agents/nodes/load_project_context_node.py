from __future__ import annotations

from time import perf_counter

from app.agents.state import PlanningState
from app.db.session import SessionLocal
from app.services.project_context_service import ProjectContextService


def load_project_context_node(state: PlanningState) -> PlanningState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    with SessionLocal() as db:
        context = ProjectContextService(db).build_context(state["project_id"])

    trace.append(
        {
            "tool_name": "load_project_context",
            "input": {"project_id": state["project_id"]},
            "output": {
                "literature_count": len(context.get("literatures", [])),
                "reference_count": len(context.get("references", [])),
            },
            "latency_ms": int((perf_counter() - started_at) * 1000),
            "status": "success",
            "error_message": None,
        }
    )
    updated = dict(state)
    updated.update({"project_context": context, "trace": trace})
    return updated

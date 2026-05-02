from __future__ import annotations

from time import perf_counter

from app.agents.state import ReviewState
from app.db.session import SessionLocal
from app.services.citation_check_service import CitationCheckService
from app.services.project_context_service import ProjectContextService


def review_context_node(state: ReviewState) -> ReviewState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    with SessionLocal() as db:
        context = ProjectContextService(db).build_context(state["project_id"])
        citations = CitationCheckService(db).get_existing_citations(state["project_id"])
    trace.append(
        {
            "tool_name": "review_context",
            "output": {"citation_count": len(citations)},
            "latency_ms": int((perf_counter() - started_at) * 1000),
            "status": "success",
            "error_message": None,
        }
    )
    updated = dict(state)
    updated.update({"project_context": context, "existing_citations": citations, "trace": trace})
    return updated

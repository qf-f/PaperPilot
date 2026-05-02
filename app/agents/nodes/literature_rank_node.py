from __future__ import annotations

from time import perf_counter

from app.agents.state import LiteratureSearchState
from app.literature.ranker import rank_literatures


def literature_rank_node(state: LiteratureSearchState) -> LiteratureSearchState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    query = " ".join(state.get("generated_queries", []))
    ranked = rank_literatures(
        items=state.get("deduped_results", []),
        query=query,
        search_mode=state.get("search_mode", "general"),
        recent_years=int(state.get("recent_years", 3)),
    )
    elapsed_ms = int((perf_counter() - started_at) * 1000)
    trace.append(
        {
            "tool_name": "literature_rank",
            "input": {"deduped_count": len(state.get("deduped_results", [])), "search_mode": state.get("search_mode")},
            "output": {"ranked_count": len(ranked)},
            "latency_ms": elapsed_ms,
            "status": "success",
            "error_message": None,
        }
    )
    updated = dict(state)
    updated.update({"ranked_results": ranked, "trace": trace})
    return updated

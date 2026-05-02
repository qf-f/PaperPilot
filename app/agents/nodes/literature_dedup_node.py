from __future__ import annotations

from time import perf_counter

from app.agents.state import LiteratureSearchState
from app.literature.deduplicator import deduplicate_literatures
from app.literature.normalizer import normalize_literatures


def literature_dedup_node(state: LiteratureSearchState) -> LiteratureSearchState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    normalized = normalize_literatures(state.get("raw_results", []))
    deduped = deduplicate_literatures(normalized, threshold=90)
    elapsed_ms = int((perf_counter() - started_at) * 1000)
    trace.append(
        {
            "tool_name": "literature_dedup",
            "input": {"raw_count": len(state.get("raw_results", []))},
            "output": {"normalized_count": len(normalized), "deduped_count": len(deduped)},
            "latency_ms": elapsed_ms,
            "status": "success",
            "error_message": None,
        }
    )
    updated = dict(state)
    updated.update({"normalized_results": normalized, "deduped_results": deduped, "trace": trace})
    return updated

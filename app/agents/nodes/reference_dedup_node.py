from __future__ import annotations

from time import perf_counter

from app.agents.state import ReferenceState
from app.core.config import get_settings
from app.references.deduplicator import deduplicate_references


def reference_dedup_node(state: ReferenceState) -> ReferenceState:
    started_at = perf_counter()
    parsed = state.get("parsed_references", [])
    deduped = deduplicate_references(parsed, threshold=get_settings().reference_dedup_threshold)
    trace = list(state.get("trace", []))
    trace.append(
        {
            "tool_name": "reference_dedup",
            "input": {"parsed_count": len(parsed)},
            "output": {"deduped_count": len(deduped)},
            "latency_ms": int((perf_counter() - started_at) * 1000),
            "status": "success",
            "error_message": None,
        }
    )
    updated = dict(state)
    updated.update({"deduped_references": deduped, "trace": trace})
    return updated

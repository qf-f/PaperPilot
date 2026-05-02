from __future__ import annotations

from time import perf_counter

from fastapi import status

from app.agents.state import ReferenceState
from app.core.exceptions import AppError
from app.references.parser import parse_references


def reference_parse_node(state: ReferenceState) -> ReferenceState:
    started_at = perf_counter()
    reference_text = state.get("reference_text") or ""
    parsed = parse_references(reference_text)
    if reference_text and not parsed:
        raise AppError("Reference parsing returned no entries", status.HTTP_409_CONFLICT)

    trace = list(state.get("trace", []))
    trace.append(
        {
            "tool_name": "reference_parse",
            "input": {"chars": len(reference_text)},
            "output": {"parsed_count": len(parsed)},
            "latency_ms": int((perf_counter() - started_at) * 1000),
            "status": "success",
            "error_message": None,
        }
    )
    updated = dict(state)
    updated.update({"parsed_references": parsed, "trace": trace})
    return updated

from __future__ import annotations

from app.agents.state import ReferenceState


def reference_response_node(state: ReferenceState) -> ReferenceState:
    updated = dict(state)
    updated.setdefault("parsed_references", [])
    updated.setdefault("deduped_references", [])
    updated.setdefault("saved_references", [])
    updated.setdefault("recommended_references", [])
    updated.setdefault("trace", [])
    return updated

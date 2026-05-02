from __future__ import annotations

from app.agents.state import WritingState


def writing_response_node(state: WritingState) -> WritingState:
    updated = dict(state)
    updated.setdefault("section_markdown", "")
    updated.setdefault("section_json", {})
    updated.setdefault("citations", [])
    updated.setdefault("warnings", [])
    updated.setdefault("trace", [])
    return updated

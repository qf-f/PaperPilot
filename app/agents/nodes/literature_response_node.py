from __future__ import annotations

from app.agents.state import LiteratureSearchState


def literature_response_node(state: LiteratureSearchState) -> LiteratureSearchState:
    updated = dict(state)
    updated.setdefault("saved_literatures", [])
    updated.setdefault("generated_queries", [])
    updated.setdefault("trace", [])
    return updated

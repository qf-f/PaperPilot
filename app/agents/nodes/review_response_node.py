from __future__ import annotations

from app.agents.state import ReviewState


def review_response_node(state: ReviewState) -> ReviewState:
    updated = dict(state)
    updated.setdefault("review_json", {})
    updated.setdefault("review_markdown", "")
    updated.setdefault("score", 0)
    return updated

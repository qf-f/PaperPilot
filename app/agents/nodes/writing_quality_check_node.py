from __future__ import annotations

from app.agents.state import ReviewState
from app.review.style_checker import check_writing_style


def writing_quality_check_node(state: ReviewState) -> ReviewState:
    if state.get("review_type") not in {"full", "writing_quality", "ai_style"}:
        state["writing_issues"] = []
        return state
    issues = check_writing_style(state.get("target_content", ""))
    updated = dict(state)
    updated["writing_issues"] = [issue.model_dump() for issue in issues]
    return updated

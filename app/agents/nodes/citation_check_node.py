from __future__ import annotations

from app.agents.state import ReviewState
from app.review.citation_checker import check_citations


def citation_check_node(state: ReviewState) -> ReviewState:
    if state.get("review_type") not in {"full", "citation"}:
        state["citation_issues"] = []
        return state
    section_type = (state.get("target_json") or {}).get("section_type")
    issues = check_citations(
        text=state.get("target_content", ""),
        existing_citations=state.get("existing_citations", []),
        section_type=section_type,
    )
    updated = dict(state)
    updated["citation_issues"] = [issue.model_dump() for issue in issues]
    return updated

from __future__ import annotations

from app.agents.state import ReviewState
from app.review.structure_checker import check_structure, check_uploaded_document_structure


def structure_check_node(state: ReviewState) -> ReviewState:
    if state.get("review_type") not in {"full", "structure"}:
        state["structure_issues"] = []
        return state
    issues = check_structure(
        target_content=state.get("target_content", ""),
        target_json=state.get("target_json", {}),
        output_type=state.get("target_output_type"),
    )
    if state.get("target_type") == "uploaded_document":
        issues.extend(check_uploaded_document_structure(state.get("target_content", "")))
    updated = dict(state)
    updated["structure_issues"] = [issue.model_dump() for issue in issues]
    return updated

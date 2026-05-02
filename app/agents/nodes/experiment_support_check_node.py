from __future__ import annotations

from app.agents.state import ReviewState
from app.review.experiment_checker import check_experiment_support


def experiment_support_check_node(state: ReviewState) -> ReviewState:
    if state.get("review_type") not in {"full", "experiment"}:
        state["experiment_issues"] = []
        return state
    has_real_results = bool((state.get("target_json") or {}).get("real_experiment_results"))
    issues = check_experiment_support(state.get("target_content", ""), has_real_results=has_real_results)
    updated = dict(state)
    updated["experiment_issues"] = [issue.model_dump() for issue in issues]
    return updated

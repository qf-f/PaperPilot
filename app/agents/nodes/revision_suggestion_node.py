from __future__ import annotations

from app.agents.state import ReviewState
from app.review.issue_schema import ReviewIssue
from app.review.report_builder import build_review_report


def revision_suggestion_node(state: ReviewState) -> ReviewState:
    all_issue_dicts = (
        state.get("structure_issues", [])
        + state.get("citation_issues", [])
        + state.get("experiment_issues", [])
        + state.get("writing_issues", [])
    )
    issues = [ReviewIssue(**item) for item in all_issue_dicts]
    target_info = {
        "target_type": state.get("target_type"),
        "target_id": state.get("target_id"),
        "target_title": state.get("target_title"),
        "review_type": state.get("review_type"),
        "content_length": len(state.get("target_content", "")),
    }
    markdown, review_json = build_review_report(issues=issues, target_info=target_info)
    updated = dict(state)
    updated.update(
        {
            "revision_suggestions": [issue.model_dump() for issue in issues if issue.severity in {"must_fix", "should_fix"}],
            "strengths": review_json["strengths"],
            "risks": review_json["risks"],
            "next_actions": review_json["next_actions"],
            "score": review_json["score"],
            "review_markdown": markdown,
            "review_json": review_json,
        }
    )
    return updated

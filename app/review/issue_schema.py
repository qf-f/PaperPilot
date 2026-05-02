from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


IssueSeverity = Literal["must_fix", "should_fix", "nice_to_have"]
IssueType = Literal[
    "structure",
    "citation",
    "experiment_support",
    "logic",
    "writing_quality",
    "ai_style",
    "overclaim",
    "missing_evidence",
    "formatting",
]


class ReviewIssue(BaseModel):
    issue_type: IssueType
    severity: IssueSeverity
    location: str = ""
    original_text: str = ""
    problem: str
    suggestion: str
    revised_text: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)

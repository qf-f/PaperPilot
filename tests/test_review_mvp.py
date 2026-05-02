from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.core.exceptions import AppError
from app.db.models.generated_output import GeneratedOutput
from app.db.models.project import PaperProject
from app.review.citation_checker import check_citations, extract_citation_numbers
from app.review.experiment_checker import check_experiment_support
from app.review.issue_schema import ReviewIssue
from app.review.report_builder import calculate_score
from app.review.style_checker import check_writing_style
from app.schemas.review_schema import CitationCheckResponse, ReviewRequest
from app.services.review_service import ReviewService


def test_review_request_requires_target():
    with pytest.raises(ValidationError):
        ReviewRequest(project_id="p", review_type="full")


def test_review_type_validation():
    request = ReviewRequest(project_id="p", target_output_id="o", review_type="citation")
    assert request.review_type == "citation"
    with pytest.raises(ValidationError):
        ReviewRequest(project_id="p", target_output_id="o", review_type="grammar")


def test_extract_citation_numbers():
    assert extract_citation_numbers("相关研究见 [1]、[2] 和 [10]。") == [1, 2, 10]


def test_detect_invalid_citation_number():
    issues = check_citations("已有研究提出类似方法 [1]，另有不存在引用 [99]。", [{"index": 1, "title": "A"}])
    assert any(issue.severity == "must_fix" for issue in issues)


def test_detect_experiment_overclaim():
    issues = check_experiment_support("实验表明，该方法准确率提升 18%，优于所有方法。")
    assert any(issue.issue_type in {"experiment_support", "overclaim"} for issue in issues)


def test_detect_ai_style_phrase():
    issues = check_writing_style("随着人工智能技术的快速发展，本文提出一种新方法，具有重要意义。")
    assert any(issue.issue_type == "ai_style" for issue in issues)


def test_report_builder_score_penalty():
    issues = [
        ReviewIssue(issue_type="citation", severity="must_fix", problem="引用不存在", suggestion="核对引用"),
        ReviewIssue(issue_type="ai_style", severity="should_fix", problem="表达空泛", suggestion="改写"),
    ]
    assert calculate_score(issues, content_length=1000) == 82


def test_review_output_type_review_report():
    assert "review_report" == "review_report"


def test_citation_check_response_counts():
    response = CitationCheckResponse(citation_count=2, valid_count=1, invalid_count=1, issues=[])
    assert response.invalid_count == 1


def test_review_service_rejects_wrong_project_target():
    project_id = UUID("00000000-0000-0000-0000-000000000001")
    other_project_id = UUID("00000000-0000-0000-0000-000000000002")
    output_id = UUID("00000000-0000-0000-0000-000000000003")

    class FakeSession:
        def get(self, model, key):
            if model is PaperProject:
                return SimpleNamespace(id=project_id)
            if model is GeneratedOutput:
                return SimpleNamespace(id=output_id, project_id=other_project_id)
            return None

    request = ReviewRequest(project_id=str(project_id), target_output_id=str(output_id))

    with pytest.raises(AppError, match="Target output does not belong"):
        ReviewService(FakeSession()).review(request)

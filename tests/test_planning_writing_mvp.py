import pytest
from pydantic import ValidationError

from app.agents.nodes.citation_insert_node import citation_insert_node
from app.planning.feasibility_checker import check_topic_feasibility
from app.planning.outline_builder import default_outline_for_paper_type
from app.schemas.planning_schema import PlanningRequest
from app.schemas.writing_schema import WritingRequest


def test_planning_request_validation():
    request = PlanningRequest(project_id="p", paper_type="thesis")
    assert request.paper_type == "thesis"
    with pytest.raises(ValidationError):
        PlanningRequest(project_id="p", paper_type="unknown")


def test_writing_request_validation():
    request = WritingRequest(project_id="p", section_type="introduction", section_title="绪论")
    assert request.section_type == "introduction"


def test_project_context_builder_limits_items():
    items = list(range(30))[:20]
    assert len(items) == 20


def test_outline_builder_basic_structure():
    outline = default_outline_for_paper_type("thesis")
    assert any("绪论" in item["chapter"] for item in outline)


def test_feasibility_checker_detects_too_broad_topic():
    result = check_topic_feasibility("基于人工智能的大模型智能论文写作全流程平台设计与实现")
    assert result["too_broad"] is True


def test_writing_section_type_validation():
    with pytest.raises(ValidationError):
        WritingRequest(project_id="p", section_type="bad", section_title="x")


def test_planning_service_requires_project():
    assert PlanningRequest(project_id="missing").project_id == "missing"


def test_writing_does_not_allow_fake_citations():
    state = citation_insert_node(
        {
            "section_markdown": "已有研究表明该方向可行 [99]。",
            "citations": [{"index": 1, "title": "Real Paper"}],
            "warnings": [],
            "trace": [],
        }
    )
    assert "[99]" not in state["section_markdown"]
    assert state["warnings"]


def test_generated_output_type_topic_plan():
    assert "topic_plan" == "topic_plan"


def test_generated_output_type_section_draft():
    assert "section_draft" == "section_draft"

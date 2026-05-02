import pytest
from pydantic import ValidationError

from app.agents.nodes import web_literature_search_node as search_node
from app.literature.deduplicator import deduplicate_literatures
from app.literature.normalizer import normalize_literature
from app.references.extractor import extract_reference_text
from app.references.formatter import format_reference
from app.references.parser import parse_reference_entry
from app.schemas.literature_schema import LiteratureSearchRequest
from app.schemas.reference_schema import ReferenceFormatRequest


def test_normalize_literature_title():
    item = normalize_literature(
        {
            "source_provider": "arxiv",
            "title": "  Retrieval\n Augmented   Generation  ",
            "authors": ["Alice"],
            "year": "2024-01-01",
        }
    )

    assert item["title"] == "Retrieval Augmented Generation"
    assert item["authors"] == [{"name": "Alice"}]
    assert item["year"] == 2024


def test_literature_deduplicate_by_doi():
    items = [
        {"title": "A Paper", "doi": "10.1000/ABC", "authors": [], "raw_data": {}},
        {"title": "A Paper Extended", "doi": "10.1000/abc", "authors": [{"name": "Bob"}], "raw_data": {}},
    ]

    deduped = deduplicate_literatures(items)

    assert len(deduped) == 1
    assert deduped[0]["authors"] == [{"name": "Bob"}]


def test_literature_deduplicate_by_fuzzy_title():
    items = [
        {"title": "Retrieval Augmented Generation for Question Answering", "doi": "", "authors": [], "raw_data": {}},
        {"title": "Retrieval-Augmented Generation for QA", "doi": "", "authors": [], "abstract": "x", "raw_data": {}},
    ]

    deduped = deduplicate_literatures(items, threshold=80)

    assert len(deduped) == 1
    assert deduped[0]["abstract"] == "x"


def test_reference_extractor_detects_references_section():
    reference_text, reason = extract_reference_text(
        [
            {"section_title": "Introduction", "content": "body"},
            {"section_title": "References", "content": "[1] Alice. A Paper. Journal, 2023."},
        ]
    )

    assert reason is None
    assert "Alice" in reference_text


def test_reference_parser_extracts_doi_and_year():
    item = parse_reference_entry("[1] Alice. A Useful Paper. Journal of Tests, 2023. doi:10.1000/test.123")

    assert item["doi"] == "10.1000/test.123"
    assert item["year"] == 2023


def test_reference_formatter_gbt7714():
    content = format_reference(
        {
            "title": "A Useful Paper",
            "authors": [{"name": "Alice"}],
            "venue": "Journal",
            "year": 2023,
            "doi": "10.1000/test",
        },
        "gb_t_7714",
    )

    assert "Alice" in content
    assert "A Useful Paper" in content
    assert "10.1000/test" in content


def test_literature_search_request_validation():
    request = LiteratureSearchRequest(
        project_id="00000000-0000-0000-0000-000000000001",
        search_mode="recent",
        max_results=10,
    )

    assert request.search_mode == "recent"

    with pytest.raises(ValidationError):
        LiteratureSearchRequest(project_id="x", search_mode="invalid")


def test_reference_format_request_validation():
    request = ReferenceFormatRequest(project_id="00000000-0000-0000-0000-000000000001", style="gb_t_7714")

    assert request.style == "gb_t_7714"

    with pytest.raises(ValidationError):
        ReferenceFormatRequest(project_id="x", style="mla")


def test_provider_failure_does_not_break_all_results(monkeypatch):
    class FailingProvider:
        provider_name = "failing"

        def search(self, query, max_results=10):
            raise RuntimeError("network down")

    class WorkingProvider:
        provider_name = "working"

        def search(self, query, max_results=10):
            return [
                {
                    "source_provider": "working",
                    "title": "A Real Result",
                    "authors": [],
                    "raw_data": {},
                }
            ]

    monkeypatch.setattr(search_node, "ArxivProvider", FailingProvider)
    monkeypatch.setattr(search_node, "CrossrefProvider", WorkingProvider)
    monkeypatch.setattr(search_node, "SemanticScholarProvider", FailingProvider)

    state = search_node.web_literature_search_node(
        {"generated_queries": ["rag agents"], "max_results": 3, "trace": []}
    )

    assert len(state["raw_results"]) == 1
    assert state["raw_results"][0]["title"] == "A Real Result"


def test_empty_search_results_has_clear_response(monkeypatch):
    class EmptyProvider:
        provider_name = "empty"

        def search(self, query, max_results=10):
            return []

    monkeypatch.setattr(search_node, "ArxivProvider", EmptyProvider)
    monkeypatch.setattr(search_node, "CrossrefProvider", EmptyProvider)
    monkeypatch.setattr(search_node, "SemanticScholarProvider", EmptyProvider)

    state = search_node.web_literature_search_node(
        {"generated_queries": ["unlikely query"], "max_results": 3, "trace": []}
    )

    assert state["raw_results"] == []
    assert state["trace"][-1]["output"]["raw_count"] == 0

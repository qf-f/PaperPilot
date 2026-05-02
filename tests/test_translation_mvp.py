from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.translation_schema import TerminologyUpsertRequest, TranslationRequest
from app.translation.bilingual_builder import build_translation_markdown
from app.translation.segment_builder import build_segments_from_chunks
from app.translation.terminology_store import deduplicate_terms
from app.translation.translation_checker import detect_inconsistent_terms


def test_translation_request_validation_full():
    request = TranslationRequest(project_id="p", document_id="d", range_type="full")
    assert request.translation_mode == "faithful"
    assert request.output_style == "bilingual"


def test_translation_request_validation_pages_requires_range():
    with pytest.raises(ValidationError):
        TranslationRequest(project_id="p", document_id="d", range_type="pages")
    with pytest.raises(ValidationError):
        TranslationRequest(project_id="p", document_id="d", range_type="pages", page_from=5, page_to=2)


def test_translation_request_validation_chunks_requires_range():
    with pytest.raises(ValidationError):
        TranslationRequest(project_id="p", document_id="d", range_type="chunks")
    with pytest.raises(ValidationError):
        TranslationRequest(project_id="p", document_id="d", range_type="chunks", chunk_from=3, chunk_to=1)


def test_segment_builder_filters_pages():
    chunks = [
        {"chunk_index": 0, "page_number": 1, "section_title": "Intro", "content": "page one"},
        {"chunk_index": 1, "page_number": 2, "section_title": "Method", "content": "page two"},
        {"chunk_index": 2, "page_number": 3, "section_title": "Method", "content": "page three"},
    ]
    segments = build_segments_from_chunks(chunks, range_type="pages", page_from=2, page_to=3)
    assert segments
    assert all(page in {2, 3} for segment in segments for page in segment["page_numbers"])


def test_segment_builder_filters_chunks():
    chunks = [
        {"chunk_index": 0, "page_number": 1, "section_title": "Intro", "content": "chunk zero"},
        {"chunk_index": 1, "page_number": 1, "section_title": "Intro", "content": "chunk one"},
        {"chunk_index": 2, "page_number": 2, "section_title": "Method", "content": "chunk two"},
    ]
    segments = build_segments_from_chunks(chunks, range_type="chunks", chunk_from=1, chunk_to=2)
    indexes = [idx for segment in segments for idx in segment["chunk_indexes"]]
    assert indexes == [1, 2]


def test_terminology_deduplicate():
    terms = deduplicate_terms(
        [
            {"source_term": " retrieval-augmented generation ", "target_term": "检索增强生成", "confidence_score": 0.7},
            {"source_term": "Retrieval-Augmented Generation", "target_term": "RAG", "confidence_score": 0.6},
        ]
    )
    assert len(terms) == 1
    assert terms[0]["target_term"] == "检索增强生成"


def test_bilingual_builder_outputs_bilingual_markdown():
    markdown, content_json = build_translation_markdown(
        "paper.pdf",
        [
            {
                "segment_index": 1,
                "section_title": "Abstract",
                "page_numbers": [1],
                "chunk_indexes": [0],
                "source_text": "Retrieval-augmented generation is useful.",
                "translated_text": "检索增强生成是有用的。",
            }
        ],
        "bilingual",
    )
    assert "### 原文" in markdown
    assert "### 译文" in markdown
    assert content_json["segment_count"] == 1


def test_bilingual_builder_outputs_chinese_only_markdown():
    markdown, _ = build_translation_markdown(
        "paper.pdf",
        [
            {
                "segment_index": 1,
                "section_title": "Introduction",
                "page_numbers": [2],
                "chunk_indexes": [1],
                "source_text": "English text.",
                "translated_text": "中文译文。",
            }
        ],
        "chinese_only",
    )
    assert "### 原文" not in markdown
    assert "中文译文" in markdown


def test_translation_checker_warns_inconsistent_terms():
    warnings = detect_inconsistent_terms(
        [
            {
                "segment_index": 1,
                "source_text": "retrieval-augmented generation improves answers.",
                "translated_text": "RAG 改善回答。",
            }
        ],
        {"retrieval-augmented generation": "检索增强生成"},
    )
    assert warnings


def test_terminology_upsert_schema():
    request = TerminologyUpsertRequest(
        source_term="retrieval-augmented generation",
        target_term="检索增强生成",
        category="method",
    )
    assert request.category == "method"

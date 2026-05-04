import pytest

from app.rag.chunker import chunk_text_blocks
from app.rag.chunkers import FixedChunker, HeadingAwareChunker


def test_fixed_chunker_matches_compatible_entrypoint():
    blocks = [
        {
            "page_number": 2,
            "section_title": "Intro",
            "text": "abcdefghijklmnopqrstuvwxyz",
        }
    ]

    fixed_chunks = FixedChunker(chunk_size=10, overlap=2).chunk(blocks)
    compatible_chunks = chunk_text_blocks(blocks, chunk_size=10, overlap=2)

    assert fixed_chunks == compatible_chunks
    assert [chunk["content"] for chunk in fixed_chunks] == [
        "abcdefghij",
        "ijklmnopqr",
        "qrstuvwxyz",
    ]
    assert [chunk["chunk_index"] for chunk in fixed_chunks] == [0, 1, 2]
    assert fixed_chunks[0]["metadata"]["chunk_strategy"] == "fixed"


def test_heading_aware_chunker_does_not_merge_across_sections():
    blocks = [
        {
            "section_title": "引言",
            "section_path": ["引言"],
            "page_number": 1,
            "char_start": 0,
            "char_end": 4,
            "text": "引言正文",
        },
        {
            "section_title": "结论",
            "section_path": ["结论"],
            "page_number": 3,
            "char_start": 10,
            "char_end": 14,
            "is_reference_section": True,
            "text": "结论正文",
        },
    ]

    chunks = HeadingAwareChunker(chunk_size=100, overlap=10).chunk(blocks)

    assert len(chunks) == 2
    assert [chunk["chunk_index"] for chunk in chunks] == [0, 1]
    assert chunks[0]["content"].startswith("[Section: 引言]\n")
    assert chunks[1]["content"].startswith("[Section: 结论]\n")
    assert chunks[0]["metadata"]["section_path"] == ["引言"]
    assert chunks[1]["metadata"]["section_path"] == ["结论"]
    assert chunks[1]["metadata"]["is_reference_section"] is True
    assert chunks[1]["metadata"]["char_start"] == 10
    assert chunks[1]["metadata"]["char_end"] == 14
    assert chunks[1]["metadata"]["chunk_strategy"] == "heading"


def test_invalid_overlap_still_raises_value_error():
    with pytest.raises(ValueError, match="overlap must be smaller than chunk_size"):
        FixedChunker(chunk_size=10, overlap=10).chunk([{"text": "abc"}])

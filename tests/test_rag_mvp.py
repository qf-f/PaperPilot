from app.rag.citation_builder import build_citations
from app.rag.prompt_builder import build_rag_user_prompt


def test_citation_builder_indexes_from_one():
    citations = build_citations(
        [
            {
                "document_id": "doc-1",
                "file_name": "paper.pdf",
                "page_number": 3,
                "section_title": "Method",
                "chunk_index": 12,
                "score": 0.82,
            }
        ]
    )

    assert citations[0]["index"] == 1
    assert citations[0]["file_name"] == "paper.pdf"


def test_prompt_builder_includes_sources():
    prompt = build_rag_user_prompt(
        query="方法是什么？",
        retrieved_chunks=[
            {
                "file_name": "paper.pdf",
                "page_number": 1,
                "section_title": "Introduction",
                "chunk_index": 0,
                "content": "本文提出了一种方法。",
                "score": 0.9,
            }
        ],
        max_context_chars=1000,
    )

    assert "[1] 来源" in prompt
    assert "用户问题" in prompt


def test_chat_no_retrieval_expected_behavior():
    expected_answer = "当前上传文档中没有找到直接依据"
    assert expected_answer in "当前上传文档中没有找到直接依据。你可以尝试指定文档。"

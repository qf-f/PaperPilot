from __future__ import annotations

from typing import Any

from app.rag.retriever import RetrievedChunk


def _get_value(chunk: RetrievedChunk | dict[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(chunk, RetrievedChunk):
        return getattr(chunk, key, default)
    return chunk.get(key, default)


def build_citations(retrieved_chunks: list[RetrievedChunk | dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for index, chunk in enumerate(retrieved_chunks, start=1):
        citations.append(
            {
                "index": index,
                "document_id": str(_get_value(chunk, "document_id", "")),
                "file_name": str(_get_value(chunk, "file_name", "")),
                "page_number": _get_value(chunk, "page_number"),
                "section_title": str(_get_value(chunk, "section_title", "") or ""),
                "chunk_index": int(_get_value(chunk, "chunk_index", 0)),
                "score": round(float(_get_value(chunk, "score", 0.0)), 4),
            }
        )
    return citations

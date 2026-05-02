from __future__ import annotations

from typing import Any


def clip_text(value: str | None, max_chars: int = 2000) -> str:
    text = (value or "").strip()
    return text[:max_chars]


def compact_generated_output(output: Any, max_chars: int = 2000) -> dict[str, Any]:
    return {
        "id": str(output.id),
        "output_type": output.output_type,
        "title": output.title or "",
        "content_markdown": clip_text(output.content_markdown, max_chars=max_chars),
        "content_json": output.content_json or {},
        "created_at": output.created_at.isoformat() if output.created_at else None,
    }


def compact_literature(item: Any, index: int) -> dict[str, Any]:
    return {
        "citation_index": index,
        "id": str(item.id),
        "title": item.title,
        "authors": item.authors or [],
        "year": item.year,
        "venue": item.venue or "",
        "doi": item.doi or "",
        "url": item.url or "",
        "abstract": clip_text(item.abstract, max_chars=800),
        "relevance_score": item.relevance_score,
        "recommendation_reason": item.recommendation_reason or "",
    }


def compact_reference(item: Any, index: int) -> dict[str, Any]:
    return {
        "citation_index": index,
        "id": str(item.id),
        "title": item.title or "",
        "authors": item.authors or [],
        "year": item.year,
        "venue": item.venue or "",
        "doi": item.doi or "",
        "url": item.url or "",
        "gb_t_7714": item.gb_t_7714 or "",
    }

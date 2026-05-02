from __future__ import annotations

from typing import Any


def literature_to_markdown_table(items: list[dict[str, Any]]) -> str:
    lines = [
        "| 标题 | 年份 | 来源 | DOI/URL | 推荐理由 |",
        "|---|---:|---|---|---|",
    ]
    for item in items:
        title = str(item.get("title", "")).replace("|", " ")
        year = item.get("year") or ""
        venue = item.get("venue") or item.get("source_provider") or ""
        link = item.get("doi") or item.get("url") or ""
        reason = str(item.get("recommendation_reason", "")).replace("|", " ")
        lines.append(f"| {title} | {year} | {venue} | {link} | {reason} |")
    return "\n".join(lines)


def literature_to_api_item(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "title": item.title,
        "authors": item.authors or [],
        "year": item.year,
        "venue": item.venue or "",
        "doi": item.doi or "",
        "url": item.url or "",
        "pdf_url": item.pdf_url or "",
        "source_provider": item.source_provider,
        "relevance_score": item.relevance_score,
        "recommendation_reason": item.recommendation_reason or "",
    }

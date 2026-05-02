from __future__ import annotations

from typing import Any

from rapidfuzz import fuzz


def recommend_references(
    topic: str,
    literatures: list[Any],
    existing_references: list[Any],
    limit: int = 10,
) -> list[dict[str, Any]]:
    existing_dois = {(ref.doi or "").lower() for ref in existing_references if getattr(ref, "doi", None)}
    existing_titles = [str(getattr(ref, "title", "") or "").lower() for ref in existing_references]
    recommendations = []

    for lit in literatures:
        if lit.doi and lit.doi.lower() in existing_dois:
            continue
        if any(fuzz.token_set_ratio(lit.title.lower(), title) >= 92 for title in existing_titles if title):
            continue

        title_score = fuzz.token_set_ratio(topic.lower(), lit.title.lower()) / 100 if topic else 0.4
        reason_parts = []
        usage = "related_work"
        combined = f"{lit.title} {lit.abstract or ''}".lower()
        if lit.year and lit.year >= 2024:
            title_score += 0.12
            reason_parts.append("近三年新工作")
        if "survey" in combined or "review" in combined:
            usage = "background"
            reason_parts.append("可作为综述或背景引用")
        if "baseline" in combined or "benchmark" in combined:
            usage = "baseline"
            reason_parts.append("可作为 baseline 或对比方法")
        if "method" in combined or "model" in combined or "framework" in combined:
            usage = "method"
            reason_parts.append("可支撑方法设计")
        if not reason_parts:
            reason_parts.append("与研究主题相关")

        recommendations.append(
            {
                "literature_id": str(lit.id),
                "title": lit.title,
                "year": lit.year,
                "reason": "；".join(reason_parts),
                "suggested_usage": usage,
                "score": round(min(title_score, 1.0), 4),
            }
        )

    return sorted(recommendations, key=lambda item: item["score"], reverse=True)[:limit]

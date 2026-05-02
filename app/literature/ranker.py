from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rapidfuzz import fuzz


SURVEY_TERMS = ["survey", "review", "综述", "研究现状"]
BASELINE_TERMS = ["baseline", "benchmark", "method", "approach", "model", "framework"]


def rank_literatures(
    items: list[dict[str, Any]],
    query: str,
    search_mode: str = "general",
    recent_years: int = 3,
) -> list[dict[str, Any]]:
    ranked = []
    current_year = datetime.now(UTC).year
    for item in items:
        score, reasons = score_literature(item, query, search_mode, current_year, recent_years)
        updated = dict(item)
        updated["relevance_score"] = round(score, 4)
        updated["recommendation_reason"] = "；".join(reasons) if reasons else "与检索词存在一定相关性"
        ranked.append(updated)
    return sorted(ranked, key=lambda x: x.get("relevance_score") or 0, reverse=True)


def score_literature(
    item: dict[str, Any],
    query: str,
    search_mode: str,
    current_year: int,
    recent_years: int,
) -> tuple[float, list[str]]:
    title = str(item.get("title", ""))
    abstract = str(item.get("abstract", ""))
    year = item.get("year")
    provider = item.get("source_provider", "")
    citation_count = item.get("citation_count") or 0

    title_score = fuzz.token_set_ratio(query.lower(), title.lower()) / 100
    abstract_score = fuzz.partial_ratio(query.lower(), abstract.lower()) / 100 if abstract else 0
    score = title_score * 0.45 + abstract_score * 0.25
    reasons = []

    if title_score >= 0.45:
        reasons.append("标题与主题相关")
    if abstract_score >= 0.45:
        reasons.append("摘要与主题相关")

    if year and year >= current_year - recent_years + 1:
        score += 0.12
        reasons.append(f"近{recent_years}年新工作")

    combined = f"{title} {abstract}".lower()
    if any(term in combined for term in SURVEY_TERMS):
        if search_mode == "survey":
            score += 0.18
        reasons.append("可能是综述类论文")

    if any(term in combined for term in BASELINE_TERMS):
        if search_mode == "baseline":
            score += 0.12
        reasons.append("可能可作为 baseline 或方法对比")

    if search_mode == "classic" and citation_count:
        score += min(citation_count / 1000, 0.2)
        reasons.append("具有一定引用影响力")

    if provider in {"crossref", "semantic_scholar", "arxiv"}:
        score += 0.05

    return min(score, 1.0), reasons

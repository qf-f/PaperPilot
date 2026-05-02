from __future__ import annotations

import re
from typing import Any


def normalize_source_term(term: str) -> str:
    normalized = re.sub(r"\s+", " ", (term or "").strip())
    normalized = normalized.strip(" .,;:()[]{}")
    return normalized


def source_key(term: str) -> str:
    return normalize_source_term(term).casefold()


def deduplicate_terms(terms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for term in terms:
        source_term = normalize_source_term(str(term.get("source_term") or ""))
        target_term = str(term.get("target_term") or "").strip()
        if not source_term or len(source_term) < 2:
            continue
        key = source_key(source_term)
        normalized = {
            "source_term": source_term,
            "target_term": target_term or source_term,
            "explanation": str(term.get("explanation") or "").strip(),
            "category": str(term.get("category") or "general").strip() or "general",
            "confidence_score": _safe_confidence(term.get("confidence_score")),
            "source": str(term.get("source") or "extracted").strip() or "extracted",
        }
        existing = by_key.get(key)
        if existing is None or (normalized["confidence_score"] or 0) > (existing.get("confidence_score") or 0):
            by_key[key] = normalized
        elif existing and not existing.get("target_term") and normalized["target_term"]:
            existing["target_term"] = normalized["target_term"]
    return list(by_key.values())


def merge_terms(existing_terms: list[dict[str, Any]], new_terms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = {source_key(item.get("source_term", "")): dict(item) for item in deduplicate_terms(existing_terms)}
    for item in deduplicate_terms(new_terms):
        key = source_key(item["source_term"])
        if key not in merged:
            merged[key] = item
            continue
        existing = merged[key]
        if not existing.get("target_term"):
            existing["target_term"] = item.get("target_term") or existing["source_term"]
        if (item.get("confidence_score") or 0) > (existing.get("confidence_score") or 0):
            existing["explanation"] = item.get("explanation") or existing.get("explanation", "")
            existing["category"] = item.get("category") or existing.get("category", "general")
            existing["confidence_score"] = item.get("confidence_score")
    return list(merged.values())


def build_term_map(terms: list[dict[str, Any]]) -> dict[str, str]:
    term_map: dict[str, str] = {}
    for item in deduplicate_terms(terms):
        source_term = item.get("source_term", "")
        target_term = item.get("target_term", "")
        if source_term and target_term:
            term_map[source_term] = target_term
    return term_map


def _safe_confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.6
    return max(0.0, min(1.0, number))

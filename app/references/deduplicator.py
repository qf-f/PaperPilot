from __future__ import annotations

from typing import Any

from rapidfuzz import fuzz


def deduplicate_references(items: list[dict[str, Any]], threshold: float = 0.9) -> list[dict[str, Any]]:
    score_threshold = threshold * 100 if threshold <= 1 else threshold
    deduped: list[dict[str, Any]] = []
    doi_index: dict[str, int] = {}

    for item in items:
        doi = (item.get("doi") or "").lower().strip()
        if doi and doi in doi_index:
            deduped[doi_index[doi]] = merge_reference(deduped[doi_index[doi]], item)
            continue

        matched_index = None
        for index, existing in enumerate(deduped):
            title_score = fuzz.token_set_ratio(
                str(item.get("title", "")).lower(),
                str(existing.get("title", "")).lower(),
            )
            raw_score = fuzz.token_set_ratio(
                str(item.get("raw_text", "")).lower(),
                str(existing.get("raw_text", "")).lower(),
            )
            if max(title_score, raw_score) >= score_threshold:
                matched_index = index
                break

        if matched_index is not None:
            deduped[matched_index] = merge_reference(deduped[matched_index], item)
        else:
            if doi:
                doi_index[doi] = len(deduped)
            deduped.append(item)

    return deduped


def merge_reference(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    merged = dict(primary)
    for key in ("title", "year", "venue", "doi", "url"):
        if not merged.get(key) and secondary.get(key):
            merged[key] = secondary[key]
    if not merged.get("authors") and secondary.get("authors"):
        merged["authors"] = secondary["authors"]
    merged["confidence_score"] = max(primary.get("confidence_score") or 0, secondary.get("confidence_score") or 0)
    return merged

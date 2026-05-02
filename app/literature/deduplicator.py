from __future__ import annotations

from typing import Any

from rapidfuzz import fuzz

from app.literature.normalizer import normalize_doi


def deduplicate_literatures(items: list[dict[str, Any]], threshold: int = 90) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    doi_index: dict[str, int] = {}

    for item in items:
        title = item.get("title", "")
        if not title:
            continue
        doi = normalize_doi(item.get("doi"))
        if doi and doi in doi_index:
            deduped[doi_index[doi]] = merge_literature(deduped[doi_index[doi]], item)
            continue

        matched_index = None
        if not doi:
            for index, existing in enumerate(deduped):
                if existing.get("doi"):
                    continue
                score = fuzz.token_set_ratio(title.lower(), str(existing.get("title", "")).lower())
                if score >= threshold:
                    matched_index = index
                    break

        if matched_index is not None:
            deduped[matched_index] = merge_literature(deduped[matched_index], item)
        else:
            if doi:
                doi_index[doi] = len(deduped)
            deduped.append(item)

    return deduped


def merge_literature(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    merged = dict(primary)
    for key in ("abstract", "doi", "url", "pdf_url", "venue", "external_id"):
        if not merged.get(key) and secondary.get(key):
            merged[key] = secondary[key]

    merged["authors"] = _merge_list_of_dicts(primary.get("authors", []), secondary.get("authors", []), "name")
    merged["categories"] = _merge_lists(primary.get("categories", []), secondary.get("categories", []))
    merged["keywords"] = _merge_lists(primary.get("keywords", []), secondary.get("keywords", []))

    if not merged.get("year") and secondary.get("year"):
        merged["year"] = secondary["year"]
    if not merged.get("published_date") and secondary.get("published_date"):
        merged["published_date"] = secondary["published_date"]

    providers = []
    for provider in [primary.get("source_provider"), secondary.get("source_provider")]:
        if isinstance(provider, list):
            providers.extend(provider)
        elif provider:
            providers.append(provider)
    merged["source_provider"] = providers[0] if providers else primary.get("source_provider", "")
    merged["raw_data"] = {
        "sources": _merge_lists(
            primary.get("raw_data", {}).get("sources", [primary.get("raw_data", {})]),
            secondary.get("raw_data", {}).get("sources", [secondary.get("raw_data", {})]),
        )
    }
    return merged


def _merge_lists(first: list, second: list) -> list:
    merged = []
    for item in (first or []) + (second or []):
        if item not in merged:
            merged.append(item)
    return merged


def _merge_list_of_dicts(first: list[dict], second: list[dict], key: str) -> list[dict]:
    merged: list[dict] = []
    seen = set()
    for item in (first or []) + (second or []):
        value = item.get(key)
        if value and value not in seen:
            seen.add(value)
            merged.append(item)
    return merged

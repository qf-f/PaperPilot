from __future__ import annotations

import re
from datetime import date
from typing import Any

from dateutil.parser import parse as parse_date


def normalize_literature(item: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(item)
    normalized["title"] = clean_text(item.get("title", ""))
    normalized["abstract"] = clean_text(item.get("abstract", ""))
    normalized["doi"] = normalize_doi(item.get("doi"))
    normalized["authors"] = normalize_authors(item.get("authors", []))
    normalized["year"] = normalize_year(item.get("year") or item.get("published_date"))
    normalized["published_date"] = normalize_date(item.get("published_date"))
    normalized["url"] = clean_url(item.get("url", ""))
    normalized["pdf_url"] = clean_url(item.get("pdf_url", ""))
    normalized["venue"] = clean_text(item.get("venue", ""))
    normalized["categories"] = item.get("categories") or []
    normalized["keywords"] = item.get("keywords") or []
    normalized["source_provider"] = item.get("source_provider", "")
    normalized["raw_data"] = make_json_safe(item.get("raw_data") or {})
    return normalized


def normalize_literatures(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_literature(item) for item in items if clean_text(item.get("title", ""))]


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_doi(value: Any) -> str:
    doi = clean_text(value).lower()
    doi = doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/").removeprefix("doi:")
    return doi.strip()


def normalize_authors(authors: Any) -> list[dict[str, str]]:
    if not authors:
        return []
    if isinstance(authors, str):
        return [{"name": clean_text(authors)}] if clean_text(authors) else []
    normalized = []
    for author in authors:
        if isinstance(author, dict):
            name = clean_text(author.get("name") or " ".join(str(v) for v in author.values() if v))
        else:
            name = clean_text(author)
        if name:
            normalized.append({"name": name})
    return normalized


def normalize_year(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value if 1800 <= value <= 2100 else None
    match = re.search(r"(19|20)\d{2}", str(value))
    return int(match.group(0)) if match else None


def normalize_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return parse_date(str(value)).date()
    except (ValueError, TypeError):
        return None


def clean_url(value: Any) -> str:
    return clean_text(value)


def make_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]
    return str(value)

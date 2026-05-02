from __future__ import annotations

from datetime import date

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.literature.providers.base import LiteratureResult, empty_literature_result


class CrossrefProvider:
    provider_name = "crossref"

    def __init__(self) -> None:
        self.settings = get_settings()

    def search(self, query: str, max_results: int = 10) -> list[LiteratureResult]:
        if not query.strip():
            return []
        return self._request(query=query, max_results=max_results)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    def _request(self, query: str, max_results: int) -> list[LiteratureResult]:
        params = {"query.bibliographic": query, "rows": max_results}
        try:
            with httpx.Client(timeout=self.settings.literature_search_timeout_seconds) as client:
                response = client.get(self.settings.crossref_base_url, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"Crossref request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Crossref request failed: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError(f"Crossref returned invalid JSON: {exc}") from exc

        items = payload.get("message", {}).get("items", [])
        results: list[LiteratureResult] = []
        for raw in items:
            try:
                title = _first(raw.get("title"))
                if not title:
                    continue
                published_date = _extract_date(raw)
                venue = _first(raw.get("container-title")) or raw.get("publisher", "") or ""
                item = empty_literature_result(self.provider_name)
                item.update(
                    {
                        "external_id": raw.get("DOI", "") or raw.get("URL", ""),
                        "title": _clean_text(title),
                        "abstract": _clean_abstract(raw.get("abstract", "")),
                        "authors": _parse_authors(raw.get("author", [])),
                        "year": published_date.year if published_date else None,
                        "published_date": published_date.isoformat() if published_date else None,
                        "venue": venue,
                        "doi": raw.get("DOI", "") or "",
                        "url": raw.get("URL", "") or "",
                        "pdf_url": "",
                        "categories": raw.get("subject", []) or [],
                        "raw_data": raw,
                    }
                )
                results.append(item)
            except Exception:
                continue
        return results


def _first(value: list | None) -> str:
    if isinstance(value, list) and value:
        return str(value[0])
    return ""


def _extract_date(raw: dict) -> date | None:
    for key in ("published-print", "published-online", "published", "issued"):
        date_parts = raw.get(key, {}).get("date-parts")
        if date_parts and date_parts[0]:
            parts = date_parts[0]
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else 1
            day = int(parts[2]) if len(parts) > 2 else 1
            return date(year, month, day)
    return None


def _parse_authors(authors: list[dict]) -> list[dict[str, str]]:
    parsed = []
    for author in authors or []:
        given = author.get("given", "")
        family = author.get("family", "")
        name = " ".join(part for part in [given, family] if part).strip()
        if name:
            parsed.append({"name": name})
    return parsed


def _clean_text(value: str) -> str:
    return " ".join((value or "").split())


def _clean_abstract(value: str) -> str:
    if not value:
        return ""
    text = BeautifulSoup(value, "html.parser").get_text(" ")
    return _clean_text(text)

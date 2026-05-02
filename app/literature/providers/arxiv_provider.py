from __future__ import annotations

from datetime import date

import feedparser
import httpx
from dateutil.parser import parse as parse_date
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.literature.providers.base import LiteratureResult, empty_literature_result


class ArxivProvider:
    provider_name = "arxiv"

    def __init__(self) -> None:
        self.settings = get_settings()

    def search(self, query: str, max_results: int = 10) -> list[LiteratureResult]:
        if not query.strip():
            return []
        return self._request(query=query, max_results=max_results)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    def _request(self, query: str, max_results: int) -> list[LiteratureResult]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        try:
            with httpx.Client(timeout=self.settings.literature_search_timeout_seconds) as client:
                response = client.get(self.settings.arxiv_base_url, params=params)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"arXiv request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"arXiv request failed: {exc}") from exc

        feed = feedparser.parse(response.text)
        results: list[LiteratureResult] = []
        for entry in feed.entries:
            item = empty_literature_result(self.provider_name)
            published_date = _parse_date(getattr(entry, "published", None))
            pdf_url = ""
            for link in getattr(entry, "links", []):
                if link.get("type") == "application/pdf":
                    pdf_url = link.get("href", "")

            item.update(
                {
                    "external_id": getattr(entry, "id", ""),
                    "title": _clean_text(getattr(entry, "title", "")),
                    "abstract": _clean_text(getattr(entry, "summary", "")),
                    "authors": [{"name": author.get("name", "")} for author in getattr(entry, "authors", [])],
                    "year": published_date.year if published_date else None,
                    "published_date": published_date.isoformat() if published_date else None,
                    "venue": "arXiv",
                    "doi": getattr(entry, "arxiv_doi", "") if hasattr(entry, "arxiv_doi") else "",
                    "url": getattr(entry, "link", "") or getattr(entry, "id", ""),
                    "pdf_url": pdf_url,
                    "categories": [tag.get("term", "") for tag in getattr(entry, "tags", [])],
                    "raw_data": dict(entry),
                }
            )
            if item["title"]:
                results.append(item)
        return results


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return parse_date(value).date()
    except (ValueError, TypeError):
        return None


def _clean_text(value: str) -> str:
    return " ".join((value or "").split())

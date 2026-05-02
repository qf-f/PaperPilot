from __future__ import annotations

import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.literature.providers.base import LiteratureResult, empty_literature_result


logger = logging.getLogger(__name__)


class SemanticScholarProvider:
    provider_name = "semantic_scholar"

    def __init__(self) -> None:
        self.settings = get_settings()

    def search(self, query: str, max_results: int = 10) -> list[LiteratureResult]:
        if not query.strip():
            return []
        return self._request(query=query, max_results=max_results)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
    def _request(self, query: str, max_results: int) -> list[LiteratureResult]:
        url = f"{self.settings.semantic_scholar_base_url.rstrip('/')}/paper/search"
        fields = ",".join(
            [
                "title",
                "abstract",
                "authors",
                "year",
                "venue",
                "url",
                "externalIds",
                "citationCount",
                "influentialCitationCount",
                "fieldsOfStudy",
            ]
        )
        headers = {}
        if self.settings.semantic_scholar_api_key:
            headers["x-api-key"] = self.settings.semantic_scholar_api_key

        try:
            with httpx.Client(timeout=self.settings.literature_search_timeout_seconds) as client:
                response = client.get(
                    url,
                    params={"query": query, "limit": max_results, "fields": fields},
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"Semantic Scholar request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Semantic Scholar request failed: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError(f"Semantic Scholar returned invalid JSON: {exc}") from exc

        results: list[LiteratureResult] = []
        for raw in payload.get("data", []) or []:
            title = raw.get("title", "") or ""
            if not title:
                continue
            external_ids = raw.get("externalIds") or {}
            item = empty_literature_result(self.provider_name)
            item.update(
                {
                    "external_id": raw.get("paperId", "") or external_ids.get("DOI", ""),
                    "title": " ".join(title.split()),
                    "abstract": " ".join((raw.get("abstract") or "").split()),
                    "authors": [{"name": a.get("name", "")} for a in raw.get("authors", []) if a.get("name")],
                    "year": raw.get("year"),
                    "published_date": None,
                    "venue": raw.get("venue", "") or "",
                    "doi": external_ids.get("DOI", "") or "",
                    "url": raw.get("url", "") or "",
                    "pdf_url": "",
                    "categories": raw.get("fieldsOfStudy") or [],
                    "citation_count": raw.get("citationCount"),
                    "influential_citation_count": raw.get("influentialCitationCount"),
                    "raw_data": raw,
                }
            )
            results.append(item)
        return results

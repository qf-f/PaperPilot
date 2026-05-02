from __future__ import annotations

from typing import Any, Protocol


LiteratureResult = dict[str, Any]


class LiteratureSearchProvider(Protocol):
    provider_name: str

    def search(self, query: str, max_results: int = 10) -> list[LiteratureResult]:
        pass


def empty_literature_result(source_provider: str) -> LiteratureResult:
    return {
        "source_provider": source_provider,
        "external_id": "",
        "title": "",
        "abstract": "",
        "authors": [],
        "year": None,
        "published_date": None,
        "venue": "",
        "doi": "",
        "url": "",
        "pdf_url": "",
        "categories": [],
        "keywords": [],
        "citation_count": None,
        "influential_citation_count": None,
        "raw_data": {},
    }

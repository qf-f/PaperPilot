from __future__ import annotations

import logging
from time import perf_counter

from fastapi import status

from app.agents.state import LiteratureSearchState
from app.core.exceptions import AppError
from app.literature.providers.arxiv_provider import ArxivProvider
from app.literature.providers.crossref_provider import CrossrefProvider
from app.literature.providers.semantic_scholar_provider import SemanticScholarProvider


logger = logging.getLogger(__name__)


def web_literature_search_node(state: LiteratureSearchState) -> LiteratureSearchState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    providers = [ArxivProvider(), CrossrefProvider(), SemanticScholarProvider()]
    raw_results = []
    provider_errors = []
    queries = state.get("generated_queries", [])
    max_results = int(state.get("max_results", 10))

    for provider in providers:
        provider_count = 0
        provider_error_messages = []
        for query in queries:
            try:
                results = provider.search(query, max_results=max_results)
                provider_count += len(results)
                raw_results.extend(results)
            except Exception as exc:
                error = {"provider": provider.provider_name, "query": query, "error": str(exc)}
                provider_errors.append(error)
                provider_error_messages.append(str(exc))
                logger.warning("provider failed provider=%s error=%s", provider.provider_name, exc)
        trace.append(
            {
                "tool_name": f"provider:{provider.provider_name}",
                "input": {"queries": queries, "max_results": max_results},
                "output": {"count": provider_count},
                "latency_ms": None,
                "status": "failed" if provider_count == 0 and provider_error_messages else "success",
                "error_message": "; ".join(provider_error_messages) if provider_error_messages else None,
            }
        )

    if not raw_results and len(provider_errors) >= len(providers) * max(1, len(queries)):
        raise AppError(f"All literature providers failed: {provider_errors}", status.HTTP_502_BAD_GATEWAY)

    elapsed_ms = int((perf_counter() - started_at) * 1000)
    trace.append(
        {
            "tool_name": "web_literature_search",
            "input": {"queries": queries},
            "output": {"raw_count": len(raw_results), "provider_errors": provider_errors},
            "latency_ms": elapsed_ms,
            "status": "success",
            "error_message": None,
        }
    )
    updated = dict(state)
    updated.update({"raw_results": raw_results, "trace": trace})
    return updated

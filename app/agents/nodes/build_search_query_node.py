from __future__ import annotations

import json
from time import perf_counter
from uuid import UUID

from fastapi import status
from sqlalchemy import select

from app.agents.prompts.literature_search_prompt import BUILD_SEARCH_QUERY_PROMPT
from app.agents.state import LiteratureSearchState
from app.core.exceptions import AppError
from app.db.models.generated_output import GeneratedOutput
from app.db.models.project import PaperProject
from app.db.session import SessionLocal
from app.services.llm_service import LLMService, LLMServiceError


def build_search_query_node(state: LiteratureSearchState) -> LiteratureSearchState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    project_id = _parse_uuid(state.get("project_id", ""), "project_id")
    query = (state.get("query") or "").strip()

    with SessionLocal() as db:
        project = db.get(PaperProject, project_id)
        if project is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)
        latest_summary = db.execute(
            select(GeneratedOutput)
            .where(
                GeneratedOutput.project_id == project_id,
                GeneratedOutput.output_type == "paper_summary",
                GeneratedOutput.status == "finished",
            )
            .order_by(GeneratedOutput.created_at.desc())
            .limit(1)
        ).scalars().first()

        project_info = {
            "title": project.title,
            "research_direction": project.research_direction,
            "keywords": project.keywords or [],
            "latest_summary": (latest_summary.content_markdown[:2000] if latest_summary and latest_summary.content_markdown else ""),
        }

    if query:
        queries = [query]
    else:
        if not project_info["title"] and not project_info["keywords"]:
            raise AppError("Query is empty and project has no title/keywords", status.HTTP_400_BAD_REQUEST)
        queries = _generate_queries_with_llm(project_info)

    elapsed_ms = int((perf_counter() - started_at) * 1000)
    trace.append(
        {
            "tool_name": "build_search_query",
            "input": {"query": query, "project_id": str(project_id)},
            "output": {"generated_queries": queries},
            "latency_ms": elapsed_ms,
            "status": "success",
            "error_message": None,
        }
    )
    updated = dict(state)
    updated.update({"project_info": project_info, "generated_queries": queries, "trace": trace})
    return updated


def _generate_queries_with_llm(project_info: dict) -> list[str]:
    fallback = " ".join(
        [project_info.get("title") or "", project_info.get("research_direction") or "", " ".join(project_info.get("keywords") or [])]
    ).strip()
    try:
        response = LLMService().generate(
            system_prompt=BUILD_SEARCH_QUERY_PROMPT,
            user_prompt=json.dumps(project_info, ensure_ascii=False),
        )
        parsed = json.loads(response.strip().strip("`"))
        queries = [str(item).strip() for item in parsed if str(item).strip()]
        return queries[:5] or [fallback]
    except (LLMServiceError, json.JSONDecodeError, TypeError):
        return [fallback]


def _parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

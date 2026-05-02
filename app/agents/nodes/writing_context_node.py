from __future__ import annotations

from time import perf_counter
from uuid import UUID

from sqlalchemy import select

from app.agents.state import WritingState
from app.core.exceptions import AppError
from app.db.models.generated_output import GeneratedOutput
from app.db.session import SessionLocal
from app.services.project_context_service import ProjectContextService


def writing_context_node(state: WritingState) -> WritingState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    with SessionLocal() as db:
        context = ProjectContextService(db).build_context(state["project_id"])
        selected_plan = _load_selected_plan(db, state)

    citations = _build_citations(context)
    warnings = []
    if state.get("section_type") == "related_work" and not context.get("literatures"):
        warnings.append("当前项目文献库较少，相关工作草稿只能作为框架，建议先执行联网文献检索。")
    if not citations:
        warnings.append("当前项目缺少可用文献或参考文献，草稿将减少引用并避免虚构引用。")

    writing_context = {
        "project": context.get("project", {}),
        "selected_plan": selected_plan,
        "literature_reviews": context.get("literature_reviews", []),
        "paper_summaries": context.get("paper_summaries", []),
        "literatures": context.get("literatures", []),
        "references": context.get("references", []),
        "citations": citations,
    }

    trace.append(
        {
            "tool_name": "writing_context",
            "input": {"project_id": state["project_id"], "plan_output_id": state.get("plan_output_id")},
            "output": {"citation_count": len(citations), "has_plan": bool(selected_plan)},
            "latency_ms": int((perf_counter() - started_at) * 1000),
            "status": "success",
            "error_message": None,
        }
    )
    updated = dict(state)
    updated.update({"project_context": context, "selected_plan": selected_plan, "writing_context": writing_context, "citations": citations, "warnings": warnings, "trace": trace})
    return updated


def _load_selected_plan(db, state: WritingState) -> dict | None:
    plan_id = state.get("plan_output_id")
    if plan_id:
        output = db.get(GeneratedOutput, UUID(str(plan_id)))
        if output is None or output.output_type != "topic_plan":
            raise AppError("Plan output not found")
    else:
        output = db.execute(
            select(GeneratedOutput)
            .where(
                GeneratedOutput.project_id == UUID(str(state["project_id"])),
                GeneratedOutput.output_type == "topic_plan",
                GeneratedOutput.status == "finished",
            )
            .order_by(GeneratedOutput.created_at.desc())
            .limit(1)
        ).scalars().first()
    if output is None:
        return None
    return {
        "id": str(output.id),
        "title": output.title,
        "content_markdown": output.content_markdown or "",
        "content_json": output.content_json or {},
    }


def _build_citations(context: dict) -> list[dict]:
    citations = []
    index = 1
    for item in context.get("literatures", [])[:12]:
        citations.append(
            {
                "index": index,
                "source_type": "literature",
                "source_id": item.get("id"),
                "title": item.get("title"),
                "year": item.get("year"),
                "venue": item.get("venue"),
                "doi": item.get("doi"),
                "url": item.get("url"),
            }
        )
        index += 1
    for item in context.get("references", [])[:8]:
        if not item.get("title"):
            continue
        citations.append(
            {
                "index": index,
                "source_type": "reference",
                "source_id": item.get("id"),
                "title": item.get("title"),
                "year": item.get("year"),
                "venue": item.get("venue"),
                "doi": item.get("doi"),
                "url": item.get("url"),
            }
        )
        index += 1
    return citations

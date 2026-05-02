from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

from fastapi import status

from app.agents.prompts.paper_summary_prompt import SECTION_SUMMARY_SYSTEM_PROMPT
from app.agents.state import PaperSummaryState
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.paper.section_detector import group_chunks_by_section
from app.paper.summary_builder import build_chunk_context, parse_section_summary_response
from app.services.llm_service import LLMService, LLMServiceError


logger = logging.getLogger(__name__)


def section_summary_node(state: PaperSummaryState) -> PaperSummaryState:
    settings = get_settings()
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    chunks = state.get("chunks", [])
    groups = group_chunks_by_section(chunks)

    try:
        llm = LLMService()
        section_summaries: list[dict[str, Any]] = []

        for group in groups:
            group_started_at = perf_counter()
            section_name = group["section_name"]
            group_chunks = group["chunks"]
            group_citations = _group_citations(group_chunks)
            batch_summaries: list[dict[str, Any]] = []

            batches = _split_chunks_by_chars(group_chunks, settings.summary_section_max_chars)
            selected_batches = _select_batches_for_summary_type(
                batches=batches,
                summary_type=state.get("summary_type", "standard"),
                is_references=group["is_references"],
            )

            for batch_chunks in selected_batches:
                context = build_chunk_context(batch_chunks, max_chars=settings.summary_section_max_chars)
                user_prompt = _build_section_user_prompt(section_name, context, is_references=group["is_references"])
                response = llm.generate(
                    system_prompt=SECTION_SUMMARY_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    user_id=state.get("user_id"),
                )
                batch_summaries.append(
                    parse_section_summary_response(
                        response=response,
                        section_name=section_name,
                        citations=_group_citations(batch_chunks),
                    )
                )

            merged_summary = _merge_batch_summaries(section_name, batch_summaries, group_citations)
            section_summaries.append(merged_summary)

            group_elapsed_ms = int((perf_counter() - group_started_at) * 1000)
            logger.info(
                "section summary finished section=%s chunk_count=%s latency_ms=%s",
                section_name,
                len(group_chunks),
                group_elapsed_ms,
            )

        elapsed_ms = int((perf_counter() - started_at) * 1000)
        trace.append(
            {
                "tool_name": "section_summary",
                "input": {"chunk_count": len(chunks), "section_group_count": len(groups)},
                "output": {"section_summary_count": len(section_summaries)},
                "latency_ms": elapsed_ms,
                "status": "success",
                "error_message": None,
            }
        )

        updated = dict(state)
        updated.update(
            {
                "section_groups": groups,
                "section_summaries": section_summaries,
                "trace": trace,
            }
        )
        return updated
    except LLMServiceError as exc:
        raise AppError(str(exc), status.HTTP_502_BAD_GATEWAY) from exc
    except Exception as exc:
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        trace.append(
            {
                "tool_name": "section_summary",
                "input": {"chunk_count": len(chunks), "section_group_count": len(groups)},
                "output": None,
                "latency_ms": elapsed_ms,
                "status": "failed",
                "error_message": str(exc),
            }
        )
        state["trace"] = trace
        state["error_message"] = str(exc)
        raise


def _build_section_user_prompt(section_name: str, context: str, is_references: bool) -> str:
    references_note = "该部分是参考文献，保留来源信息即可，不要作为论文正文重点。" if is_references else ""
    return f"""章节名称：{section_name}
{references_note}

论文片段：
{context}

请基于上述片段总结该章节。只输出 JSON。"""


def _split_chunks_by_chars(chunks: list[dict[str, Any]], max_chars: int) -> list[list[dict[str, Any]]]:
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0

    for chunk in chunks:
        content_len = len(str(chunk.get("content") or ""))
        if current and current_chars + content_len > max_chars:
            batches.append(current)
            current = []
            current_chars = 0
        current.append(chunk)
        current_chars += content_len

    if current:
        batches.append(current)
    return batches


def _select_batches_for_summary_type(
    batches: list[list[dict[str, Any]]],
    summary_type: str,
    is_references: bool,
) -> list[list[dict[str, Any]]]:
    if not batches:
        return []
    if is_references:
        return batches[:1]

    max_batches = {
        "quick": 3,
        "standard": 8,
        "detailed": 16,
    }.get(summary_type, 8)
    if len(batches) <= max_batches:
        return batches
    if max_batches <= 3:
        middle = len(batches) // 2
        return [batches[0], batches[middle], batches[-1]]

    head_count = max_batches // 2
    tail_count = max_batches - head_count - 1
    middle = len(batches) // 2
    selected = batches[:head_count] + [batches[middle]] + batches[-tail_count:]
    deduped: list[list[dict[str, Any]]] = []
    seen: set[int] = set()
    for batch in selected:
        marker = id(batch)
        if marker not in seen:
            seen.add(marker)
            deduped.append(batch)
    return deduped[:max_batches]


def _group_citations(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "index": chunk.get("citation_index"),
            "chunk_index": chunk.get("chunk_index"),
            "page_number": chunk.get("page_number"),
            "section_title": chunk.get("section_title") or "",
        }
        for chunk in chunks
    ]


def _merge_batch_summaries(
    section_name: str,
    batch_summaries: list[dict[str, Any]],
    citations: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(batch_summaries) == 1:
        one = batch_summaries[0]
        one["citations"] = citations
        return one

    summaries = [item.get("summary", "") for item in batch_summaries if item.get("summary")]
    key_points: list[str] = []
    for item in batch_summaries:
        key_points.extend(item.get("key_points") or [])

    return {
        "section_name": section_name,
        "summary": "\n".join(summaries) if summaries else "该部分未提供明确依据",
        "key_points": key_points,
        "citations": citations,
    }

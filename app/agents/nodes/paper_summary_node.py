from __future__ import annotations

import json
import logging
from time import perf_counter

from fastapi import status

from app.agents.prompts.paper_summary_prompt import FINAL_SUMMARY_SYSTEM_PROMPT
from app.agents.state import PaperSummaryState
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.paper.summary_builder import parse_final_summary_response
from app.services.llm_service import LLMService, LLMServiceError


logger = logging.getLogger(__name__)


def paper_summary_node(state: PaperSummaryState) -> PaperSummaryState:
    settings = get_settings()
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    section_summaries = state.get("section_summaries", [])

    try:
        if not section_summaries:
            raise AppError("No section summaries generated", status.HTTP_409_CONFLICT)

        prompt = _build_final_summary_user_prompt(state, settings.summary_final_max_chars)
        response = LLMService().generate(
            system_prompt=FINAL_SUMMARY_SYSTEM_PROMPT,
            user_prompt=prompt,
            user_id=state.get("user_id"),
        )
        markdown, summary_json = parse_final_summary_response(response, citations=state.get("citations", []))

        elapsed_ms = int((perf_counter() - started_at) * 1000)
        trace.append(
            {
                "tool_name": "final_paper_summary",
                "input": {
                    "summary_type": state.get("summary_type"),
                    "section_summary_count": len(section_summaries),
                },
                "output": {
                    "markdown_chars": len(markdown),
                    "json_keys": list(summary_json.keys()),
                },
                "latency_ms": elapsed_ms,
                "status": "success",
                "error_message": None,
            }
        )
        logger.info(
            "final summary finished document_id=%s summary_type=%s latency_ms=%s",
            state.get("document_id"),
            state.get("summary_type"),
            elapsed_ms,
        )

        updated = dict(state)
        updated.update(
            {
                "final_summary_markdown": markdown,
                "final_summary_json": summary_json,
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
                "tool_name": "final_paper_summary",
                "input": {"summary_type": state.get("summary_type")},
                "output": None,
                "latency_ms": elapsed_ms,
                "status": "failed",
                "error_message": str(exc),
            }
        )
        state["trace"] = trace
        state["error_message"] = str(exc)
        raise


def _build_final_summary_user_prompt(state: PaperSummaryState, max_chars: int) -> str:
    summary_type = state.get("summary_type", "standard")
    mode_instruction = {
        "quick": "请输出较短版本，突出核心问题、核心方法、主要结论和局限性。",
        "standard": "请输出中等长度版本，适合作为文献阅读笔记。",
        "detailed": "请输出详细版本，适合写综述或开题报告前使用。",
    }.get(summary_type, "请输出中等长度版本，适合作为文献阅读笔记。")

    payload = {
        "document_info": state.get("document_info", {}),
        "summary_type": summary_type,
        "project_topic": state.get("project_topic"),
        "section_summaries": state.get("section_summaries", []),
    }
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    return f"""{mode_instruction}

用户当前论文题目或方向：
{state.get("project_topic") or "未提供"}

章节总结材料：
{serialized[:max_chars]}
"""

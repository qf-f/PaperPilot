from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from copy import deepcopy
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.token_usage import get_token_usage, reset_token_usage, start_token_usage
from app.db.models.agent_run import AgentRun
from app.db.models.tool_trace import ToolTrace


logger = logging.getLogger(__name__)

MAX_TRACE_CHARS = 4000


def trace_node(node_name: str, node_fn: Callable[[dict], dict], max_retries: int = 2) -> Callable[[dict], dict]:
    def wrapped(state: dict) -> dict:
        attempt = 0
        last_error: Exception | None = None
        while attempt <= max_retries:
            started_at = time.perf_counter()
            try:
                result = node_fn(state)
                trace = list(result.get("trace", []))
                trace.append(
                    {
                        "node_name": node_name,
                        "tool_name": node_name,
                        "input": _clip_payload(state),
                        "output": _clip_payload(result),
                        "status": "success",
                        "latency_ms": int((time.perf_counter() - started_at) * 1000),
                        "error_message": None,
                        "attempt": attempt + 1,
                    }
                )
                updated = dict(result)
                updated["trace"] = trace
                return updated
            except Exception as exc:
                last_error = exc
                if attempt >= max_retries:
                    trace = list(state.get("trace", []))
                    trace.append(
                        {
                            "node_name": node_name,
                            "tool_name": node_name,
                            "input": _clip_payload(state),
                            "output": None,
                            "status": "error",
                            "latency_ms": int((time.perf_counter() - started_at) * 1000),
                            "error_message": str(exc),
                            "attempt": attempt + 1,
                        }
                    )
                    state["trace"] = trace
                    raise
                time.sleep(min(2**attempt, 4))
                attempt += 1
        raise last_error or RuntimeError(f"{node_name} failed")

    return wrapped


class AgentRunner:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def create_run(
        self,
        project_id: str,
        intent: str,
        user_query: str,
        session_id: str | None = None,
        status_value: str = "queued",
    ) -> AgentRun:
        run = AgentRun(
            project_id=UUID(str(project_id)),
            session_id=UUID(str(session_id)) if session_id else None,
            user_query=user_query[:4000],
            intent=intent,
            status=status_value,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def run_sync(
        self,
        graph: Any,
        input_state: dict[str, Any],
        project_id: str,
        intent: str,
        user_query: str,
        session_id: str | None = None,
        run_id: str | None = None,
    ) -> tuple[dict[str, Any], AgentRun]:
        run = self._get_or_create_run(project_id, intent, user_query, session_id, run_id)
        run.status = "running"
        self.db.commit()

        started_at = time.perf_counter()
        usage_token = start_token_usage()
        try:
            input_state = dict(input_state)
            input_state.setdefault("trace", [])
            input_state["agent_run_id"] = str(run.id)
            final_state = graph.invoke(input_state)
            usage = get_token_usage()
            run.prompt_tokens = usage.prompt_tokens
            run.completion_tokens = usage.completion_tokens
            run.total_tokens = usage.total_tokens
            run.estimated_cost = usage.estimated_cost
            run.status = self._status_from_state(final_state)
            run.error_message = None
            self._save_traces(run.id, final_state.get("trace", []))
            self.db.commit()
            logger.info(
                "agent_run_finished run_id=%s intent=%s status=%s latency_ms=%s total_tokens=%s",
                run.id,
                intent,
                run.status,
                int((time.perf_counter() - started_at) * 1000),
                run.total_tokens,
            )
            return final_state, run
        except Exception as exc:
            self.db.rollback()
            run = self.db.get(AgentRun, run.id) or run
            run.status = "failed"
            run.error_message = str(exc)
            self.db.commit()
            logger.exception("agent_run_failed run_id=%s intent=%s error=%s", run.id, intent, exc)
            if isinstance(exc, AppError):
                raise
            raise AppError(f"Agent run failed: {exc}", status.HTTP_500_INTERNAL_SERVER_ERROR) from exc
        finally:
            reset_token_usage(usage_token)

    async def run_async(self, *args: Any, **kwargs: Any) -> tuple[dict[str, Any], AgentRun]:
        return await asyncio.to_thread(self.run_sync, *args, **kwargs)

    def _get_or_create_run(
        self,
        project_id: str,
        intent: str,
        user_query: str,
        session_id: str | None,
        run_id: str | None,
    ) -> AgentRun:
        if run_id:
            run = self.db.get(AgentRun, UUID(str(run_id)))
            if run is None:
                raise AppError("Agent run not found", status.HTTP_404_NOT_FOUND)
            return run
        return self.create_run(project_id, intent, user_query, session_id=session_id, status_value="running")

    def _save_traces(self, run_id: UUID, traces: list[dict[str, Any]]) -> None:
        for trace in traces:
            self.db.add(
                ToolTrace(
                    agent_run_id=run_id,
                    node_name=trace.get("node_name") or trace.get("tool_name"),
                    tool_name=trace.get("tool_name") or trace.get("node_name") or "unknown",
                    input=trace.get("input") if self.settings.agent_trace_debug else _clip_payload(trace.get("input")),
                    output=trace.get("output") if self.settings.agent_trace_debug else _clip_payload(trace.get("output")),
                    latency_ms=trace.get("latency_ms"),
                    status=trace.get("status", "unknown"),
                    error_message=trace.get("error_message"),
                )
            )

    @staticmethod
    def _status_from_state(state: dict[str, Any]) -> str:
        if state.get("partial_success"):
            return "partial_success"
        traces = state.get("trace", [])
        if any(trace.get("status") == "error" for trace in traces):
            return "partial_success"
        warning_values = state.get("warnings") or state.get("consistency_warnings") or []
        if any("失败" in str(item) or "failed" in str(item).lower() for item in warning_values):
            return "partial_success"
        return "success"


def _clip_payload(payload: Any) -> Any:
    if payload is None:
        return None
    safe = _safe_payload(payload)
    text = str(safe)
    if len(text) <= MAX_TRACE_CHARS:
        return safe
    return {"preview": text[:MAX_TRACE_CHARS], "truncated": True}


def _safe_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        result = {}
        for key, value in payload.items():
            if key in {"target_content", "source_text", "translated_markdown", "content_markdown"}:
                result[key] = str(value)[:800]
            elif key in {"segments", "translated_segments", "retrieved_chunks"} and isinstance(value, list):
                result[key] = {"count": len(value), "preview": deepcopy(value[:2])}
            else:
                result[key] = _safe_payload(value)
        return result
    if isinstance(payload, list):
        return [_safe_payload(item) for item in payload[:10]]
    if isinstance(payload, (str, int, float, bool)) or payload is None:
        return payload if not isinstance(payload, str) or len(payload) <= 1200 else payload[:1200]
    return str(payload)

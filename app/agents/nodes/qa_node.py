from __future__ import annotations

from time import perf_counter

from fastapi import status

from app.agents.prompts.knowledge_qa_prompt import KNOWLEDGE_QA_SYSTEM_PROMPT
from app.agents.state import PaperAgentState
from app.core.exceptions import AppError
from app.services.llm_service import LLMService, LLMServiceError


NO_EVIDENCE_ANSWER = "当前上传文档中没有找到直接依据。你可以尝试指定文档、降低相似度阈值，或先上传相关论文。"


def qa_node(state: PaperAgentState) -> PaperAgentState:
    retrieved_chunks = state.get("retrieved_chunks", [])
    trace = list(state.get("trace", []))

    if not retrieved_chunks:
        trace.append(
            {
                "tool_name": "llm",
                "input": {"retrieved_count": 0},
                "output": {"skipped": True, "reason": "no_retrieved_chunks"},
                "latency_ms": 0,
                "status": "skipped",
                "error_message": None,
            }
        )
        updated = dict(state)
        updated.update(
            {
                "answer": NO_EVIDENCE_ANSWER,
                "uncertainty_flag": True,
                "trace": trace,
            }
        )
        return updated

    started_at = perf_counter()
    try:
        answer = LLMService().generate(
            system_prompt=KNOWLEDGE_QA_SYSTEM_PROMPT,
            user_prompt=state.get("context_prompt", ""),
        )
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        trace.append(
            {
                "tool_name": "llm",
                "input": {
                    "model": "configured_chat_model",
                    "retrieved_count": len(retrieved_chunks),
                },
                "output": {"answer_chars": len(answer)},
                "latency_ms": elapsed_ms,
                "status": "success",
                "error_message": None,
            }
        )

        updated = dict(state)
        updated.update(
            {
                "answer": answer,
                "uncertainty_flag": False,
                "trace": trace,
            }
        )
        return updated
    except LLMServiceError as exc:
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        trace.append(
            {
                "tool_name": "llm",
                "input": {"retrieved_count": len(retrieved_chunks)},
                "output": None,
                "latency_ms": elapsed_ms,
                "status": "failed",
                "error_message": str(exc),
            }
        )
        state["trace"] = trace
        state["error_message"] = str(exc)
        raise AppError(str(exc), status.HTTP_502_BAD_GATEWAY) from exc

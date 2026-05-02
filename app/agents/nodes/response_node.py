from __future__ import annotations

from app.agents.state import PaperAgentState


def response_node(state: PaperAgentState) -> PaperAgentState:
    updated = dict(state)
    error_message = updated.get("error_message")
    if error_message and not updated.get("answer"):
        updated["answer"] = f"知识库问答失败：{error_message}"

    updated.setdefault("answer", "")
    updated.setdefault("citations", [])
    updated.setdefault("retrieved_chunks", [])
    updated.setdefault("trace", [])
    updated.setdefault("uncertainty_flag", not bool(updated.get("retrieved_chunks")))
    return updated

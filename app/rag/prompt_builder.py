from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.rag.retriever import RetrievedChunk


def _get_value(chunk: RetrievedChunk | dict[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(chunk, RetrievedChunk):
        return getattr(chunk, key, default)
    return chunk.get(key, default)


def build_rag_user_prompt(
    query: str,
    retrieved_chunks: list[RetrievedChunk | dict[str, Any]],
    max_context_chars: int | None = None,
) -> str:
    settings = get_settings()
    context_budget = max_context_chars or settings.rag_max_context_chars
    sorted_chunks = sorted(
        retrieved_chunks,
        key=lambda item: float(_get_value(item, "score", 0.0)),
        reverse=True,
    )

    context_parts: list[str] = []
    used_chars = 0

    for index, chunk in enumerate(sorted_chunks, start=1):
        file_name = _get_value(chunk, "file_name", "")
        page_number = _get_value(chunk, "page_number")
        section_title = _get_value(chunk, "section_title", "") or ""
        chunk_index = _get_value(chunk, "chunk_index", 0)
        content = str(_get_value(chunk, "content", "")).strip()
        if not content:
            continue

        header = (
            f"[{index}] 来源：file_name={file_name}, "
            f"page={page_number}, section={section_title}, chunk={chunk_index}\n"
            "内容：\n"
        )
        remaining = context_budget - used_chars - len(header)
        if remaining <= 0:
            break
        clipped_content = content[:remaining]
        part = f"{header}{clipped_content}"
        context_parts.append(part)
        used_chars += len(part)

        if used_chars >= context_budget:
            break

    context = "\n\n".join(context_parts).strip()
    if not context:
        context = "无可用检索上下文。"

    return f"""检索上下文：
{context}

用户问题：
{query}
"""

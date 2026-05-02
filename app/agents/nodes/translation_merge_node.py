from __future__ import annotations

from time import perf_counter

from app.agents.state import TranslationState
from app.translation.bilingual_builder import build_translation_markdown


def translation_merge_node(state: TranslationState) -> TranslationState:
    started_at = perf_counter()
    document_name = state.get("document_info", {}).get("original_filename", state.get("document_id", "document"))
    markdown, content_json = build_translation_markdown(
        document_name=document_name,
        translated_segments=state.get("translated_segments", []),
        output_style=state.get("output_style", "bilingual"),
        warnings=state.get("consistency_warnings", []),
    )
    content_json.update(
        {
            "translation_mode": state.get("translation_mode", "faithful"),
            "range_type": state.get("range_type", "full"),
            "page_from": state.get("page_from"),
            "page_to": state.get("page_to"),
            "chunk_from": state.get("chunk_from"),
            "chunk_to": state.get("chunk_to"),
            "document_info": state.get("document_info", {}),
            "terminologies": state.get("existing_terms", []) + state.get("extracted_terms", []),
            "term_map": state.get("term_map", {}),
        }
    )
    trace = list(state.get("trace", []))
    trace.append(
        {
            "tool_name": "translation_merge",
            "output": {"markdown_chars": len(markdown)},
            "latency_ms": int((perf_counter() - started_at) * 1000),
            "status": "success",
        }
    )
    updated = dict(state)
    updated.update({"translated_markdown": markdown, "content_json": content_json, "trace": trace})
    return updated

from __future__ import annotations

import json
from time import perf_counter

from fastapi import status

from app.agents.prompts.translation_prompt import SEGMENT_TRANSLATION_SYSTEM_PROMPT
from app.agents.state import TranslationState
from app.core.exceptions import AppError
from app.services.llm_service import LLMService


def translation_segment_node(state: TranslationState) -> TranslationState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    warnings = list(state.get("consistency_warnings", []))

    try:
        llm = LLMService()
    except Exception as exc:
        raise AppError(f"Translation LLM is not configured or unavailable: {exc}", status.HTTP_502_BAD_GATEWAY) from exc

    translated_segments: list[dict] = []
    success_count = 0
    for segment in state.get("segments", []):
        prompt = _build_segment_prompt(state, segment)
        translated = ""
        warning = ""
        try:
            translated = llm.generate(
                system_prompt=SEGMENT_TRANSLATION_SYSTEM_PROMPT,
                user_prompt=prompt,
                user_id=state.get("user_id"),
            ).strip()
            success_count += 1
        except Exception as exc:
            warning = f"段落 {segment.get('segment_index')} 翻译失败：{exc}"
            warnings.append(warning)
        translated_item = dict(segment)
        translated_item.update({"translated_text": translated, "warning": warning})
        translated_segments.append(translated_item)

    if translated_segments and success_count == 0:
        raise AppError("All translation segments failed. Please check LLM configuration and retry.", status.HTTP_502_BAD_GATEWAY)

    trace.append(
        {
            "tool_name": "translation_segment",
            "output": {"segment_count": len(translated_segments), "success_count": success_count},
            "latency_ms": int((perf_counter() - started_at) * 1000),
            "status": "success",
        }
    )
    updated = dict(state)
    updated.update({"translated_segments": translated_segments, "consistency_warnings": warnings, "trace": trace})
    return updated


def _build_segment_prompt(state: TranslationState, segment: dict) -> str:
    term_items = [
        {"source_term": source_term, "target_term": target_term}
        for source_term, target_term in state.get("term_map", {}).items()
    ][:80]
    return json.dumps(
        {
            "translation_mode": state.get("translation_mode", "faithful"),
            "output_style": state.get("output_style", "bilingual"),
            "requirements": state.get("requirements"),
            "section_title": segment.get("section_title"),
            "page_number": segment.get("page_number"),
            "chunk_indexes": segment.get("chunk_indexes", []),
            "terminology_table": term_items,
            "source_text": segment.get("source_text", ""),
        },
        ensure_ascii=False,
    )

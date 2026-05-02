from __future__ import annotations

import re
from typing import Any


def detect_inconsistent_terms(translated_segments: list[dict[str, Any]], term_map: dict[str, str]) -> list[str]:
    warnings: list[str] = []
    for source_term, target_term in term_map.items():
        if not source_term or not target_term:
            continue
        affected = [
            segment
            for segment in translated_segments
            if re.search(re.escape(source_term), segment.get("source_text", ""), flags=re.IGNORECASE)
        ]
        if not affected:
            continue
        missing = [
            str(segment.get("segment_index"))
            for segment in affected
            if target_term not in (segment.get("translated_text") or "")
        ]
        if missing:
            warnings.append(
                f"术语 {source_term} 已登记为“{target_term}”，但段落 {', '.join(missing)} 的译文可能未使用该译名。"
            )
        if _english_term_left_untranslated(source_term, affected):
            warnings.append(f"术语 {source_term} 在部分译文中可能未翻译，请人工确认。")
    return _dedupe(warnings)


def _english_term_left_untranslated(source_term: str, segments: list[dict[str, Any]]) -> bool:
    if not re.search(r"[A-Za-z]", source_term):
        return False
    return any(re.search(re.escape(source_term), segment.get("translated_text", ""), flags=re.IGNORECASE) for segment in segments)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

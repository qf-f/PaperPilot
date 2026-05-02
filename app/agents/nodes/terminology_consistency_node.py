from __future__ import annotations

from time import perf_counter

from app.agents.state import TranslationState
from app.translation.translation_checker import detect_inconsistent_terms


def terminology_consistency_node(state: TranslationState) -> TranslationState:
    started_at = perf_counter()
    warnings = list(state.get("consistency_warnings", []))
    warnings.extend(detect_inconsistent_terms(state.get("translated_segments", []), state.get("term_map", {})))
    trace = list(state.get("trace", []))
    trace.append(
        {
            "tool_name": "terminology_consistency",
            "output": {"warning_count": len(warnings)},
            "latency_ms": int((perf_counter() - started_at) * 1000),
            "status": "success",
        }
    )
    updated = dict(state)
    updated.update({"consistency_warnings": warnings, "trace": trace})
    return updated

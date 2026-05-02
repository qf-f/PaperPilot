from __future__ import annotations

from app.agents.state import TranslationState


def translation_response_node(state: TranslationState) -> TranslationState:
    updated = dict(state)
    updated.setdefault("translated_markdown", "")
    updated.setdefault("content_json", {})
    updated.setdefault("extracted_terms", [])
    updated.setdefault("consistency_warnings", [])
    return updated

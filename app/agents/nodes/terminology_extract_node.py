from __future__ import annotations

from time import perf_counter

from app.agents.state import TranslationState
from app.db.session import SessionLocal
from app.services.llm_service import LLMService
from app.services.terminology_service import TerminologyService
from app.translation.terminology_extractor import extract_terms_from_segments
from app.translation.terminology_store import build_term_map


def terminology_extract_node(state: TranslationState) -> TranslationState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    warnings = list(state.get("consistency_warnings", []))

    with SessionLocal() as db:
        service = TerminologyService(db)
        existing_rows = service.list_terms(state["project_id"])
        existing_terms = [service.to_dict(row) for row in existing_rows]

        try:
            llm_service = LLMService()
        except Exception as exc:
            llm_service = None
            warnings.append(f"术语 LLM 增强不可用，已使用规则抽取术语：{exc}")

        extracted_terms = extract_terms_from_segments(
            segments=state.get("segments", []),
            existing_terms=existing_terms,
            llm_service=llm_service,
        )
        saved_terms = service.upsert_terms(
            project_id=state["project_id"],
            document_id=state["document_id"],
            terms=extracted_terms,
            overwrite_target=False,
        )
        saved_dicts = [service.to_dict(row) for row in saved_terms]
        all_terms = existing_terms + saved_dicts
        term_map = build_term_map(all_terms)

    trace.append(
        {
            "tool_name": "terminology_extract",
            "output": {"existing_count": len(existing_terms), "extracted_count": len(extracted_terms)},
            "latency_ms": int((perf_counter() - started_at) * 1000),
            "status": "success",
        }
    )
    updated = dict(state)
    updated.update(
        {
            "existing_terms": existing_terms,
            "extracted_terms": saved_dicts,
            "term_map": term_map,
            "consistency_warnings": warnings,
            "trace": trace,
        }
    )
    return updated

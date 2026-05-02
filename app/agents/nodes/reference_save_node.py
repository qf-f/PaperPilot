from __future__ import annotations

from time import perf_counter
from uuid import UUID

from sqlalchemy import select

from app.agents.state import ReferenceState
from app.db.models.reference import PaperReference
from app.db.session import SessionLocal
from app.references.formatter import format_all_styles


def reference_save_node(state: ReferenceState) -> ReferenceState:
    started_at = perf_counter()
    project_id = UUID(str(state["project_id"]))
    document_id = UUID(str(state["document_id"])) if state.get("document_id") else None
    saved = []

    with SessionLocal() as db:
        for item in state.get("deduped_references", []):
            if not item.get("title"):
                continue
            existing = _find_existing(db, project_id, document_id, item)
            formatted = format_all_styles(item)
            if existing is None:
                existing = PaperReference(
                    project_id=project_id,
                    document_id=document_id,
                    source_type="uploaded_document" if document_id else "manual",
                    raw_text=item.get("raw_text", ""),
                )
                db.add(existing)
            existing.title = item.get("title")
            existing.authors = item.get("authors", [])
            existing.year = item.get("year")
            existing.venue = item.get("venue", "")
            existing.doi = item.get("doi", "")
            existing.url = item.get("url", "")
            existing.confidence_score = item.get("confidence_score")
            existing.gb_t_7714 = formatted["gb_t_7714"]
            existing.ieee = formatted["ieee"]
            existing.apa = formatted["apa"]
            existing.bibtex = formatted["bibtex"]
            db.flush()
            saved.append(_to_dict(existing))
        db.commit()

    trace = list(state.get("trace", []))
    trace.append(
        {
            "tool_name": "reference_save",
            "input": {"deduped_count": len(state.get("deduped_references", []))},
            "output": {"saved_count": len(saved)},
            "latency_ms": int((perf_counter() - started_at) * 1000),
            "status": "success",
            "error_message": None,
        }
    )
    updated = dict(state)
    updated.update({"saved_references": saved, "trace": trace})
    return updated


def _find_existing(db, project_id: UUID, document_id: UUID | None, item: dict) -> PaperReference | None:
    if item.get("doi"):
        found = db.execute(
            select(PaperReference).where(PaperReference.project_id == project_id, PaperReference.doi == item["doi"])
        ).scalars().first()
        if found:
            return found
    return db.execute(
        select(PaperReference).where(
            PaperReference.project_id == project_id,
            PaperReference.document_id == document_id,
            PaperReference.title == item.get("title"),
        )
    ).scalars().first()


def _to_dict(row: PaperReference) -> dict:
    return {
        "id": str(row.id),
        "title": row.title or "",
        "authors": row.authors or [],
        "year": row.year,
        "venue": row.venue or "",
        "doi": row.doi or "",
        "url": row.url or "",
        "source_type": row.source_type,
        "confidence_score": row.confidence_score,
    }

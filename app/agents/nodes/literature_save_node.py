from __future__ import annotations

from datetime import date
from time import perf_counter
from uuid import UUID

from sqlalchemy import select

from app.agents.state import LiteratureSearchState
from app.db.models.literature import Literature
from app.db.session import SessionLocal


def literature_save_node(state: LiteratureSearchState) -> LiteratureSearchState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    project_id = UUID(str(state["project_id"]))
    saved = []

    with SessionLocal() as db:
        for item in state.get("ranked_results", []):
            if not item.get("title"):
                continue
            existing = _find_existing(db, project_id, item)
            if existing is None:
                existing = Literature(project_id=project_id, title=item["title"], source_provider=item.get("source_provider", "unknown"))
                db.add(existing)
            _apply_literature(existing, item)
            db.flush()
            saved.append(_to_dict(existing))
        db.commit()

    elapsed_ms = int((perf_counter() - started_at) * 1000)
    trace.append(
        {
            "tool_name": "literature_save",
            "input": {"ranked_count": len(state.get("ranked_results", []))},
            "output": {"saved_count": len(saved)},
            "latency_ms": elapsed_ms,
            "status": "success",
            "error_message": None,
        }
    )
    updated = dict(state)
    updated.update({"saved_literatures": saved, "trace": trace})
    return updated


def _find_existing(db, project_id: UUID, item: dict) -> Literature | None:
    if item.get("doi"):
        found = db.execute(
            select(Literature).where(Literature.project_id == project_id, Literature.doi == item["doi"])
        ).scalars().first()
        if found:
            return found
    return db.execute(
        select(Literature).where(
            Literature.project_id == project_id,
            Literature.title == item["title"],
        )
    ).scalars().first()

def _apply_literature(row: Literature, item: dict) -> None:
    for key in [
        "source_provider",
        "external_id",
        "title",
        "abstract",
        "authors",
        "year",
        "venue",
        "doi",
        "url",
        "pdf_url",
        "categories",
        "keywords",
        "citation_count",
        "influential_citation_count",
        "relevance_score",
        "recommendation_reason",
        "raw_data",
    ]:
        setattr(row, key, item.get(key))
    published = item.get("published_date")
    row.published_date = published if isinstance(published, date) else None


def _to_dict(row: Literature) -> dict:
    return {
        "id": str(row.id),
        "title": row.title,
        "authors": row.authors or [],
        "year": row.year,
        "venue": row.venue or "",
        "doi": row.doi or "",
        "url": row.url or "",
        "pdf_url": row.pdf_url or "",
        "source_provider": row.source_provider,
        "relevance_score": row.relevance_score,
        "recommendation_reason": row.recommendation_reason or "",
    }

from __future__ import annotations

from time import perf_counter
from uuid import UUID

from sqlalchemy import select

from app.agents.state import ReferenceState
from app.db.models.literature import Literature
from app.db.models.project import PaperProject
from app.db.models.reference import PaperReference
from app.db.session import SessionLocal
from app.references.recommender import recommend_references


def reference_recommend_node(state: ReferenceState) -> ReferenceState:
    started_at = perf_counter()
    project_id = UUID(str(state["project_id"]))
    with SessionLocal() as db:
        project = db.get(PaperProject, project_id)
        topic = " ".join([project.title if project else "", project.research_direction if project else ""]).strip()
        literatures = list(
            db.execute(
                select(Literature)
                .where(Literature.project_id == project_id)
                .order_by(Literature.relevance_score.desc().nullslast())
                .limit(50)
            ).scalars().all()
        )
        existing_refs = list(db.execute(select(PaperReference).where(PaperReference.project_id == project_id)).scalars().all())

    recommendations = recommend_references(topic=topic, literatures=literatures, existing_references=existing_refs)
    trace = list(state.get("trace", []))
    trace.append(
        {
            "tool_name": "reference_recommend",
            "input": {"literature_count": len(literatures), "reference_count": len(existing_refs)},
            "output": {"recommendation_count": len(recommendations)},
            "latency_ms": int((perf_counter() - started_at) * 1000),
            "status": "success",
            "error_message": None,
        }
    )
    updated = dict(state)
    updated.update({"recommended_references": recommendations, "trace": trace})
    return updated

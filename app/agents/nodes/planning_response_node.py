from __future__ import annotations

from app.agents.state import PlanningState


def planning_response_node(state: PlanningState) -> PlanningState:
    updated = dict(state)
    updated.setdefault("final_markdown", "")
    updated.setdefault("final_json", {})
    updated.setdefault("trace", [])
    return updated

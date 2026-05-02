from __future__ import annotations

import json
from time import perf_counter

from app.agents.prompts.planning_prompt import EXPERIMENT_DESIGN_SYSTEM_PROMPT
from app.agents.state import PlanningState
from app.planning.experiment_template import default_experiment_plan
from app.services.llm_service import LLMService


def experiment_design_node(state: PlanningState) -> PlanningState:
    started_at = perf_counter()
    fallback = default_experiment_plan(state["topic"])
    payload = json.dumps({"topic": state["topic"], "innovations": state.get("innovations"), "context": state.get("project_context")}, ensure_ascii=False)
    result = _safe_llm_json(EXPERIMENT_DESIGN_SYSTEM_PROMPT, payload, fallback)
    trace = list(state.get("trace", []))
    trace.append({"tool_name": "experiment_design", "latency_ms": int((perf_counter() - started_at) * 1000), "status": "success"})
    updated = dict(state)
    updated.update({"experiment_plan": result, "trace": trace})
    return updated


def _safe_llm_json(system_prompt: str, user_prompt: str, fallback: dict) -> dict:
    try:
        content = LLMService().generate(system_prompt=system_prompt, user_prompt=user_prompt)
        start = content.find("{")
        end = content.rfind("}")
        return json.loads(content[start : end + 1]) if start >= 0 and end > start else fallback
    except Exception:
        return fallback

from __future__ import annotations

import json
from time import perf_counter

from app.agents.prompts.planning_prompt import TOPIC_ANALYSIS_SYSTEM_PROMPT
from app.agents.state import PlanningState
from app.planning.feasibility_checker import check_topic_feasibility
from app.services.llm_service import LLMService


def topic_analysis_node(state: PlanningState) -> PlanningState:
    started_at = perf_counter()
    fallback = check_topic_feasibility(state["topic"], state.get("research_direction"))
    prompt = json.dumps(
        {
            "topic": state["topic"],
            "paper_type": state["paper_type"],
            "research_direction": state.get("research_direction"),
            "requirements": state.get("requirements"),
            "project_context": state.get("project_context", {}),
            "rule_check": fallback,
        },
        ensure_ascii=False,
    )
    analysis = _safe_llm_json(TOPIC_ANALYSIS_SYSTEM_PROMPT, prompt, fallback)
    trace = list(state.get("trace", []))
    trace.append({"tool_name": "topic_analysis", "latency_ms": int((perf_counter() - started_at) * 1000), "status": "success"})
    updated = dict(state)
    updated.update({"topic_analysis": analysis, "trace": trace})
    return updated


def _safe_llm_json(system_prompt: str, user_prompt: str, fallback: dict) -> dict:
    try:
        content = LLMService().generate(system_prompt=system_prompt, user_prompt=user_prompt)
        start = content.find("{")
        end = content.rfind("}")
        return json.loads(content[start : end + 1]) if start >= 0 and end > start else fallback
    except Exception:
        return fallback

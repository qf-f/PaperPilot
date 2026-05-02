from __future__ import annotations

import json
from time import perf_counter

from app.agents.prompts.planning_prompt import RESEARCH_PROBLEM_SYSTEM_PROMPT
from app.agents.state import PlanningState
from app.services.llm_service import LLMService


def research_problem_node(state: PlanningState) -> PlanningState:
    started_at = perf_counter()
    fallback = {
        "research_questions": [
            {"id": "RQ1", "question": "如何构建面向论文项目的可信 RAG 知识库与引用溯源机制？"},
            {"id": "RQ2", "question": "如何设计覆盖论文阅读、总结、规划和写作的 Agent 工作流？"},
            {"id": "RQ3", "question": "如何评价系统生成内容的可信性、完整性和可用性？"},
        ],
        "research_objectives": ["实现项目级知识隔离", "实现可追溯问答与总结", "形成可评估的论文写作辅助流程"],
        "research_contents": [
            {"name": "项目级 RAG 知识库构建", "description": "围绕文档解析、chunk、embedding、metadata filter 展开"},
            {"name": "LangGraph Agent 工作流设计", "description": "围绕问答、总结、文献管理、规划写作展开"},
            {"name": "实验与评价体系设计", "description": "围绕引用准确率、拒答率、可用性和性能展开"},
        ],
    }
    payload = json.dumps({"topic": state["topic"], "analysis": state.get("topic_analysis"), "context": state.get("project_context")}, ensure_ascii=False)
    result = _safe_llm_json(RESEARCH_PROBLEM_SYSTEM_PROMPT, payload, fallback)
    trace = list(state.get("trace", []))
    trace.append({"tool_name": "research_problem", "latency_ms": int((perf_counter() - started_at) * 1000), "status": "success"})
    updated = dict(state)
    updated.update(
        {
            "research_questions": result.get("research_questions", fallback["research_questions"]),
            "research_objectives": result.get("research_objectives", fallback["research_objectives"]),
            "research_contents": result.get("research_contents", fallback["research_contents"]),
            "trace": trace,
        }
    )
    return updated


def _safe_llm_json(system_prompt: str, user_prompt: str, fallback: dict) -> dict:
    try:
        content = LLMService().generate(system_prompt=system_prompt, user_prompt=user_prompt)
        start = content.find("{")
        end = content.rfind("}")
        return json.loads(content[start : end + 1]) if start >= 0 and end > start else fallback
    except Exception:
        return fallback

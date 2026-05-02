from __future__ import annotations

import json
from time import perf_counter

from app.agents.prompts.planning_prompt import INNOVATION_DESIGN_SYSTEM_PROMPT
from app.agents.state import PlanningState
from app.services.llm_service import LLMService


def innovation_design_node(state: PlanningState) -> PlanningState:
    started_at = perf_counter()
    fallback = {
        "innovations": [
            {
                "name": "面向论文项目的引用可追溯 RAG 流程",
                "support": "已有知识库问答、citation、metadata filter 模块",
                "validation": "通过引用准确率、无依据拒答率和人工评审验证",
            },
            {
                "name": "面向论文写作流程的 LangGraph Agent 编排",
                "support": "已有问答、总结、文献管理、规划和写作节点",
                "validation": "通过任务完成度、结构完整性和用户可用性评分验证",
            },
        ]
    }
    payload = json.dumps({"topic": state["topic"], "questions": state.get("research_questions"), "context": state.get("project_context")}, ensure_ascii=False)
    result = _safe_llm_json(INNOVATION_DESIGN_SYSTEM_PROMPT, payload, fallback)
    trace = list(state.get("trace", []))
    trace.append({"tool_name": "innovation_design", "latency_ms": int((perf_counter() - started_at) * 1000), "status": "success"})
    updated = dict(state)
    updated.update({"innovations": result.get("innovations", fallback["innovations"]), "technical_route": result.get("technical_route", _default_route()), "trace": trace})
    return updated


def _default_route() -> dict:
    return {
        "steps": ["文档输入", "文档解析与切分", "向量索引", "检索增强问答", "Agent 编排", "生成内容保存与导出", "人工评价反馈"]
    }


def _safe_llm_json(system_prompt: str, user_prompt: str, fallback: dict) -> dict:
    try:
        content = LLMService().generate(system_prompt=system_prompt, user_prompt=user_prompt)
        start = content.find("{")
        end = content.rfind("}")
        return json.loads(content[start : end + 1]) if start >= 0 and end > start else fallback
    except Exception:
        return fallback

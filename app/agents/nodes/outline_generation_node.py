from __future__ import annotations

import json
from time import perf_counter

from app.agents.prompts.planning_prompt import FINAL_PLAN_SYSTEM_PROMPT, OUTLINE_GENERATION_SYSTEM_PROMPT
from app.agents.state import PlanningState
from app.planning.outline_builder import default_outline_for_paper_type
from app.services.llm_service import LLMService


def outline_generation_node(state: PlanningState) -> PlanningState:
    started_at = perf_counter()
    fallback_outline = default_outline_for_paper_type(state.get("paper_type", "thesis"))
    fallback = {
        "outline": fallback_outline,
        "risks": [
            {"risk": "文献不足", "mitigation": "继续使用联网检索和参考文献扩展补充关键文献"},
            {"risk": "创新点不足", "mitigation": "将贡献聚焦到可信引用、Agent 编排和可评价流程"},
            {"risk": "实验不充分", "mitigation": "建立问答、总结、写作任务测试集和人工评价表"},
        ],
        "next_tasks": [
            {"time": "本周", "task": "确定题目边界和实验评价指标"},
            {"time": "下周", "task": "补充相关工作和 baseline"},
            {"time": "之后两周", "task": "完成系统实验与章节草稿"},
        ],
    }
    payload = json.dumps({"state": {k: v for k, v in state.items() if k != "trace"}}, ensure_ascii=False)
    result = _safe_llm_json(OUTLINE_GENERATION_SYSTEM_PROMPT, payload, fallback)
    outline = result.get("outline", fallback_outline)
    risks = result.get("risks", fallback["risks"])
    next_tasks = result.get("next_tasks", fallback["next_tasks"])
    final_markdown, final_json = _build_final_plan(state, outline, risks, next_tasks)
    trace = list(state.get("trace", []))
    trace.append({"tool_name": "outline_generation", "latency_ms": int((perf_counter() - started_at) * 1000), "status": "success"})
    updated = dict(state)
    updated.update({"outline": outline, "risks": risks, "next_tasks": next_tasks, "final_markdown": final_markdown, "final_json": final_json, "trace": trace})
    return updated


def _build_final_plan(state: PlanningState, outline: list[dict], risks: list[dict], next_tasks: list[dict]) -> tuple[str, dict]:
    final_json = {
        "topic": state["topic"],
        "paper_type": state["paper_type"],
        "topic_analysis": state.get("topic_analysis", {}),
        "research_questions": state.get("research_questions", []),
        "research_objectives": state.get("research_objectives", []),
        "research_contents": state.get("research_contents", []),
        "innovations": state.get("innovations", []),
        "technical_route": state.get("technical_route", {}),
        "experiment_plan": state.get("experiment_plan", {}),
        "outline": outline,
        "risks": risks,
        "next_tasks": next_tasks,
    }
    markdown = [
        f"# 论文规划：{state['topic']}",
        "",
        "## 1. 题目可行性分析",
        json.dumps(state.get("topic_analysis", {}), ensure_ascii=False, indent=2),
        "",
        "## 2. 研究问题",
        *[f"- {item.get('id', '')}：{item.get('question', item)}" for item in state.get("research_questions", [])],
        "",
        "## 3. 研究目标",
        *[f"- {item}" for item in state.get("research_objectives", [])],
        "",
        "## 4. 研究内容",
        *[f"- {item.get('name', '')}：{item.get('description', '')}" for item in state.get("research_contents", [])],
        "",
        "## 5. 创新点",
        *[f"- {item.get('name', '')}：{item.get('validation', '')}" for item in state.get("innovations", [])],
        "",
        "## 6. 技术路线",
        json.dumps(state.get("technical_route", {}), ensure_ascii=False, indent=2),
        "",
        "## 7. 实验方案",
        json.dumps(state.get("experiment_plan", {}), ensure_ascii=False, indent=2),
        "",
        "## 8. 论文大纲",
        *[f"- {item.get('chapter', '')}：{'、'.join(item.get('sections', []))}" for item in outline],
        "",
        "## 9. 风险分析",
        *[f"- {item.get('risk', '')}：{item.get('mitigation', '')}" for item in risks],
        "",
        "## 10. 下一步任务清单",
        *[f"- {item.get('time', '')}：{item.get('task', '')}" for item in next_tasks],
    ]
    return "\n".join(markdown), final_json


def _safe_llm_json(system_prompt: str, user_prompt: str, fallback: dict) -> dict:
    try:
        content = LLMService().generate(system_prompt=system_prompt, user_prompt=user_prompt)
        start = content.find("{")
        end = content.rfind("}")
        return json.loads(content[start : end + 1]) if start >= 0 and end > start else fallback
    except Exception:
        return fallback

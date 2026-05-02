from __future__ import annotations


TOO_BROAD_TERMS = ["平台", "系统", "智能", "全流程", "一体化", "大模型", "人工智能"]


def check_topic_feasibility(topic: str, research_direction: str | None = None) -> dict:
    text = f"{topic} {research_direction or ''}".strip()
    broad_hits = [term for term in TOO_BROAD_TERMS if term in text]
    too_broad = len(text) > 45 or len(broad_hits) >= 3
    engineering_like = any(term in text for term in ["系统", "平台", "设计与实现", "助手"])
    has_method_focus = any(term.lower() in text.lower() for term in ["rag", "agent", "检索", "引用", "工作流", "评估"])

    if too_broad and not has_method_focus:
        level = "high_risk"
    elif engineering_like and not has_method_focus:
        level = "medium_risk"
    else:
        level = "feasible"

    suggestions = []
    if too_broad:
        suggestions.append("题目范围偏大，建议收缩到一个清晰任务链路，例如可信问答、论文总结或写作规划。")
    if engineering_like:
        suggestions.append("题目偏工程实现，需要把贡献落到可评估机制，如引用溯源、Agent 编排、质量评价或流程效率。")
    if not has_method_focus:
        suggestions.append("题目中方法焦点不够明确，建议补充 RAG、Agent 工作流、引用校验或评估指标。")

    return {
        "feasibility_level": level,
        "too_broad": too_broad,
        "engineering_like": engineering_like,
        "has_method_focus": has_method_focus,
        "risk_terms": broad_hits,
        "suggestions": suggestions,
    }

from __future__ import annotations

import json
import re
from time import perf_counter

from app.agents.prompts.writing_prompt import SECTION_DRAFT_SYSTEM_PROMPT
from app.agents.state import WritingState
from app.services.llm_service import LLMService


def section_draft_node(state: WritingState) -> WritingState:
    started_at = perf_counter()
    prompt = json.dumps(
        {
            "topic": state.get("topic") or state.get("writing_context", {}).get("project", {}).get("title"),
            "section_type": state["section_type"],
            "section_title": state["section_title"],
            "requirements": state.get("requirements"),
            "writing_context": state.get("writing_context", {}),
            "rules": _section_rules(state["section_type"]),
        },
        ensure_ascii=False,
    )
    try:
        response = LLMService().generate(system_prompt=SECTION_DRAFT_SYSTEM_PROMPT, user_prompt=prompt)
        markdown, section_json = _parse_response(response)
    except Exception:
        markdown = _fallback_markdown(state)
        section_json = {"section_type": state["section_type"], "section_title": state["section_title"], "fallback": True}

    trace = list(state.get("trace", []))
    trace.append({"tool_name": "section_draft", "latency_ms": int((perf_counter() - started_at) * 1000), "status": "success"})
    updated = dict(state)
    updated.update({"section_markdown": markdown, "section_json": section_json, "trace": trace})
    return updated


def _section_rules(section_type: str) -> list[str]:
    rules = {
        "abstract": ["研究背景", "问题", "方法", "实验或验证方式", "预期贡献", "关键词"],
        "introduction": ["研究背景", "研究意义", "现有问题", "本文工作", "论文结构"],
        "related_work": ["按方法类别组织", "代表工作", "优点", "不足", "与本文关系"],
        "method": ["总体架构", "关键模块", "工作流", "数据流"],
        "system_design": ["总体架构", "模块设计", "流程设计", "调用链路"],
        "experiment": ["实验目标", "测试集", "baseline", "指标", "对比实验", "消融实验"],
        "conclusion": ["阶段性总结", "主要贡献", "不足", "未来工作"],
    }
    return rules.get(section_type, ["按用户要求生成草稿"])


def _parse_response(response: str) -> tuple[str, dict]:
    markdown_match = re.search(r"<markdown>(.*?)</markdown>", response, re.DOTALL | re.IGNORECASE)
    json_match = re.search(r"<json>(.*?)</json>", response, re.DOTALL | re.IGNORECASE)
    markdown = markdown_match.group(1).strip() if markdown_match else response.strip()
    section_json = {}
    if json_match:
        try:
            section_json = json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            section_json = {}
    return markdown, section_json


def _fallback_markdown(state: WritingState) -> str:
    title = state["section_title"]
    warnings = "\n".join(f"- {item}" for item in state.get("warnings", []))
    return f"""# {title}

当前材料不足，以下内容为写作草稿框架。

## 写作目标

围绕“{state.get("topic") or "当前论文题目"}”撰写“{title}”章节，内容需要结合已有规划、文献和项目实现情况继续补充。

## 建议结构

{chr(10).join(f"- {item}" for item in _section_rules(state["section_type"]))}

## 注意事项

{warnings or "- 不要编造实验结果或不存在的引用。"}
"""

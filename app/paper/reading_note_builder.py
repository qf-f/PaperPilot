from __future__ import annotations

from typing import Any


def build_reading_note_markdown(summary_json: dict[str, Any]) -> str:
    title = summary_json.get("title") or "论文阅读笔记"
    lines = [f"# {title}", ""]

    for key, heading in [
        ("problem", "核心问题"),
        ("method", "核心方法"),
        ("experiments", "实验设计"),
        ("results", "实验结果"),
        ("conclusion", "主要结论"),
    ]:
        lines.extend([f"## {heading}", str(summary_json.get(key) or "原文中未找到明确依据"), ""])

    for key, heading in [
        ("innovations", "创新点"),
        ("limitations", "局限性"),
        ("inspiration_for_project", "对当前论文项目的启发"),
        ("quotable_points", "可引用观点"),
    ]:
        lines.append(f"## {heading}")
        values = summary_json.get(key) or []
        if not values:
            lines.append("- 原文中未找到明确依据")
        else:
            lines.extend(f"- {value}" for value in values)
        lines.append("")

    return "\n".join(lines).strip() + "\n"

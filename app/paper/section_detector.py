from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any


SECTION_ALIASES: list[tuple[str, list[str]]] = [
    ("Abstract", ["abstract", "摘要"]),
    ("Introduction", ["introduction", "引言", "绪论"]),
    ("Related Work", ["related work", "background", "literature review", "相关工作", "研究现状"]),
    ("Method", ["method", "methods", "methodology", "approach", "模型", "方法", "方法设计"]),
    ("Model", ["model", "architecture", "framework", "模型结构", "系统架构"]),
    ("Experiment", ["experiment", "experiments", "experimental setup", "实验", "实验设计"]),
    ("Results", ["result", "results", "evaluation", "结果", "评价", "评估"]),
    ("Discussion", ["discussion", "analysis", "讨论", "分析"]),
    ("Conclusion", ["conclusion", "conclusions", "结论", "总结"]),
    ("References", ["references", "bibliography", "参考文献"]),
]


HEADING_PATTERN = re.compile(
    r"^\s*((\d+(\.\d+)*)|[IVX]+)?\s*[\.\、\)]?\s*([A-Za-z][A-Za-z\s\-]{2,60}|[\u4e00-\u9fa5]{2,20})\s*$"
)


def normalize_section_name(raw_title: str | None, content: str | None = None) -> str:
    candidate = (raw_title or "").strip()
    from_metadata = bool(candidate)
    if not candidate and content:
        candidate = _guess_heading_from_content(content)

    normalized = candidate.lower().strip()
    for canonical, aliases in SECTION_ALIASES:
        if any(alias in normalized for alias in aliases):
            return canonical

    return candidate[:80] if from_metadata and candidate else "Unknown"


def group_chunks_by_section(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: "OrderedDict[str, list[dict[str, Any]]]" = OrderedDict()

    for chunk in chunks:
        section_name = normalize_section_name(
            raw_title=chunk.get("section_title"),
            content=chunk.get("content"),
        )
        grouped.setdefault(section_name, []).append(chunk)

    groups: list[dict[str, Any]] = []
    for section_name, section_chunks in grouped.items():
        groups.append(
            {
                "section_name": section_name,
                "is_references": section_name == "References",
                "chunks": section_chunks,
                "chunk_count": len(section_chunks),
            }
        )
    return groups


def _guess_heading_from_content(content: str) -> str:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return ""

    first_line = lines[0]
    if len(first_line) > 80:
        return ""

    match = HEADING_PATTERN.match(first_line)
    if not match:
        return ""
    normalized = first_line.lower().strip()
    if not any(alias in normalized for _, aliases in SECTION_ALIASES for alias in aliases):
        return ""

    return first_line

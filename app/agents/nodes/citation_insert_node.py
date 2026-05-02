from __future__ import annotations

import re
from time import perf_counter

from app.agents.state import WritingState


CITATION_RE = re.compile(r"\[(\d+)\]")


def citation_insert_node(state: WritingState) -> WritingState:
    started_at = perf_counter()
    markdown = state.get("section_markdown", "")
    citations = state.get("citations", [])
    allowed = {int(item["index"]) for item in citations}
    warnings = list(state.get("warnings", []))

    used = {int(match.group(1)) for match in CITATION_RE.finditer(markdown)}
    invalid = used - allowed
    if invalid:
        warnings.append(f"草稿中出现不存在的引用编号 {sorted(invalid)}，已移除这些编号。")
        markdown = CITATION_RE.sub(lambda m: m.group(0) if int(m.group(1)) in allowed else "", markdown)
    if not used and citations and state.get("section_type") in {"related_work", "introduction"}:
        warnings.append("草稿未充分使用已有文献引用，建议人工补充关键引用。")

    section_json = dict(state.get("section_json", {}))
    section_json["used_citation_indexes"] = sorted(list(used & allowed))
    section_json["warnings"] = warnings

    trace = list(state.get("trace", []))
    trace.append({"tool_name": "citation_insert", "latency_ms": int((perf_counter() - started_at) * 1000), "status": "success"})
    updated = dict(state)
    updated.update({"section_markdown": markdown, "section_json": section_json, "warnings": warnings, "trace": trace})
    return updated

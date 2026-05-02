from __future__ import annotations

import json
import re
from typing import Any


MARKDOWN_BLOCK_RE = re.compile(r"<markdown>(.*?)</markdown>", re.DOTALL | re.IGNORECASE)
JSON_BLOCK_RE = re.compile(r"<json>(.*?)</json>", re.DOTALL | re.IGNORECASE)


DEFAULT_SUMMARY_JSON: dict[str, Any] = {
    "title": "",
    "research_field": "",
    "keywords": [],
    "problem": "原文中未找到明确依据",
    "method": "原文中未找到明确依据",
    "experiments": "原文中未找到明确依据",
    "results": "原文中未找到明确依据",
    "conclusion": "原文中未找到明确依据",
    "innovations": [],
    "limitations": [],
    "inspiration_for_project": [],
    "quotable_points": [],
    "citations": [],
}


def build_chunk_context(chunks: list[dict[str, Any]], max_chars: int) -> str:
    parts: list[str] = []
    used = 0

    for chunk in chunks:
        citation_index = chunk.get("citation_index")
        file_name = chunk.get("file_name", "")
        page_number = chunk.get("page_number")
        section_title = chunk.get("section_title") or ""
        chunk_index = chunk.get("chunk_index")
        content = str(chunk.get("content") or "").strip()
        if not content:
            continue

        header = (
            f"[{citation_index}] 来源：file_name={file_name}, "
            f"page={page_number}, section={section_title}, chunk={chunk_index}\n"
            "内容：\n"
        )
        remaining = max_chars - used - len(header)
        if remaining <= 0:
            break
        part = f"{header}{content[:remaining]}"
        parts.append(part)
        used += len(part)
        if used >= max_chars:
            break

    return "\n\n".join(parts)


def parse_section_summary_response(
    response: str,
    section_name: str,
    citations: list[dict[str, Any]],
) -> dict[str, Any]:
    data = extract_first_json(response)
    if isinstance(data, dict):
        data.setdefault("section_name", section_name)
        data.setdefault("summary", "该部分未提供明确依据")
        data.setdefault("key_points", [])
        data.setdefault("citations", citations)
        return data

    return {
        "section_name": section_name,
        "summary": response.strip() or "该部分未提供明确依据",
        "key_points": [],
        "citations": citations,
    }


def parse_final_summary_response(
    response: str,
    citations: list[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    markdown_match = MARKDOWN_BLOCK_RE.search(response)
    json_match = JSON_BLOCK_RE.search(response)

    markdown = markdown_match.group(1).strip() if markdown_match else response.strip()
    parsed_json = extract_first_json(json_match.group(1)) if json_match else extract_first_json(response)

    summary_json = dict(DEFAULT_SUMMARY_JSON)
    if isinstance(parsed_json, dict):
        summary_json.update(parsed_json)
    summary_json["citations"] = citations

    return markdown, summary_json


def extract_first_json(text: str) -> Any:
    cleaned = strip_markdown_fence(text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None


def strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped

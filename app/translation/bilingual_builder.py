from __future__ import annotations

from typing import Any


def build_translation_markdown(
    document_name: str,
    translated_segments: list[dict[str, Any]],
    output_style: str,
    warnings: list[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    warnings = warnings or []
    lines = [f"# 论文翻译：{document_name}", ""]
    if warnings:
        lines.extend(["## 翻译提醒", *[f"- {warning}" for warning in warnings], ""])

    last_section = None
    for segment in translated_segments:
        section_title = segment.get("section_title") or "未命名章节"
        if section_title != last_section:
            lines.extend([f"## {section_title}", ""])
            last_section = section_title
        page_info = _page_info(segment)
        lines.extend([f"<!-- page={page_info}, chunks={','.join(map(str, segment.get('chunk_indexes', [])))} -->", ""])
        if output_style == "bilingual":
            lines.extend(
                [
                    "### 原文",
                    "",
                    segment.get("source_text", "").strip(),
                    "",
                    "### 译文",
                    "",
                    segment.get("translated_text", "").strip() or "（该段翻译失败，请重试或人工翻译。）",
                    "",
                    "---",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    segment.get("translated_text", "").strip() or "（该段翻译失败，请重试或人工翻译。）",
                    "",
                ]
            )

    content_json = {
        "document_name": document_name,
        "output_style": output_style,
        "segment_count": len(translated_segments),
        "warnings": warnings,
        "segments": [
            {
                "segment_index": item.get("segment_index"),
                "page_number": item.get("page_number"),
                "page_numbers": item.get("page_numbers", []),
                "section_title": item.get("section_title", ""),
                "chunk_indexes": item.get("chunk_indexes", []),
                "source_text": item.get("source_text", ""),
                "translated_text": item.get("translated_text", ""),
                "warning": item.get("warning", ""),
            }
            for item in translated_segments
        ],
    }
    return "\n".join(lines).strip() + "\n", content_json


def _page_info(segment: dict[str, Any]) -> str:
    pages = segment.get("page_numbers") or []
    if pages:
        return ",".join(str(page) for page in pages)
    page_number = segment.get("page_number")
    return str(page_number) if page_number is not None else "unknown"

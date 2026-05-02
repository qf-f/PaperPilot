from __future__ import annotations

import re
from typing import Any


REFERENCE_MARKERS = ["references", "bibliography", "参考文献", "参考书目"]


def extract_reference_text(chunks: list[dict[str, Any]], max_chars: int = 50000) -> tuple[str, str | None]:
    if not chunks:
        return "", "Document has no chunks"

    start_index = _find_reference_start_by_section(chunks)
    marker_offset = None

    if start_index is None:
        start_index, marker_offset = _find_reference_start_by_content(chunks)

    if start_index is None:
        return "", "No References/Bibliography section found"

    selected = chunks[start_index:]
    texts: list[str] = []
    for index, chunk in enumerate(selected):
        content = str(chunk.get("content") or "")
        if index == 0 and marker_offset is not None:
            content = content[marker_offset:]
        texts.append(content)

    reference_text = "\n".join(texts).strip()
    return reference_text[:max_chars], None


def _find_reference_start_by_section(chunks: list[dict[str, Any]]) -> int | None:
    for index, chunk in enumerate(chunks):
        section_title = str(chunk.get("section_title") or "").lower()
        if any(marker in section_title for marker in REFERENCE_MARKERS):
            return index
    return None


def _find_reference_start_by_content(chunks: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    pattern = re.compile(r"(?im)^\s*(references|bibliography|参考文献|参考书目)\s*$")
    for index, chunk in enumerate(chunks):
        content = str(chunk.get("content") or "")
        match = pattern.search(content)
        if match:
            return index, match.start()
    return None, None

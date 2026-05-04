from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

import fitz
from docx import Document as DocxDocument


class ParsedBlock(TypedDict, total=False):
    text: str
    block_type: str
    heading_level: int | None
    section_title: str
    section_path: list[str]
    page_number: int | None
    paragraph_index: int
    char_start: int
    char_end: int
    is_reference_section: bool


CHINESE_SECTION_TITLES = {
    "摘要": "摘要",
    "关键词": "关键词",
    "引言": "引言",
    "相关工作": "相关工作",
    "方法": "方法",
    "实验": "实验",
    "结果": "结果",
    "讨论": "讨论",
    "结论": "结论",
    "结语": "结论",
    "总结": "总结",
    "展望": "展望",
    "参考文献": "参考文献",
}
ENGLISH_SECTION_TITLES = {
    "abstract": "Abstract",
    "keywords": "Keywords",
    "introduction": "Introduction",
    "related work": "Related Work",
    "method": "Method",
    "methods": "Methods",
    "experiments": "Experiments",
    "results": "Results",
    "discussion": "Discussion",
    "conclusion": "Conclusion",
    "references": "References",
}
REFERENCE_SECTIONS = {"参考文献", "References"}


def _strip_heading_prefix(text: str) -> str:
    stripped = text.strip()
    stripped = re.sub(r"^第\s*[一二三四五六七八九十百0-9]+\s*[章节篇]\s*", "", stripped)
    stripped = re.sub(r"^\d+(?:\.\d+)*\s*[.)、．]?\s*", "", stripped)
    stripped = re.sub(r"^[IVXivx]+\s*[.)、．]\s*", "", stripped)
    return stripped.strip(" ：:.-—")


def _detect_section_heading(text: str) -> tuple[str, int] | None:
    candidate = _strip_heading_prefix(text)
    compact_candidate = re.sub(r"\s+", " ", candidate).strip()
    if compact_candidate in CHINESE_SECTION_TITLES:
        return CHINESE_SECTION_TITLES[compact_candidate], 1

    lowered = compact_candidate.casefold()
    if lowered in ENGLISH_SECTION_TITLES:
        return ENGLISH_SECTION_TITLES[lowered], 1
    return None


def _is_reference_section(section_title: str) -> bool:
    return section_title in REFERENCE_SECTIONS


def _make_block(
    text: str,
    paragraph_index: int,
    page_number: int | None,
    section_title: str,
    section_path: list[str],
    block_type: str = "text",
    heading_level: int | None = None,
    char_start: int = 0,
    char_end: int | None = None,
    is_reference_section: bool = False,
) -> ParsedBlock:
    return {
        "page_number": page_number,
        "section_title": section_title,
        "section_path": list(section_path),
        "block_type": block_type,
        "heading_level": heading_level,
        "paragraph_index": paragraph_index,
        "char_start": char_start,
        "char_end": len(text) if char_end is None else char_end,
        "is_reference_section": is_reference_section,
        "text": text,
    }


def _split_text_paragraphs(text: str) -> list[tuple[str, int, int]]:
    paragraphs: list[tuple[str, int, int]] = []
    current_lines: list[str] = []
    current_start: int | None = None
    search_offset = 0

    def flush(end_offset: int) -> None:
        nonlocal current_lines, current_start
        paragraph = "\n".join(current_lines).strip()
        if paragraph and current_start is not None:
            paragraphs.append((paragraph, current_start, end_offset))
        current_lines = []
        current_start = None

    for raw_line in text.splitlines():
        line_start = text.find(raw_line, search_offset)
        if line_start < 0:
            line_start = search_offset
        line_end = line_start + len(raw_line)
        search_offset = line_end + 1
        stripped = raw_line.strip()
        if not stripped:
            flush(line_start)
            continue
        if current_start is None:
            current_start = line_start + (len(raw_line) - len(raw_line.lstrip()))
        current_lines.append(stripped)

    flush(len(text))
    return paragraphs


def parse_pdf(file_path: str | Path) -> list[ParsedBlock]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    try:
        blocks: list[ParsedBlock] = []
        current_section = ""
        current_section_path: list[str] = []
        in_reference_section = False
        paragraph_index = 0

        with fitz.open(path) as doc:
            for page_index, page in enumerate(doc, start=1):
                page_text = page.get_text("text").strip()
                if not page_text:
                    continue

                current_lines: list[str] = []
                current_start: int | None = None
                search_offset = 0

                def flush(end_offset: int) -> None:
                    nonlocal current_lines, current_start, paragraph_index
                    paragraph = "\n".join(current_lines).strip()
                    if paragraph and current_start is not None:
                        blocks.append(
                            _make_block(
                                text=paragraph,
                                paragraph_index=paragraph_index,
                                page_number=page_index,
                                section_title=current_section,
                                section_path=current_section_path,
                                heading_level=None,
                                char_start=current_start,
                                char_end=end_offset,
                                is_reference_section=in_reference_section,
                            )
                        )
                        paragraph_index += 1
                    current_lines = []
                    current_start = None

                for raw_line in page_text.splitlines():
                    line_start = page_text.find(raw_line, search_offset)
                    if line_start < 0:
                        line_start = search_offset
                    line_end = line_start + len(raw_line)
                    search_offset = line_end + 1
                    stripped = raw_line.strip()
                    if not stripped:
                        flush(line_start)
                        continue

                    heading = _detect_section_heading(stripped)
                    if heading is not None:
                        flush(line_start)
                        current_section, heading_level = heading
                        current_section_path = [current_section]
                        if _is_reference_section(current_section):
                            in_reference_section = True
                        continue

                    if current_start is None:
                        current_start = line_start + (len(raw_line) - len(raw_line.lstrip()))
                    current_lines.append(stripped)

                flush(len(page_text))
        return blocks
    except Exception as exc:
        raise RuntimeError(f"Failed to parse PDF '{path}': {exc}") from exc


def _heading_level_from_style(style_name: str) -> int | None:
    match = re.search(r"heading\s*(\d+)", style_name, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _update_section_path(section_path: list[str], heading_level: int, title: str) -> list[str]:
    if heading_level <= 0:
        return [title]
    updated = list(section_path[: heading_level - 1])
    updated.append(title)
    return updated


def parse_docx(file_path: str | Path) -> list[ParsedBlock]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"DOCX file not found: {path}")

    try:
        doc = DocxDocument(path)
        blocks: list[ParsedBlock] = []
        current_section = ""
        current_heading_level: int | None = None
        current_section_path: list[str] = []
        current_lines: list[str] = []
        paragraph_index = 0
        char_cursor = 0
        current_block_start = 0

        def flush_section() -> None:
            nonlocal paragraph_index, current_block_start
            if current_lines:
                text = "\n".join(current_lines).strip()
                blocks.append(
                    _make_block(
                        text=text,
                        paragraph_index=paragraph_index,
                        page_number=1,
                        section_title=current_section,
                        section_path=current_section_path,
                        heading_level=current_heading_level,
                        char_start=current_block_start,
                        char_end=current_block_start + len(text),
                        is_reference_section=_is_reference_section(current_section),
                    )
                )
                paragraph_index += 1
                current_lines.clear()
                current_block_start = char_cursor

        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if not text:
                char_cursor += 1
                continue
            style_name = paragraph.style.name if paragraph.style else ""
            heading_level = _heading_level_from_style(style_name)
            if heading_level is not None:
                flush_section()
                current_section = text
                current_heading_level = heading_level
                current_section_path = _update_section_path(current_section_path, heading_level, text)
                current_block_start = char_cursor + len(text) + 1
            else:
                if not current_lines:
                    current_block_start = char_cursor
                current_lines.append(text)
            char_cursor += len(text) + 1

        flush_section()

        if not blocks and current_section:
            blocks.append(
                _make_block(
                    text=current_section,
                    paragraph_index=0,
                    page_number=1,
                    section_title=current_section,
                    section_path=current_section_path,
                    heading_level=current_heading_level,
                    char_start=0,
                    char_end=len(current_section),
                    is_reference_section=_is_reference_section(current_section),
                )
            )

        return blocks
    except Exception as exc:
        raise RuntimeError(f"Failed to parse DOCX '{path}': {exc}") from exc


def _read_text_file(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("utf-8", b"", 0, 1, f"Unable to decode text file: {path}")


def parse_txt(file_path: str | Path) -> list[ParsedBlock]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"TXT file not found: {path}")

    try:
        text = _read_text_file(path).strip()
        if not text:
            return []
        return [
            _make_block(
                text=text,
                paragraph_index=0,
                page_number=1,
                section_title="",
                section_path=[],
                char_start=0,
                char_end=len(text),
                is_reference_section=False,
            )
        ]
    except Exception as exc:
        raise RuntimeError(f"Failed to parse TXT '{path}': {exc}") from exc


def parse_markdown(file_path: str | Path) -> list[ParsedBlock]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Markdown file not found: {path}")

    try:
        text = _read_text_file(path).strip()
        if not text:
            return []

        blocks: list[ParsedBlock] = []
        current_section = ""
        current_heading_level: int | None = None
        current_section_path: list[str] = []
        current_lines: list[str] = []
        paragraph_index = 0
        char_cursor = 0
        current_block_start = 0

        def flush_section() -> None:
            nonlocal paragraph_index, current_block_start
            if current_lines:
                block_text = "\n".join(current_lines).strip()
                blocks.append(
                    _make_block(
                        text=block_text,
                        paragraph_index=paragraph_index,
                        page_number=1,
                        section_title=current_section,
                        section_path=current_section_path,
                        heading_level=current_heading_level,
                        char_start=current_block_start,
                        char_end=current_block_start + len(block_text),
                        is_reference_section=_is_reference_section(current_section),
                    )
                )
                paragraph_index += 1
                current_lines.clear()
                current_block_start = char_cursor

        for line in text.splitlines():
            stripped = line.strip()
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if heading_match:
                flush_section()
                current_heading_level = len(heading_match.group(1))
                current_section = heading_match.group(2).strip()
                current_section_path = _update_section_path(
                    current_section_path,
                    current_heading_level,
                    current_section,
                )
                current_block_start = char_cursor + len(line) + 1
            elif stripped:
                if not current_lines:
                    current_block_start = char_cursor
                current_lines.append(stripped)
            char_cursor += len(line) + 1

        flush_section()
        return blocks or [
            _make_block(
                text=text,
                paragraph_index=0,
                page_number=1,
                section_title="",
                section_path=[],
                char_start=0,
                char_end=len(text),
                is_reference_section=False,
            )
        ]
    except Exception as exc:
        raise RuntimeError(f"Failed to parse Markdown '{path}': {exc}") from exc


def parse_file(file_path: str | Path, file_type: str) -> list[ParsedBlock]:
    normalized = file_type.lower().lstrip(".")
    if normalized == "pdf":
        return parse_pdf(file_path)
    if normalized == "docx":
        return parse_docx(file_path)
    if normalized == "txt":
        return parse_txt(file_path)
    if normalized in {"md", "markdown"}:
        return parse_markdown(file_path)
    raise ValueError(f"Unsupported parser file type: {file_type}")

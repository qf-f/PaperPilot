from pathlib import Path

import fitz
from docx import Document as DocxDocument


ParsedBlock = dict[str, str | int | None]


def parse_pdf(file_path: str | Path) -> list[ParsedBlock]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    try:
        blocks: list[ParsedBlock] = []
        with fitz.open(path) as doc:
            for page_index, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                if text:
                    blocks.append(
                        {
                            "page_number": page_index,
                            "section_title": "",
                            "text": text,
                        }
                    )
        return blocks
    except Exception as exc:
        raise RuntimeError(f"Failed to parse PDF '{path}': {exc}") from exc


def parse_docx(file_path: str | Path) -> list[ParsedBlock]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"DOCX file not found: {path}")

    try:
        doc = DocxDocument(path)
        blocks: list[ParsedBlock] = []
        current_section = ""
        current_lines: list[str] = []

        def flush_section() -> None:
            if current_lines:
                blocks.append(
                    {
                        "page_number": 1,
                        "section_title": current_section,
                        "text": "\n".join(current_lines).strip(),
                    }
                )
                current_lines.clear()

        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue
            style_name = paragraph.style.name if paragraph.style else ""
            if style_name.lower().startswith("heading"):
                flush_section()
                current_section = text
            else:
                current_lines.append(text)

        flush_section()

        if not blocks and current_section:
            blocks.append({"page_number": 1, "section_title": current_section, "text": current_section})

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
        return [{"page_number": 1, "section_title": "", "text": text}] if text else []
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
        current_lines: list[str] = []

        def flush_section() -> None:
            if current_lines:
                blocks.append(
                    {
                        "page_number": 1,
                        "section_title": current_section,
                        "text": "\n".join(current_lines).strip(),
                    }
                )
                current_lines.clear()

        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                flush_section()
                current_section = stripped.lstrip("#").strip()
            elif stripped:
                current_lines.append(stripped)

        flush_section()
        return blocks or [{"page_number": 1, "section_title": "", "text": text}]
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

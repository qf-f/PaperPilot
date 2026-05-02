from __future__ import annotations

import re
from pathlib import Path


def safe_filename(value: str, default: str = "paperpilot-output") -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "_", value).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:120] or default


def export_markdown(content: str, file_path: str) -> str:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() != ".md":
        path = path.with_suffix(".md")
    path.write_text(content or "", encoding="utf-8")
    return str(path)

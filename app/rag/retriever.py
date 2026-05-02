from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    project_id: str
    file_name: str
    chunk_index: int
    page_number: int | None
    section_title: str
    content: str
    score: float
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

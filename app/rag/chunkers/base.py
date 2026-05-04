from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypedDict

from app.rag.parser import ParsedBlock


class Chunk(TypedDict, total=False):
    chunk_index: int
    page_number: int | None
    section_title: str
    content: str
    token_count: int
    metadata: dict[str, Any]


def estimate_token_count(text: str) -> int:
    return len(text)


def validate_chunk_params(chunk_size: int, overlap: int) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0:
        raise ValueError("overlap cannot be negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")


def split_single_text(text: str, chunk_size: int, overlap: int) -> list[tuple[str, int, int]]:
    normalized = text.strip()
    if not normalized:
        return []
    validate_chunk_params(chunk_size, overlap)

    chunks: list[tuple[str, int, int]] = []
    start = 0
    text_length = len(normalized)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        raw_chunk = normalized[start:end]
        chunk = raw_chunk.strip()
        if chunk:
            leading_trim = len(raw_chunk) - len(raw_chunk.lstrip())
            trailing_trim = len(raw_chunk.rstrip())
            chunks.append((chunk, start + leading_trim, start + trailing_trim))
        if end >= text_length:
            break
        start = max(0, end - overlap)

    return chunks


class BaseChunker(ABC):
    strategy_name: str

    def __init__(self, chunk_size: int = 500, overlap: int = 80) -> None:
        validate_chunk_params(chunk_size, overlap)
        self.chunk_size = chunk_size
        self.overlap = overlap

    @abstractmethod
    def chunk(self, blocks: list[ParsedBlock]) -> list[Chunk]:
        raise NotImplementedError

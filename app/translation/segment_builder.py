from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session


DEFAULT_SEGMENT_CHARS = 3500
MIN_MERGE_CHARS = 800


def load_translation_segments(
    db: Session,
    project_id: UUID,
    document_id: UUID,
    range_type: str,
    page_from: int | None = None,
    page_to: int | None = None,
    chunk_from: int | None = None,
    chunk_to: int | None = None,
) -> list[dict[str, Any]]:
    from app.db.models.document_chunk import DocumentChunk

    chunks = list(
        db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.project_id == project_id, DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        .scalars()
        .all()
    )
    chunk_dicts = [
        {
            "id": str(chunk.id),
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.page_number,
            "section_title": chunk.section_title or "",
            "content": chunk.content or "",
        }
        for chunk in chunks
    ]
    return build_segments_from_chunks(
        chunk_dicts,
        range_type=range_type,
        page_from=page_from,
        page_to=page_to,
        chunk_from=chunk_from,
        chunk_to=chunk_to,
    )


def build_segments_from_chunks(
    chunks: list[dict[str, Any]],
    range_type: str = "full",
    page_from: int | None = None,
    page_to: int | None = None,
    chunk_from: int | None = None,
    chunk_to: int | None = None,
    max_chars: int = DEFAULT_SEGMENT_CHARS,
) -> list[dict[str, Any]]:
    filtered = _filter_chunks(chunks, range_type, page_from, page_to, chunk_from, chunk_to)
    if not filtered:
        raise ValueError("No document chunks found for the requested translation range")

    segments: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    current_len = 0
    for chunk in filtered:
        content = (chunk.get("content") or "").strip()
        if not content:
            continue
        chunk_len = len(content)
        should_flush = current and (
            current_len + chunk_len > max_chars
            or _section_changed(current[-1], chunk)
            and current_len >= MIN_MERGE_CHARS
        )
        if should_flush:
            segments.append(_make_segment(len(segments) + 1, current))
            current = []
            current_len = 0
        current.append(chunk)
        current_len += chunk_len

    if current:
        segments.append(_make_segment(len(segments) + 1, current))
    if not segments:
        raise ValueError("Selected chunks are empty and cannot be translated")
    return segments


def _filter_chunks(
    chunks: list[dict[str, Any]],
    range_type: str,
    page_from: int | None,
    page_to: int | None,
    chunk_from: int | None,
    chunk_to: int | None,
) -> list[dict[str, Any]]:
    ordered = sorted(chunks, key=lambda item: item.get("chunk_index", 0))
    if range_type == "full":
        return ordered
    if range_type == "pages":
        if page_from is None or page_to is None:
            raise ValueError("page_from and page_to are required when range_type=pages")
        return [
            chunk
            for chunk in ordered
            if chunk.get("page_number") is not None and page_from <= int(chunk["page_number"]) <= page_to
        ]
    if range_type == "chunks":
        if chunk_from is None or chunk_to is None:
            raise ValueError("chunk_from and chunk_to are required when range_type=chunks")
        return [chunk for chunk in ordered if chunk_from <= int(chunk.get("chunk_index", -1)) <= chunk_to]
    raise ValueError(f"Unsupported range_type: {range_type}")


def _section_changed(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return bool(left.get("section_title") and right.get("section_title") and left.get("section_title") != right.get("section_title"))


def _make_segment(index: int, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    section_title = next((chunk.get("section_title") for chunk in chunks if chunk.get("section_title")), "")
    page_numbers = [chunk.get("page_number") for chunk in chunks if chunk.get("page_number") is not None]
    chunk_indexes = [int(chunk.get("chunk_index", 0)) for chunk in chunks]
    source_text = "\n\n".join(chunk.get("content", "").strip() for chunk in chunks if chunk.get("content"))
    return {
        "segment_index": index,
        "page_number": page_numbers[0] if page_numbers else None,
        "page_numbers": sorted(set(page_numbers)),
        "section_title": section_title,
        "chunk_indexes": chunk_indexes,
        "source_text": source_text,
    }

from __future__ import annotations

from typing import Any

from app.rag.chunkers.base import BaseChunker, Chunk, estimate_token_count, split_single_text
from app.rag.parser import ParsedBlock


def _metadata_for_block(
    block: ParsedBlock,
    section_title: str,
    page_number: object,
    char_start: int | None,
    char_end: int | None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "source": "parser",
        "page_number": page_number,
        "section_title": section_title,
        "chunk_strategy": "fixed",
        "section_path": block.get("section_path") or [],
        "char_start": char_start,
        "char_end": char_end,
        "is_reference_section": bool(block.get("is_reference_section", False)),
    }
    return metadata


class FixedChunker(BaseChunker):
    strategy_name = "fixed"

    def chunk(self, blocks: list[ParsedBlock]) -> list[Chunk]:
        chunks: list[Chunk] = []
        chunk_index = 0

        for block in blocks:
            text = str(block.get("text") or "").strip()
            if not text:
                continue

            page_number = block.get("page_number")
            section_title = str(block.get("section_title") or "")
            block_char_start = block.get("char_start")
            base_char_start = int(block_char_start) if isinstance(block_char_start, int) else 0

            for content, relative_start, relative_end in split_single_text(
                text,
                chunk_size=self.chunk_size,
                overlap=self.overlap,
            ):
                chunks.append(
                    {
                        "chunk_index": chunk_index,
                        "page_number": page_number,
                        "section_title": section_title,
                        "content": content,
                        "token_count": estimate_token_count(content),
                        "metadata": _metadata_for_block(
                            block=block,
                            section_title=section_title,
                            page_number=page_number,
                            char_start=base_char_start + relative_start,
                            char_end=base_char_start + relative_end,
                        ),
                    }
                )
                chunk_index += 1

        return chunks

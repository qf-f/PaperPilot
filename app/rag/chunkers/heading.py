from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.rag.chunkers.base import BaseChunker, Chunk, estimate_token_count, split_single_text
from app.rag.parser import ParsedBlock


@dataclass
class _SectionGroup:
    section_title: str
    section_path: list[str]
    page_number: object
    blocks: list[ParsedBlock] = field(default_factory=list)
    is_reference_section: bool = False

    @property
    def text(self) -> str:
        return "\n\n".join(str(block.get("text") or "").strip() for block in self.blocks if block.get("text"))

    @property
    def char_start(self) -> int | None:
        starts = [block.get("char_start") for block in self.blocks if isinstance(block.get("char_start"), int)]
        return min(starts) if starts else None

    @property
    def char_end(self) -> int | None:
        ends = [block.get("char_end") for block in self.blocks if isinstance(block.get("char_end"), int)]
        return max(ends) if ends else None


def _section_path(block: ParsedBlock, section_title: str) -> list[str]:
    raw_path = block.get("section_path")
    if isinstance(raw_path, list):
        return [str(item) for item in raw_path if str(item)]
    if section_title:
        return [section_title]
    return []


def _section_key(block: ParsedBlock) -> tuple[str, ...]:
    section_title = str(block.get("section_title") or "")
    path = _section_path(block, section_title)
    return tuple(path or [section_title])


def _content_with_section(section_title: str, text: str) -> str:
    if section_title:
        return f"[Section: {section_title}]\n{text}"
    return text


class HeadingAwareChunker(BaseChunker):
    strategy_name = "heading"

    def chunk(self, blocks: list[ParsedBlock]) -> list[Chunk]:
        groups = self._group_blocks(blocks)
        chunks: list[Chunk] = []
        chunk_index = 0

        for group in groups:
            content_text = _content_with_section(group.section_title, group.text.strip())
            if not content_text.strip():
                continue
            for content, _, _ in split_single_text(
                content_text,
                chunk_size=self.chunk_size,
                overlap=self.overlap,
            ):
                chunks.append(
                    {
                        "chunk_index": chunk_index,
                        "page_number": group.page_number,
                        "section_title": group.section_title,
                        "content": content,
                        "token_count": estimate_token_count(content),
                        "metadata": self._metadata_for_group(group),
                    }
                )
                chunk_index += 1

        return chunks

    def _group_blocks(self, blocks: list[ParsedBlock]) -> list[_SectionGroup]:
        groups: list[_SectionGroup] = []
        current_group: _SectionGroup | None = None
        current_key: tuple[str, ...] | None = None

        for block in blocks:
            text = str(block.get("text") or "").strip()
            if not text:
                continue
            section_title = str(block.get("section_title") or "")
            section_path = _section_path(block, section_title)
            key = _section_key(block)
            if current_group is None or key != current_key:
                current_group = _SectionGroup(
                    section_title=section_title,
                    section_path=section_path,
                    page_number=block.get("page_number"),
                    is_reference_section=bool(block.get("is_reference_section", False)),
                )
                groups.append(current_group)
                current_key = key

            current_group.blocks.append(block)
            current_group.is_reference_section = current_group.is_reference_section or bool(
                block.get("is_reference_section", False)
            )

        return groups

    @staticmethod
    def _metadata_for_group(group: _SectionGroup) -> dict[str, Any]:
        return {
            "source": "parser",
            "page_number": group.page_number,
            "section_title": group.section_title,
            "chunk_strategy": "heading",
            "section_path": group.section_path,
            "char_start": group.char_start,
            "char_end": group.char_end,
            "is_reference_section": group.is_reference_section,
        }

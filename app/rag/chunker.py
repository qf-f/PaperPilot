from app.rag.chunkers import Chunk, FixedChunker, estimate_token_count
from app.rag.chunkers.base import split_single_text
from app.rag.parser import ParsedBlock


def _split_single_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    return [content for content, _, _ in split_single_text(text, chunk_size=chunk_size, overlap=overlap)]


def chunk_text_blocks(
    blocks: list[ParsedBlock],
    chunk_size: int = 500,
    overlap: int = 80,
) -> list[Chunk]:
    return FixedChunker(chunk_size=chunk_size, overlap=overlap).chunk(blocks)

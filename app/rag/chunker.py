from app.rag.parser import ParsedBlock


Chunk = dict[str, object]


def estimate_token_count(text: str) -> int:
    return len(text)


def _split_single_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0:
        raise ValueError("overlap cannot be negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[str] = []
    start = 0
    text_length = len(normalized)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_length:
            break
        start = max(0, end - overlap)

    return chunks


def chunk_text_blocks(
    blocks: list[ParsedBlock],
    chunk_size: int = 500,
    overlap: int = 80,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    chunk_index = 0

    for block in blocks:
        text = str(block.get("text") or "").strip()
        if not text:
            continue

        page_number = block.get("page_number")
        section_title = str(block.get("section_title") or "")

        for content in _split_single_text(text, chunk_size=chunk_size, overlap=overlap):
            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "page_number": page_number,
                    "section_title": section_title,
                    "content": content,
                    "token_count": estimate_token_count(content),
                    "metadata": {
                        "source": "parser",
                        "page_number": page_number,
                        "section_title": section_title,
                    },
                }
            )
            chunk_index += 1

    return chunks

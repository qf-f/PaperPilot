from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.rag.chunker import Chunk


def insert_document_chunks(db: Session, document: Document, chunks: list[Chunk]) -> int:
    chunk_rows = [
        DocumentChunk(
            project_id=document.project_id,
            document_id=document.id,
            chunk_index=int(chunk["chunk_index"]),
            page_number=chunk.get("page_number"),
            section_title=chunk.get("section_title") or "",
            content=str(chunk["content"]),
            token_count=int(chunk["token_count"]),
            embedding=None,
            chunk_metadata=dict(chunk.get("metadata") or {}),
        )
        for chunk in chunks
    ]

    db.add_all(chunk_rows)
    return len(chunk_rows)

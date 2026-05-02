from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.db.models.task import AsyncTask
from app.db.session import SessionLocal
from app.services.embedding_service import EmbeddingService


settings = get_settings()


def _get_latest_embedding_task(db: Session, document_id: UUID) -> AsyncTask | None:
    stmt = (
        select(AsyncTask)
        .where(
            AsyncTask.task_type == "embed_document_chunks",
            AsyncTask.target_id == document_id,
        )
        .order_by(AsyncTask.created_at.desc())
    )
    return db.execute(stmt).scalars().first()


def _mark_failed(document_id: UUID, message: str) -> None:
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        if document is not None:
            document.index_status = "failed"
            document.index_error_message = message

        task = _get_latest_embedding_task(db, document_id)
        if task is not None:
            task.status = "failed"
            task.error_message = message

        db.commit()


def embed_document_chunks_task(document_id: str) -> dict[str, str | int]:
    parsed_document_id = UUID(document_id)

    with SessionLocal() as db:
        try:
            document = db.get(Document, parsed_document_id)
            if document is None:
                raise ValueError(f"Document not found: {document_id}")
            if document.parse_status != "parsed":
                raise ValueError(
                    f"Document must be parsed before embedding, current parse_status={document.parse_status}"
                )

            task = _get_latest_embedding_task(db, document.id)
            if task is not None:
                task.status = "running"
                task.error_message = None

            document.index_status = "indexing"
            document.index_error_message = None
            db.commit()

            chunks = list(
                db.execute(
                    select(DocumentChunk)
                    .where(DocumentChunk.document_id == document.id)
                    .order_by(DocumentChunk.chunk_index.asc())
                )
                .scalars()
                .all()
            )
            non_empty_chunks = [chunk for chunk in chunks if chunk.content and chunk.content.strip()]

            embedding_service = EmbeddingService()
            embedded_count = 0
            for start in range(0, len(non_empty_chunks), settings.embedding_batch_size):
                batch_chunks = non_empty_chunks[start : start + settings.embedding_batch_size]
                texts = [chunk.content for chunk in batch_chunks]
                embeddings = embedding_service.embed_texts(texts)
                for chunk, embedding in zip(batch_chunks, embeddings, strict=True):
                    chunk.embedding = embedding
                    embedded_count += 1
                db.commit()

            document.index_status = "indexed"
            document.indexed_at = datetime.now(UTC)
            document.index_error_message = None

            task = _get_latest_embedding_task(db, document.id)
            if task is not None:
                task.status = "finished"
                task.error_message = None

            db.commit()
            return {
                "document_id": str(document.id),
                "chunk_count": len(chunks),
                "embedded_count": embedded_count,
            }
        except Exception as exc:
            db.rollback()
            error_message = str(exc)
            _mark_failed(parsed_document_id, error_message)
            raise

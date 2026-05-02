from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.db.models.task import AsyncTask
from app.db.session import SessionLocal
from app.rag.chunker import chunk_text_blocks
from app.rag.indexer import insert_document_chunks
from app.rag.parser import parse_file
from app.workers.queue import get_document_queue
from app.workers.tasks_embedding import embed_document_chunks_task


settings = get_settings()


def _get_latest_parse_task(db: Session, document_id: UUID) -> AsyncTask | None:
    stmt = (
        select(AsyncTask)
        .where(
            AsyncTask.task_type == "parse_document",
            AsyncTask.target_id == document_id,
        )
        .order_by(AsyncTask.created_at.desc())
    )
    return db.execute(stmt).scalars().first()


def _mark_failed(document_id: UUID, message: str) -> None:
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        if document is not None:
            document.parse_status = "failed"
            document.error_message = message

        task = _get_latest_parse_task(db, document_id)
        if task is not None:
            task.status = "failed"
            task.error_message = message

        db.commit()


def parse_document_task(document_id: str) -> dict[str, str | int]:
    parsed_document_id = UUID(document_id)

    with SessionLocal() as db:
        try:
            document = db.get(Document, parsed_document_id)
            if document is None:
                raise ValueError(f"Document not found: {document_id}")

            task = _get_latest_parse_task(db, document.id)
            if task is not None:
                task.status = "running"
                task.error_message = None

            document.parse_status = "parsing"
            document.error_message = None
            db.commit()
            db.refresh(document)

            blocks = parse_file(document.file_path, document.file_type)
            chunks = chunk_text_blocks(
                blocks,
                chunk_size=settings.chunk_size,
                overlap=settings.chunk_overlap,
            )

            db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
            inserted_count = insert_document_chunks(db, document, chunks)

            document.parse_status = "parsed"
            document.chunk_count = inserted_count
            document.error_message = None
            document.index_status = "uploaded"
            document.indexed_at = None
            document.index_error_message = None

            task = _get_latest_parse_task(db, document.id)
            if task is not None:
                task.status = "finished"
                task.error_message = None

            embedding_task = AsyncTask(
                task_type="embed_document_chunks",
                status="queued",
                target_id=document.id,
            )
            db.add(embedding_task)
            db.commit()

            try:
                job = get_document_queue().enqueue(
                    embed_document_chunks_task,
                    str(document.id),
                    job_timeout="60m",
                    result_ttl=3600,
                    failure_ttl=86400,
                )
                embedding_task.rq_job_id = job.id
                db.commit()
            except Exception as exc:
                document.index_status = "failed"
                document.index_error_message = f"Failed to enqueue embedding job: {exc}"
                embedding_task.status = "failed"
                embedding_task.error_message = document.index_error_message
                db.commit()
                raise

            return {
                "document_id": str(document.id),
                "status": "parsed",
                "chunk_count": inserted_count,
                "embedding_task_id": str(embedding_task.id),
            }
        except Exception as exc:
            db.rollback()
            error_message = str(exc)
            _mark_failed(parsed_document_id, error_message)
            raise

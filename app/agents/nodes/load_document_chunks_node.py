from __future__ import annotations

import logging
from time import perf_counter
from uuid import UUID

from fastapi import status
from sqlalchemy import select

from app.agents.state import PaperSummaryState
from app.core.exceptions import AppError
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.db.models.project import PaperProject
from app.db.session import SessionLocal


logger = logging.getLogger(__name__)


def load_document_chunks_node(state: PaperSummaryState) -> PaperSummaryState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    project_id = _parse_uuid(state.get("project_id", ""), "project_id")
    document_id = _parse_uuid(state.get("document_id", ""), "document_id")

    try:
        with SessionLocal() as db:
            project = db.get(PaperProject, project_id)
            if project is None:
                raise AppError("Project not found", status.HTTP_404_NOT_FOUND)

            document = db.get(Document, document_id)
            if document is None:
                raise AppError("Document not found", status.HTTP_404_NOT_FOUND)
            if document.project_id != project_id:
                raise AppError("Document does not belong to this project", status.HTTP_409_CONFLICT)
            if document.parse_status != "parsed":
                raise AppError(
                    f"Document is not parsed yet, current parse_status={document.parse_status}",
                    status.HTTP_409_CONFLICT,
                )

            rows = list(
                db.execute(
                    select(DocumentChunk)
                    .where(DocumentChunk.document_id == document_id)
                    .order_by(DocumentChunk.chunk_index.asc())
                )
                .scalars()
                .all()
            )
            if not rows:
                raise AppError("Document has no chunks. Please re-parse this document.", status.HTTP_409_CONFLICT)

            chunks: list[dict] = []
            citations: list[dict] = []
            for citation_index, chunk in enumerate(rows, start=1):
                chunk_dict = {
                    "chunk_id": str(chunk.id),
                    "project_id": str(chunk.project_id),
                    "document_id": str(chunk.document_id),
                    "file_name": document.original_filename,
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                    "section_title": chunk.section_title or "",
                    "content": chunk.content,
                    "token_count": chunk.token_count,
                    "metadata": chunk.chunk_metadata or {},
                    "citation_index": citation_index,
                }
                chunks.append(chunk_dict)
                citations.append(
                    {
                        "index": citation_index,
                        "document_id": str(document.id),
                        "file_name": document.original_filename,
                        "page_number": chunk.page_number,
                        "section_title": chunk.section_title or "",
                        "chunk_index": chunk.chunk_index,
                    }
                )

            warning = None
            if document.index_status != "indexed":
                warning = f"Document index_status={document.index_status}; summary can continue without embeddings."

            elapsed_ms = int((perf_counter() - started_at) * 1000)
            trace.append(
                {
                    "tool_name": "load_document_chunks",
                    "input": {"project_id": str(project_id), "document_id": str(document_id)},
                    "output": {
                        "chunk_count": len(chunks),
                        "index_status": document.index_status,
                        "warning": warning,
                    },
                    "latency_ms": elapsed_ms,
                    "status": "success",
                    "error_message": None,
                }
            )

            logger.info(
                "loaded document chunks project_id=%s document_id=%s chunk_count=%s index_status=%s latency_ms=%s",
                project_id,
                document_id,
                len(chunks),
                document.index_status,
                elapsed_ms,
            )

            updated = dict(state)
            updated.update(
                {
                    "document_info": {
                        "id": str(document.id),
                        "project_id": str(document.project_id),
                        "file_name": document.original_filename,
                        "file_type": document.file_type,
                        "parse_status": document.parse_status,
                        "index_status": document.index_status,
                        "chunk_count": document.chunk_count,
                        "warning": warning,
                    },
                    "chunks": chunks,
                    "citations": citations,
                    "trace": trace,
                }
            )
            return updated
    except Exception as exc:
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        trace.append(
            {
                "tool_name": "load_document_chunks",
                "input": {"project_id": str(project_id), "document_id": str(document_id)},
                "output": None,
                "latency_ms": elapsed_ms,
                "status": "failed",
                "error_message": str(exc),
            }
        )
        state["trace"] = trace
        state["error_message"] = str(exc)
        raise


def _parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

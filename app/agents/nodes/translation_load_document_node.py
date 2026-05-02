from __future__ import annotations

from time import perf_counter
from uuid import UUID

from fastapi import status

from app.agents.state import TranslationState
from app.core.exceptions import AppError
from app.db.models.document import Document
from app.db.models.project import PaperProject
from app.db.session import SessionLocal
from app.translation.segment_builder import load_translation_segments


def translation_load_document_node(state: TranslationState) -> TranslationState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    project_id = UUID(str(state["project_id"]))
    document_id = UUID(str(state["document_id"]))

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
        try:
            segments = load_translation_segments(
                db=db,
                project_id=project_id,
                document_id=document_id,
                range_type=state.get("range_type", "full"),
                page_from=state.get("page_from"),
                page_to=state.get("page_to"),
                chunk_from=state.get("chunk_from"),
                chunk_to=state.get("chunk_to"),
            )
        except ValueError as exc:
            raise AppError(str(exc), status.HTTP_400_BAD_REQUEST) from exc
        document_info = {
            "id": str(document.id),
            "project_id": str(document.project_id),
            "original_filename": document.original_filename,
            "file_type": document.file_type,
            "chunk_count": document.chunk_count,
            "parse_status": document.parse_status,
        }

    trace.append(
        {
            "tool_name": "translation_load_document",
            "output": {"segment_count": len(segments), "document_id": str(document_id)},
            "latency_ms": int((perf_counter() - started_at) * 1000),
            "status": "success",
        }
    )
    updated = dict(state)
    updated.update({"document_info": document_info, "segments": segments, "trace": trace})
    return updated

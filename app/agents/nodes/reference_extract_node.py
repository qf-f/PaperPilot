from __future__ import annotations

from time import perf_counter
from uuid import UUID

from fastapi import status
from sqlalchemy import select

from app.agents.state import ReferenceState
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.db.models.project import PaperProject
from app.db.session import SessionLocal
from app.references.extractor import extract_reference_text


def reference_extract_node(state: ReferenceState) -> ReferenceState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    project_id = _parse_uuid(state.get("project_id", ""), "project_id")
    document_id_raw = state.get("document_id")

    if not document_id_raw:
        updated = dict(state)
        updated["reference_text"] = state.get("reference_text") or ""
        return updated

    document_id = _parse_uuid(document_id_raw, "document_id")
    with SessionLocal() as db:
        project = db.get(PaperProject, project_id)
        if project is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)
        document = db.get(Document, document_id)
        if document is None:
            raise AppError("Document not found", status.HTTP_404_NOT_FOUND)
        if document.project_id != project_id:
            raise AppError("Document does not belong to this project", status.HTTP_409_CONFLICT)
        chunks = [
            {
                "chunk_index": chunk.chunk_index,
                "section_title": chunk.section_title or "",
                "content": chunk.content,
            }
            for chunk in db.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index.asc())
            ).scalars()
        ]

    reference_text, reason = extract_reference_text(chunks, max_chars=get_settings().reference_extract_max_chars)
    if not reference_text:
        raise AppError(reason or "No reference text extracted", status.HTTP_404_NOT_FOUND)

    elapsed_ms = int((perf_counter() - started_at) * 1000)
    trace.append(
        {
            "tool_name": "reference_extract",
            "input": {"project_id": str(project_id), "document_id": str(document_id)},
            "output": {"chars": len(reference_text)},
            "latency_ms": elapsed_ms,
            "status": "success",
            "error_message": None,
        }
    )
    updated = dict(state)
    updated.update({"reference_text": reference_text, "trace": trace})
    return updated


def _parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

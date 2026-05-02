from __future__ import annotations

from time import perf_counter
from uuid import UUID

from fastapi import status
from sqlalchemy import select

from app.agents.state import ReviewState
from app.core.exceptions import AppError
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.db.models.generated_output import GeneratedOutput
from app.db.session import SessionLocal


MAX_REVIEW_CHARS = 30000


def review_load_target_node(state: ReviewState) -> ReviewState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    project_id = UUID(str(state["project_id"]))

    with SessionLocal() as db:
        if state.get("target_output_id"):
            output = db.get(GeneratedOutput, UUID(str(state["target_output_id"])))
            if output is None:
                raise AppError("Target generated output not found", status.HTTP_404_NOT_FOUND)
            if output.project_id != project_id:
                raise AppError("Target output does not belong to this project", status.HTTP_409_CONFLICT)
            content = output.content_markdown or ""
            if not content.strip():
                raise AppError("Target generated output has empty content", status.HTTP_409_CONFLICT)
            target = {
                "target_type": "generated_output",
                "target_id": str(output.id),
                "target_title": output.title or output.output_type,
                "target_content": content[:MAX_REVIEW_CHARS],
                "target_json": output.content_json or {},
                "target_output_type": output.output_type,
            }
        elif state.get("document_id"):
            document = db.get(Document, UUID(str(state["document_id"])))
            if document is None:
                raise AppError("Document not found", status.HTTP_404_NOT_FOUND)
            if document.project_id != project_id:
                raise AppError("Document does not belong to this project", status.HTTP_409_CONFLICT)
            chunks = list(
                db.execute(
                    select(DocumentChunk)
                    .where(DocumentChunk.document_id == document.id)
                    .order_by(DocumentChunk.chunk_index.asc())
                ).scalars().all()
            )
            content = "\n\n".join(chunk.content for chunk in chunks if chunk.content)
            if not content.strip():
                raise AppError("Document has no reviewable text chunks", status.HTTP_409_CONFLICT)
            target = {
                "target_type": "uploaded_document",
                "target_id": str(document.id),
                "target_title": document.original_filename,
                "target_content": content[:MAX_REVIEW_CHARS],
                "target_json": {},
                "target_output_type": None,
            }
        else:
            raise AppError("target_output_id or document_id is required", status.HTTP_400_BAD_REQUEST)

    trace.append(
        {
            "tool_name": "review_load_target",
            "input": {"target_output_id": state.get("target_output_id"), "document_id": state.get("document_id")},
            "output": {"target_type": target["target_type"], "chars": len(target["target_content"])},
            "latency_ms": int((perf_counter() - started_at) * 1000),
            "status": "success",
            "error_message": None,
        }
    )
    updated = dict(state)
    updated.update(target)
    updated["trace"] = trace
    return updated

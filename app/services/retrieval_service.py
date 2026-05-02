from __future__ import annotations

import logging
from time import perf_counter
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.db.models.project import PaperProject
from app.rag.retriever import RetrievedChunk
from app.services.embedding_service import EmbeddingService, EmbeddingServiceError


logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self, db: Session, embedding_service: EmbeddingService | None = None) -> None:
        self.db = db
        self.embedding_service = embedding_service or EmbeddingService()

    def retrieve(
        self,
        project_id: str,
        query: str,
        document_ids: list[str] | None = None,
        top_k: int = 6,
        similarity_threshold: float = 0.25,
    ) -> list[RetrievedChunk]:
        started_at = perf_counter()
        clean_query = query.strip()
        if not clean_query:
            raise AppError("Query cannot be empty", status.HTTP_400_BAD_REQUEST)

        project_uuid = self._parse_uuid(project_id, "project_id")
        project = self.db.get(PaperProject, project_uuid)
        if project is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)

        document_uuids = self._validate_documents(project_uuid, document_ids)
        self._ensure_index_ready(project_uuid, document_uuids, require_all=bool(document_uuids))

        try:
            query_embedding = self.embedding_service.embed_text(clean_query)
        except EmbeddingServiceError as exc:
            raise AppError(str(exc), status.HTTP_502_BAD_GATEWAY) from exc

        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        score_expr = (1 - distance).label("score")
        stmt = (
            select(DocumentChunk, Document.original_filename.label("file_name"), score_expr)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                DocumentChunk.project_id == project_uuid,
                Document.parse_status == "parsed",
                Document.index_status == "indexed",
                DocumentChunk.embedding.is_not(None),
                distance <= (1 - similarity_threshold),
            )
            .order_by(distance.asc())
            .limit(top_k)
        )

        if document_uuids:
            stmt = stmt.where(DocumentChunk.document_id.in_(document_uuids))

        try:
            rows = self.db.execute(stmt).all()
        except Exception as exc:
            raise AppError(f"pgvector retrieval failed: {exc}", status.HTTP_500_INTERNAL_SERVER_ERROR) from exc

        chunks = [
            RetrievedChunk(
                chunk_id=str(chunk.id),
                document_id=str(chunk.document_id),
                project_id=str(chunk.project_id),
                file_name=file_name,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                section_title=chunk.section_title or "",
                content=chunk.content,
                score=float(score or 0.0),
                metadata=chunk.chunk_metadata or {},
            )
            for chunk, file_name, score in rows
        ]

        elapsed_ms = int((perf_counter() - started_at) * 1000)
        logger.info(
            "retrieval finished project_id=%s document_ids=%s top_k=%s threshold=%s count=%s latency_ms=%s",
            project_id,
            document_ids,
            top_k,
            similarity_threshold,
            len(chunks),
            elapsed_ms,
        )
        return chunks

    def _validate_documents(self, project_id: UUID, document_ids: list[str] | None) -> list[UUID]:
        if not document_ids:
            return []

        document_uuids = [self._parse_uuid(document_id, "document_id") for document_id in document_ids]
        docs = list(
            self.db.execute(
                select(Document).where(
                    Document.project_id == project_id,
                    Document.id.in_(document_uuids),
                )
            )
            .scalars()
            .all()
        )
        found_ids = {doc.id for doc in docs}
        missing_ids = [str(doc_id) for doc_id in document_uuids if doc_id not in found_ids]
        if missing_ids:
            raise AppError(
                f"Document not found in current project: {', '.join(missing_ids)}",
                status.HTTP_404_NOT_FOUND,
            )
        return document_uuids

    def _ensure_index_ready(self, project_id: UUID, document_ids: list[UUID], require_all: bool) -> None:
        stmt = select(Document).where(Document.project_id == project_id)
        if document_ids:
            stmt = stmt.where(Document.id.in_(document_ids))

        docs = list(self.db.execute(stmt).scalars().all())
        if not docs:
            return

        indexed_docs = [doc for doc in docs if doc.parse_status == "parsed" and doc.index_status == "indexed"]
        if not require_all and indexed_docs:
            return

        not_parsed = [doc.original_filename for doc in docs if doc.parse_status != "parsed"]
        if not_parsed and require_all:
            raise AppError(
                f"Document is not parsed yet: {', '.join(not_parsed)}",
                status.HTTP_409_CONFLICT,
            )

        not_indexed = [doc.original_filename for doc in docs if doc.index_status != "indexed"]
        if not_indexed:
            raise AppError(
                f"Document is not indexed yet: {', '.join(not_indexed)}",
                status.HTTP_409_CONFLICT,
            )

    @staticmethod
    def _parse_uuid(value: str, field_name: str) -> UUID:
        try:
            return UUID(str(value))
        except ValueError as exc:
            raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

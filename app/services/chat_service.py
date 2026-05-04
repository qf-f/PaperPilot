from __future__ import annotations

import logging
from time import perf_counter
from uuid import UUID

from fastapi import status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.agents.graph import run_knowledge_qa_graph
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.models.agent_run import AgentRun
from app.db.models.chat import ChatMessage, ChatSession
from app.db.models.document import Document
from app.db.models.project import PaperProject
from app.db.models.tool_trace import ToolTrace
from app.schemas.chat_schema import ChatRequest, ChatResponse, CitationItem, RetrievedChunkPreview


logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def chat(self, request: ChatRequest) -> ChatResponse:
        started_at = perf_counter()
        project_id = self._parse_uuid(request.project_id, "project_id")
        user_id = self._parse_uuid(request.user_id, "user_id")
        top_k = request.top_k or self.settings.rag_top_k
        similarity_threshold = (
            request.similarity_threshold
            if request.similarity_threshold is not None
            else self.settings.rag_similarity_threshold
        )
        query = request.query.strip()
        if not query:
            raise AppError("Query cannot be empty", status.HTTP_400_BAD_REQUEST)

        project = self.db.get(PaperProject, project_id)
        if project is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)

        document_ids = self._resolve_document_ids(project_id, request)

        session = self._get_or_create_session(
            project_id=project_id,
            user_id=user_id,
            session_id=request.session_id,
            query=query,
        )
        agent_run = AgentRun(
            project_id=project_id,
            session_id=session.id,
            user_query=query,
            intent="knowledge_qa",
            status="running",
        )
        self.db.add(agent_run)
        self.db.commit()
        self.db.refresh(agent_run)

        logger.info(
            "chat start agent_run_id=%s project_id=%s document_ids=%s top_k=%s threshold=%s query=%s",
            agent_run.id,
            project_id,
            document_ids,
            top_k,
            similarity_threshold,
            query,
        )

        try:
            final_state = run_knowledge_qa_graph(
                {
                    "user_id": str(user_id),
                    "project_id": str(project_id),
                    "session_id": str(session.id),
                    "query": query,
                    "document_ids": document_ids,
                    "top_k": top_k,
                    "similarity_threshold": similarity_threshold,
                    "trace": [],
                }
            )

            citations = final_state.get("citations", [])
            retrieved_chunks = final_state.get("retrieved_chunks", [])
            answer = final_state.get("answer", "")
            retrieved_chunk_ids = [chunk["chunk_id"] for chunk in retrieved_chunks]

            self.db.add(
                ChatMessage(
                    session_id=session.id,
                    project_id=project_id,
                    role="user",
                    content=query,
                    citations=[],
                    retrieved_chunk_ids=[],
                )
            )
            self.db.add(
                ChatMessage(
                    session_id=session.id,
                    project_id=project_id,
                    role="assistant",
                    content=answer,
                    citations=citations,
                    retrieved_chunk_ids=retrieved_chunk_ids,
                )
            )
            self._save_tool_traces(agent_run.id, final_state.get("trace", []))

            agent_run.status = "success"
            agent_run.error_message = None
            self.db.commit()

            elapsed_ms = int((perf_counter() - started_at) * 1000)
            logger.info(
                "chat success agent_run_id=%s retrieved_count=%s latency_ms=%s",
                agent_run.id,
                len(retrieved_chunks),
                elapsed_ms,
            )

            return ChatResponse(
                session_id=session.id,
                agent_run_id=agent_run.id,
                answer=answer,
                citations=[CitationItem(**citation) for citation in citations],
                retrieved_chunks=[
                    RetrievedChunkPreview(
                        chunk_id=chunk["chunk_id"],
                        document_id=chunk["document_id"],
                        file_name=chunk["file_name"],
                        page_number=chunk.get("page_number"),
                        section_title=chunk.get("section_title") or "",
                        chunk_index=chunk["chunk_index"],
                        content_preview=(chunk.get("content") or "")[:200],
                        score=round(float(chunk.get("score", 0.0)), 4),
                    )
                    for chunk in retrieved_chunks
                ],
                uncertainty_flag=bool(final_state.get("uncertainty_flag", False)),
            )
        except AppError as exc:
            self.db.rollback()
            agent_run.status = "failed"
            agent_run.error_message = exc.message
            self.db.commit()
            logger.exception("chat failed agent_run_id=%s error=%s", agent_run.id, exc.message)
            raise
        except Exception as exc:
            self.db.rollback()
            agent_run.status = "failed"
            agent_run.error_message = str(exc)
            self.db.commit()
            logger.exception("chat failed agent_run_id=%s error=%s", agent_run.id, exc)
            raise AppError(f"Knowledge QA failed: {exc}", status.HTTP_500_INTERNAL_SERVER_ERROR) from exc

    def _resolve_document_ids(self, project_id: UUID, request: ChatRequest) -> list[str]:
        document_ids = list(request.document_ids or [])
        single_document_id = (request.document_id or "").strip()
        if single_document_id:
            document_ids.append(single_document_id)

        deduped_document_ids = list(
            dict.fromkeys(str(document_id).strip() for document_id in document_ids if str(document_id).strip())
        )
        if deduped_document_ids:
            return deduped_document_ids

        file_name = (request.file_name or "").strip()
        if not file_name:
            return []

        stmt = (
            select(Document)
            .where(
                Document.project_id == project_id,
                or_(Document.original_filename == file_name, Document.stored_filename == file_name),
            )
            .order_by(Document.created_at.asc())
        )
        document = self.db.execute(stmt).scalars().first()
        if document is None:
            raise AppError(f"Document not found for file_name: {file_name}", status.HTTP_404_NOT_FOUND)
        return [str(document.id)]

    def _get_or_create_session(
        self,
        project_id: UUID,
        user_id: UUID,
        session_id: str | None,
        query: str,
    ) -> ChatSession:
        if session_id:
            parsed_session_id = self._parse_uuid(session_id, "session_id")
            session = self.db.get(ChatSession, parsed_session_id)
            if session is None:
                raise AppError("Chat session not found", status.HTTP_404_NOT_FOUND)
            if session.project_id != project_id:
                raise AppError("Chat session does not belong to this project", status.HTTP_409_CONFLICT)
            return session

        title = query[:20]
        session = ChatSession(project_id=project_id, user_id=user_id, title=title)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def _save_tool_traces(self, agent_run_id: UUID, traces: list[dict]) -> None:
        for trace in traces:
            self.db.add(
                ToolTrace(
                    agent_run_id=agent_run_id,
                    tool_name=trace.get("tool_name", "unknown"),
                    input=trace.get("input"),
                    output=trace.get("output"),
                    latency_ms=trace.get("latency_ms"),
                    status=trace.get("status", "unknown"),
                    error_message=trace.get("error_message"),
                )
            )

    @staticmethod
    def _parse_uuid(value: str, field_name: str) -> UUID:
        try:
            return UUID(str(value))
        except ValueError as exc:
            raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

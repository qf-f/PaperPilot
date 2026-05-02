from __future__ import annotations

from time import perf_counter

from app.agents.state import PaperAgentState
from app.db.session import SessionLocal
from app.rag.citation_builder import build_citations
from app.rag.prompt_builder import build_rag_user_prompt
from app.services.retrieval_service import RetrievalService


def retrieve_node(state: PaperAgentState) -> PaperAgentState:
    started_at = perf_counter()
    trace = list(state.get("trace", []))
    query = state.get("query", "")
    project_id = state.get("project_id", "")
    document_ids = state.get("document_ids") or None
    top_k = int(state.get("top_k", 6))
    similarity_threshold = float(state.get("similarity_threshold", 0.25))

    try:
        with SessionLocal() as db:
            retrieval_service = RetrievalService(db)
            chunks = retrieval_service.retrieve(
                project_id=project_id,
                query=query,
                document_ids=document_ids,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )

        chunk_dicts = [chunk.to_dict() for chunk in chunks]
        citations = build_citations(chunk_dicts)
        context_prompt = build_rag_user_prompt(query=query, retrieved_chunks=chunk_dicts)
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        trace.append(
            {
                "tool_name": "retrieval",
                "input": {
                    "project_id": project_id,
                    "document_ids": document_ids,
                    "top_k": top_k,
                    "similarity_threshold": similarity_threshold,
                },
                "output": {"retrieved_count": len(chunk_dicts)},
                "latency_ms": elapsed_ms,
                "status": "success",
                "error_message": None,
            }
        )

        updated = dict(state)
        updated.update(
            {
                "retrieved_chunks": chunk_dicts,
                "citations": citations,
                "context_prompt": context_prompt,
                "uncertainty_flag": len(chunk_dicts) == 0,
                "trace": trace,
            }
        )
        return updated
    except Exception as exc:
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        trace.append(
            {
                "tool_name": "retrieval",
                "input": {
                    "project_id": project_id,
                    "document_ids": document_ids,
                    "top_k": top_k,
                    "similarity_threshold": similarity_threshold,
                },
                "output": None,
                "latency_ms": elapsed_ms,
                "status": "failed",
                "error_message": str(exc),
            }
        )
        state["trace"] = trace
        state["error_message"] = str(exc)
        raise

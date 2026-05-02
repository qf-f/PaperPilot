from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.models.agent_run import AgentRun
from app.db.models.tool_trace import ToolTrace
from app.schemas.run_schema import AgentRunDetail, ToolTraceItem


class RunService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_run(self, run_id: str) -> AgentRunDetail:
        run = self.db.get(AgentRun, self._parse_uuid(run_id, "run_id"))
        if run is None:
            raise AppError("Agent run not found", status.HTTP_404_NOT_FOUND)
        traces = list(
            self.db.execute(
                select(ToolTrace).where(ToolTrace.agent_run_id == run.id).order_by(ToolTrace.created_at.asc())
            )
            .scalars()
            .all()
        )
        return AgentRunDetail(
            run_id=str(run.id),
            project_id=str(run.project_id),
            session_id=str(run.session_id) if run.session_id else None,
            intent=run.intent,
            status=run.status,
            error_message=run.error_message,
            prompt_tokens=run.prompt_tokens,
            completion_tokens=run.completion_tokens,
            total_tokens=run.total_tokens,
            estimated_cost=run.estimated_cost,
            nodes=[ToolTraceItem.model_validate(trace) for trace in traces],
            total_latency_ms=sum(trace.latency_ms or 0 for trace in traces),
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    @staticmethod
    def _parse_uuid(value: str, field_name: str) -> UUID:
        try:
            return UUID(str(value))
        except ValueError as exc:
            raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

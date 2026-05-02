from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentRunAcceptedResponse(BaseModel):
    run_id: str
    status: str = "queued"
    message: str = "Agent run has been queued"


class ToolTraceItem(BaseModel):
    id: UUID
    node_name: str | None = None
    tool_name: str
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    latency_ms: int | None = None
    status: str
    error_message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentRunDetail(BaseModel):
    run_id: str
    project_id: str
    session_id: str | None = None
    intent: str
    status: str
    error_message: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    nodes: list[ToolTraceItem] = Field(default_factory=list)
    total_latency_ms: int = 0
    created_at: datetime
    updated_at: datetime

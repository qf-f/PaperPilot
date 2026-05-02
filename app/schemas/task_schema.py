from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TaskRead(BaseModel):
    id: UUID
    task_type: str
    rq_job_id: str | None = None
    status: str
    rq_status: str | None = None
    target_id: UUID | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

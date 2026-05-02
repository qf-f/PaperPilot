from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


ExportType = Literal["markdown", "word"]


class ExportRequest(BaseModel):
    export_type: ExportType


class ExportResponse(BaseModel):
    export_task_id: str
    output_id: str
    export_type: ExportType
    file_name: str
    file_path: str
    status: str


class ExportTaskRead(BaseModel):
    id: UUID
    project_id: UUID
    output_id: UUID
    export_type: str
    file_path: str | None = None
    file_name: str | None = None
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

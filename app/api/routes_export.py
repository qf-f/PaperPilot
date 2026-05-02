from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.export_schema import ExportRequest, ExportResponse, ExportTaskRead
from app.services.export_service import ExportService


router = APIRouter(tags=["export"])


@router.post("/api/outputs/{output_id}/export", response_model=ExportResponse)
def export_output(
    output_id: str,
    request: ExportRequest,
    db: Session = Depends(get_db),
) -> ExportResponse:
    return ExportService(db).export_output(output_id, request)


@router.get("/api/export/tasks/{export_task_id}", response_model=ExportTaskRead)
def get_export_task(export_task_id: str, db: Session = Depends(get_db)) -> ExportTaskRead:
    task = ExportService(db).get_export_task(export_task_id)
    return ExportTaskRead.model_validate(task)

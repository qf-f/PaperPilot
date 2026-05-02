from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.task_schema import TaskRead
from app.services import task_service


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: UUID, db: Session = Depends(get_db)) -> TaskRead:
    task, rq_status = task_service.get_task(db, task_id)
    task_read = TaskRead.model_validate(task)
    return task_read.model_copy(update={"rq_status": rq_status})

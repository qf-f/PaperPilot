from uuid import UUID

from fastapi import status
from rq.exceptions import NoSuchJobError
from rq.job import Job
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.models.task import AsyncTask
from app.workers.redis_conn import redis_conn


def get_task(db: Session, task_id: UUID) -> tuple[AsyncTask, str | None]:
    task = db.get(AsyncTask, task_id)
    if task is None:
        raise AppError("Task not found", status.HTTP_404_NOT_FOUND)

    rq_status = None
    if task.rq_job_id:
        try:
            job = Job.fetch(task.rq_job_id, connection=redis_conn)
            rq_status = job.get_status(refresh=True)
        except NoSuchJobError:
            rq_status = "missing"

    return task, rq_status

from pathlib import Path
from uuid import UUID

from fastapi import UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.models.document import Document
from app.db.models.project import PaperProject
from app.db.models.task import AsyncTask
from app.utils.file_utils import build_stored_filename, save_upload_file, validate_file_type
from app.workers.queue import get_document_queue
from app.workers.tasks_document import parse_document_task


settings = get_settings()


def list_documents(db: Session, project_id: UUID) -> list[Document]:
    project = db.get(PaperProject, project_id)
    if project is None:
        raise AppError("Project not found", status.HTTP_404_NOT_FOUND)

    stmt = (
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_document(db: Session, document_id: UUID) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise AppError("Document not found", status.HTTP_404_NOT_FOUND)
    return document


async def upload_document(
    db: Session,
    project_id: UUID,
    upload_file: UploadFile,
) -> tuple[Document, AsyncTask]:
    project = db.get(PaperProject, project_id)
    if project is None:
        raise AppError("Project not found", status.HTTP_404_NOT_FOUND)

    original_filename = upload_file.filename or "uploaded_file"
    try:
        file_type = validate_file_type(original_filename)
    except ValueError as exc:
        raise AppError(str(exc), status.HTTP_400_BAD_REQUEST) from exc

    stored_filename = build_stored_filename(original_filename)
    project_upload_dir = Path(settings.upload_dir) / str(project_id)
    file_path = project_upload_dir / stored_filename

    try:
        file_size = await save_upload_file(
            upload_file=upload_file,
            destination=file_path,
            max_size_mb=settings.max_upload_size_mb,
        )
    except ValueError as exc:
        raise AppError(str(exc), status.HTTP_413_REQUEST_ENTITY_TOO_LARGE) from exc

    document = Document(
        project_id=project.id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=str(file_path),
        file_type=file_type,
        file_size=file_size,
        parse_status="uploaded",
        chunk_count=0,
    )
    db.add(document)
    db.flush()

    async_task = AsyncTask(
        task_type="parse_document",
        status="queued",
        target_id=document.id,
    )
    db.add(async_task)
    db.commit()
    db.refresh(document)
    db.refresh(async_task)

    try:
        job = get_document_queue().enqueue(
            parse_document_task,
            str(document.id),
            job_timeout="30m",
            result_ttl=3600,
            failure_ttl=86400,
        )
        async_task.rq_job_id = job.id
        db.commit()
        db.refresh(async_task)
    except Exception as exc:
        async_task.status = "failed"
        async_task.error_message = f"Failed to enqueue parse job: {exc}"
        document.parse_status = "failed"
        document.error_message = async_task.error_message
        db.commit()
        raise AppError(async_task.error_message, status.HTTP_503_SERVICE_UNAVAILABLE) from exc

    return document, async_task

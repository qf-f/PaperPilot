from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.document_schema import DocumentRead, DocumentUploadResponse
from app.services import document_service


router = APIRouter(tags=["documents"])


@router.post(
    "/api/projects/{project_id}/documents/upload",
    response_model=DocumentUploadResponse,
)
async def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    document, async_task = await document_service.upload_document(db, project_id, file)
    return DocumentUploadResponse(
        document_id=document.id,
        task_id=async_task.id,
        rq_job_id=async_task.rq_job_id,
        parse_status=document.parse_status,
    )


@router.get(
    "/api/projects/{project_id}/documents",
    response_model=list[DocumentRead],
)
def list_documents(project_id: UUID, db: Session = Depends(get_db)) -> list[DocumentRead]:
    documents = document_service.list_documents(db, project_id)
    return [DocumentRead.model_validate(document) for document in documents]


@router.get("/api/documents/{document_id}", response_model=DocumentRead)
def get_document(document_id: UUID, db: Session = Depends(get_db)) -> DocumentRead:
    document = document_service.get_document(db, document_id)
    return DocumentRead.model_validate(document)

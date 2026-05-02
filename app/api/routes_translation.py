from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.run_schema import AgentRunAcceptedResponse
from app.schemas.translation_schema import (
    TerminologyItem,
    TerminologyUpsertRequest,
    TerminologyUpsertResponse,
    TranslationDetail,
    TranslationItem,
    TranslationRequest,
    TranslationResponse,
)
from app.services.terminology_service import TerminologyService
from app.services.translation_service import TranslationService


router = APIRouter(tags=["translation"])


@router.post("/api/translation/document", response_model=TranslationResponse | AgentRunAcceptedResponse)
def translate_document(request: TranslationRequest, db: Session = Depends(get_db)) -> TranslationResponse | AgentRunAcceptedResponse:
    return TranslationService(db).translate_document(request)


@router.get("/api/projects/{project_id}/translations", response_model=list[TranslationItem])
def list_project_translations(project_id: str, db: Session = Depends(get_db)) -> list[TranslationItem]:
    outputs = TranslationService(db).list_translations(project_id)
    return [TranslationItem.model_validate(output) for output in outputs]


@router.get("/api/translations/{output_id}", response_model=TranslationDetail)
def get_translation(output_id: str, db: Session = Depends(get_db)) -> TranslationDetail:
    output = TranslationService(db).get_translation(output_id)
    return TranslationDetail.model_validate(output)


@router.get("/api/projects/{project_id}/terminologies", response_model=list[TerminologyItem])
def list_project_terminologies(project_id: str, db: Session = Depends(get_db)) -> list[TerminologyItem]:
    terms = TerminologyService(db).list_terms(project_id)
    return [TerminologyItem.model_validate(term) for term in terms]


@router.post("/api/projects/{project_id}/terminologies", response_model=TerminologyUpsertResponse)
def upsert_project_terminology(
    project_id: str,
    request: TerminologyUpsertRequest,
    db: Session = Depends(get_db),
) -> TerminologyUpsertResponse:
    saved = TerminologyService(db).upsert_terms(
        project_id=project_id,
        document_id=None,
        terms=[
            {
                "source_term": request.source_term,
                "target_term": request.target_term,
                "category": request.category,
                "explanation": request.explanation or "",
                "confidence_score": request.confidence_score,
                "source": "manual",
            }
        ],
        overwrite_target=True,
    )
    return TerminologyUpsertResponse(terminology=TerminologyItem.model_validate(saved[0]))

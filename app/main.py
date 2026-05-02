from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes_chat import router as chat_router
from app.api.routes_document import router as document_router
from app.api.routes_export import router as export_router
from app.api.routes_literature import router as literature_router
from app.api.routes_paper import router as paper_router
from app.api.routes_planning import router as planning_router
from app.api.routes_project import router as project_router
from app.api.routes_reference import router as reference_router
from app.api.routes_review import router as review_router
from app.api.routes_run import router as run_router
from app.api.routes_task import router as task_router
from app.api.routes_translation import router as translation_router
from app.api.routes_writing import router as writing_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.db.base import import_all_models


configure_logging()
import_all_models()
settings = get_settings()

app = FastAPI(title=settings.app_name)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


app.include_router(project_router)
app.include_router(document_router)
app.include_router(task_router)
app.include_router(chat_router)
app.include_router(paper_router)
app.include_router(export_router)
app.include_router(literature_router)
app.include_router(reference_router)
app.include_router(planning_router)
app.include_router(writing_router)
app.include_router(review_router)
app.include_router(translation_router)
app.include_router(run_router)

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.models.project import PaperProject
from app.schemas.project_schema import ProjectCreate


def create_project(db: Session, payload: ProjectCreate) -> PaperProject:
    project = PaperProject(
        user_id=payload.user_id,
        title=payload.title,
        research_direction=payload.research_direction,
        keywords=payload.keywords,
        description=payload.description,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def list_projects(db: Session) -> list[PaperProject]:
    stmt = select(PaperProject).order_by(PaperProject.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def get_project(db: Session, project_id: UUID) -> PaperProject:
    project = db.get(PaperProject, project_id)
    if project is None:
        raise AppError("Project not found", status.HTTP_404_NOT_FOUND)
    return project

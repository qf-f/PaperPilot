from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.models.generated_output import GeneratedOutput
from app.db.models.project import PaperProject


def list_project_outputs(
    db: Session,
    project_id: str,
    output_type: str | None = None,
    document_id: str | None = None,
) -> list[GeneratedOutput]:
    project_uuid = _parse_uuid(project_id, "project_id")
    if db.get(PaperProject, project_uuid) is None:
        raise AppError("Project not found", status.HTTP_404_NOT_FOUND)

    stmt = select(GeneratedOutput).where(GeneratedOutput.project_id == project_uuid)
    if output_type:
        stmt = stmt.where(GeneratedOutput.output_type == output_type)
    if document_id:
        stmt = stmt.where(GeneratedOutput.document_id == _parse_uuid(document_id, "document_id"))

    stmt = stmt.order_by(GeneratedOutput.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def list_project_outputs_paginated(
    db: Session,
    project_id: str,
    output_type: str | None = None,
    document_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_order: str = "desc",
) -> tuple[list[GeneratedOutput], int]:
    project_uuid = _parse_uuid(project_id, "project_id")
    if db.get(PaperProject, project_uuid) is None:
        raise AppError("Project not found", status.HTTP_404_NOT_FOUND)

    filters = [GeneratedOutput.project_id == project_uuid]
    if output_type:
        filters.append(GeneratedOutput.output_type == output_type)
    if document_id:
        filters.append(GeneratedOutput.document_id == _parse_uuid(document_id, "document_id"))

    total = db.execute(select(func.count()).select_from(GeneratedOutput).where(*filters)).scalar_one()
    order_col = GeneratedOutput.created_at.desc() if sort_order != "asc" else GeneratedOutput.created_at.asc()
    stmt = (
        select(GeneratedOutput)
        .where(*filters)
        .order_by(order_col)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.execute(stmt).scalars().all()), int(total)


def get_output(db: Session, output_id: str) -> GeneratedOutput:
    output = db.get(GeneratedOutput, _parse_uuid(output_id, "output_id"))
    if output is None:
        raise AppError("Generated output not found", status.HTTP_404_NOT_FOUND)
    return output


def _parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

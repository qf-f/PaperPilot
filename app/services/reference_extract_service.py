from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.reference_graph import run_reference_graph


class ReferenceExtractService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def extract(self, project_id: str, document_id: str, user_id: str = "demo-user") -> dict:
        return run_reference_graph(
            {
                "user_id": user_id,
                "project_id": project_id,
                "document_id": document_id,
                "trace": [],
            }
        )

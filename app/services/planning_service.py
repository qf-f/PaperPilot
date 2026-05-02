from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.planning_graph import build_planning_graph
from app.agents.runner import AgentRunner
from app.core.exceptions import AppError
from app.db.models.generated_output import GeneratedOutput
from app.db.models.project import PaperProject
from app.schemas.planning_schema import PlanningRequest, PlanningResponse
from app.schemas.run_schema import AgentRunAcceptedResponse
from app.workers.queue import get_document_queue


class PlanningService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def generate_plan(self, request: PlanningRequest) -> PlanningResponse | AgentRunAcceptedResponse:
        project_id = self._parse_uuid(request.project_id, "project_id")
        project = self.db.get(PaperProject, project_id)
        if project is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)

        topic = (request.topic or project.title or "").strip()
        if not topic:
            raise AppError("Topic is empty and project title is empty", status.HTTP_400_BAD_REQUEST)
        if request.mode == "async":
            run = AgentRunner(self.db).create_run(str(project_id), "planning", topic, status_value="queued")
            payload = request.model_dump()
            payload.update({"mode": "sync", "run_id": str(run.id)})
            from app.workers.tasks_planning import generate_planning_task

            get_document_queue().enqueue(generate_planning_task, payload, job_timeout="30m")
            return AgentRunAcceptedResponse(run_id=str(run.id))

        final_state, _ = AgentRunner(self.db).run_sync(
            graph=build_planning_graph(),
            project_id=str(project_id),
            intent="planning",
            user_query=topic,
            run_id=request.run_id,
            input_state=
            {
                "user_id": request.user_id,
                "project_id": str(project_id),
                "topic": topic,
                "paper_type": request.paper_type,
                "research_direction": request.research_direction or project.research_direction,
                "requirements": request.requirements,
                "trace": [],
            },
        )
        output_id = final_state.get("output_id")
        output = self.db.get(GeneratedOutput, self._parse_uuid(output_id, "output_id")) if output_id else None
        if output is None:
            raise AppError("Planning output was not saved", status.HTTP_500_INTERNAL_SERVER_ERROR)

        return PlanningResponse(
            output_id=str(output.id),
            topic=topic,
            paper_type=request.paper_type,
            final_markdown=output.content_markdown or "",
            final_json=output.content_json or {},
            created_at=output.created_at,
        )

    def list_plans(self, project_id: str) -> list[GeneratedOutput]:
        project_uuid = self._parse_uuid(project_id, "project_id")
        if self.db.get(PaperProject, project_uuid) is None:
            raise AppError("Project not found", status.HTTP_404_NOT_FOUND)
        return list(
            self.db.execute(
                select(GeneratedOutput)
                .where(GeneratedOutput.project_id == project_uuid, GeneratedOutput.output_type == "topic_plan")
                .order_by(GeneratedOutput.created_at.desc())
            )
            .scalars()
            .all()
        )

    def get_plan(self, output_id: str) -> GeneratedOutput:
        output = self.db.get(GeneratedOutput, self._parse_uuid(output_id, "output_id"))
        if output is None or output.output_type != "topic_plan":
            raise AppError("Plan not found", status.HTTP_404_NOT_FOUND)
        return output

    @staticmethod
    def _parse_uuid(value: str | None, field_name: str) -> UUID:
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise AppError(f"Invalid {field_name}: {value}", status.HTTP_400_BAD_REQUEST) from exc

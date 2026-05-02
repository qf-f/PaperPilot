from __future__ import annotations

from typing import Any

from app.review.structure_checker import check_structure


class ConsistencyCheckService:
    def check_topic_plan(self, plan_json: dict[str, Any], plan_markdown: str = "") -> list[dict]:
        issues = check_structure(
            target_type="generated_output",
            target_output_type="topic_plan",
            target_content=plan_markdown,
            target_json=plan_json or {},
            project_context={},
        )
        return [issue.model_dump() for issue in issues]

    def check_generated_output(
        self,
        output_type: str,
        content_markdown: str,
        content_json: dict[str, Any] | None = None,
        project_context: dict[str, Any] | None = None,
    ) -> list[dict]:
        issues = check_structure(
            target_type="generated_output",
            target_output_type=output_type,
            target_content=content_markdown or "",
            target_json=content_json or {},
            project_context=project_context or {},
        )
        return [issue.model_dump() for issue in issues]

from __future__ import annotations

from app.agents.state import PaperSummaryState


def summary_response_node(state: PaperSummaryState) -> PaperSummaryState:
    updated = dict(state)
    updated.setdefault("final_summary_markdown", "")
    updated.setdefault("final_summary_json", {})
    updated.setdefault("citations", [])
    updated.setdefault("section_summaries", [])
    updated.setdefault("section_groups", [])
    updated.setdefault("trace", [])
    return updated

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.runner import trace_node

from app.agents.nodes.citation_check_node import citation_check_node
from app.agents.nodes.experiment_support_check_node import experiment_support_check_node
from app.agents.nodes.review_context_node import review_context_node
from app.agents.nodes.review_load_target_node import review_load_target_node
from app.agents.nodes.review_response_node import review_response_node
from app.agents.nodes.review_save_node import review_save_node
from app.agents.nodes.revision_suggestion_node import revision_suggestion_node
from app.agents.nodes.structure_check_node import structure_check_node
from app.agents.nodes.writing_quality_check_node import writing_quality_check_node
from app.agents.state import ReviewState


@lru_cache
def build_review_graph():
    graph = StateGraph(ReviewState)
    graph.add_node("review_load_target", trace_node("review_load_target", review_load_target_node))
    graph.add_node("review_context", trace_node("review_context", review_context_node))
    graph.add_node("structure_check", trace_node("structure_check", structure_check_node))
    graph.add_node("citation_check", trace_node("citation_check", citation_check_node))
    graph.add_node("experiment_support_check", trace_node("experiment_support_check", experiment_support_check_node))
    graph.add_node("writing_quality_check", trace_node("writing_quality_check", writing_quality_check_node))
    graph.add_node("revision_suggestion", trace_node("revision_suggestion", revision_suggestion_node))
    graph.add_node("review_save", trace_node("review_save", review_save_node))
    graph.add_node("review_response", trace_node("review_response", review_response_node))

    graph.add_edge(START, "review_load_target")
    graph.add_edge("review_load_target", "review_context")
    graph.add_edge("review_context", "structure_check")
    graph.add_edge("structure_check", "citation_check")
    graph.add_edge("citation_check", "experiment_support_check")
    graph.add_edge("experiment_support_check", "writing_quality_check")
    graph.add_edge("writing_quality_check", "revision_suggestion")
    graph.add_edge("revision_suggestion", "review_save")
    graph.add_edge("review_save", "review_response")
    graph.add_edge("review_response", END)
    return graph.compile()


def run_review_graph(input_state: ReviewState) -> ReviewState:
    return build_review_graph().invoke(input_state)

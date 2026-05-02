from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.runner import trace_node

from app.agents.nodes.reference_dedup_node import reference_dedup_node
from app.agents.nodes.reference_extract_node import reference_extract_node
from app.agents.nodes.reference_parse_node import reference_parse_node
from app.agents.nodes.reference_recommend_node import reference_recommend_node
from app.agents.nodes.reference_response_node import reference_response_node
from app.agents.nodes.reference_save_node import reference_save_node
from app.agents.state import ReferenceState


@lru_cache
def build_reference_graph():
    graph = StateGraph(ReferenceState)
    graph.add_node("reference_extract", trace_node("reference_extract", reference_extract_node))
    graph.add_node("reference_parse", trace_node("reference_parse", reference_parse_node))
    graph.add_node("reference_dedup", trace_node("reference_dedup", reference_dedup_node))
    graph.add_node("reference_save", trace_node("reference_save", reference_save_node))
    graph.add_node("reference_recommend", trace_node("reference_recommend", reference_recommend_node))
    graph.add_node("reference_response", trace_node("reference_response", reference_response_node))

    graph.add_edge(START, "reference_extract")
    graph.add_edge("reference_extract", "reference_parse")
    graph.add_edge("reference_parse", "reference_dedup")
    graph.add_edge("reference_dedup", "reference_save")
    graph.add_edge("reference_save", "reference_recommend")
    graph.add_edge("reference_recommend", "reference_response")
    graph.add_edge("reference_response", END)
    return graph.compile()


def run_reference_graph(input_state: ReferenceState) -> ReferenceState:
    return build_reference_graph().invoke(input_state)

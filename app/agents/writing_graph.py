from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.runner import trace_node

from app.agents.nodes.citation_insert_node import citation_insert_node
from app.agents.nodes.section_draft_node import section_draft_node
from app.agents.nodes.writing_context_node import writing_context_node
from app.agents.nodes.writing_response_node import writing_response_node
from app.agents.nodes.writing_save_node import writing_save_node
from app.agents.state import WritingState


@lru_cache
def build_writing_graph():
    graph = StateGraph(WritingState)
    graph.add_node("writing_context", trace_node("writing_context", writing_context_node))
    graph.add_node("section_draft", trace_node("section_draft", section_draft_node))
    graph.add_node("citation_insert", trace_node("citation_insert", citation_insert_node))
    graph.add_node("writing_save", trace_node("writing_save", writing_save_node))
    graph.add_node("writing_response", trace_node("writing_response", writing_response_node))

    graph.add_edge(START, "writing_context")
    graph.add_edge("writing_context", "section_draft")
    graph.add_edge("section_draft", "citation_insert")
    graph.add_edge("citation_insert", "writing_save")
    graph.add_edge("writing_save", "writing_response")
    graph.add_edge("writing_response", END)
    return graph.compile()


def run_writing_graph(input_state: WritingState) -> WritingState:
    return build_writing_graph().invoke(input_state)

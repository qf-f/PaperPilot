from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.runner import trace_node

from app.agents.nodes.load_document_chunks_node import load_document_chunks_node
from app.agents.nodes.paper_summary_node import paper_summary_node
from app.agents.nodes.save_summary_node import save_summary_node
from app.agents.nodes.section_summary_node import section_summary_node
from app.agents.nodes.summary_response_node import summary_response_node
from app.agents.state import PaperSummaryState


@lru_cache
def build_paper_summary_graph():
    graph = StateGraph(PaperSummaryState)
    graph.add_node("load_document_chunks", trace_node("load_document_chunks", load_document_chunks_node))
    graph.add_node("section_summary", trace_node("section_summary", section_summary_node))
    graph.add_node("paper_summary", trace_node("paper_summary", paper_summary_node))
    graph.add_node("save_summary", trace_node("save_summary", save_summary_node))
    graph.add_node("summary_response", trace_node("summary_response", summary_response_node))

    graph.add_edge(START, "load_document_chunks")
    graph.add_edge("load_document_chunks", "section_summary")
    graph.add_edge("section_summary", "paper_summary")
    graph.add_edge("paper_summary", "save_summary")
    graph.add_edge("save_summary", "summary_response")
    graph.add_edge("summary_response", END)
    return graph.compile()


def run_paper_summary_graph(input_state: PaperSummaryState) -> PaperSummaryState:
    graph = build_paper_summary_graph()
    return graph.invoke(input_state)

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.runner import trace_node

from app.agents.nodes.build_search_query_node import build_search_query_node
from app.agents.nodes.literature_dedup_node import literature_dedup_node
from app.agents.nodes.literature_rank_node import literature_rank_node
from app.agents.nodes.literature_response_node import literature_response_node
from app.agents.nodes.literature_save_node import literature_save_node
from app.agents.nodes.web_literature_search_node import web_literature_search_node
from app.agents.state import LiteratureSearchState


@lru_cache
def build_literature_search_graph():
    graph = StateGraph(LiteratureSearchState)
    graph.add_node("build_search_query", trace_node("build_search_query", build_search_query_node))
    graph.add_node("web_literature_search", trace_node("web_literature_search", web_literature_search_node))
    graph.add_node("literature_dedup", trace_node("literature_dedup", literature_dedup_node))
    graph.add_node("literature_rank", trace_node("literature_rank", literature_rank_node))
    graph.add_node("literature_save", trace_node("literature_save", literature_save_node))
    graph.add_node("literature_response", trace_node("literature_response", literature_response_node))

    graph.add_edge(START, "build_search_query")
    graph.add_edge("build_search_query", "web_literature_search")
    graph.add_edge("web_literature_search", "literature_dedup")
    graph.add_edge("literature_dedup", "literature_rank")
    graph.add_edge("literature_rank", "literature_save")
    graph.add_edge("literature_save", "literature_response")
    graph.add_edge("literature_response", END)
    return graph.compile()


def run_literature_search_graph(input_state: LiteratureSearchState) -> LiteratureSearchState:
    return build_literature_search_graph().invoke(input_state)

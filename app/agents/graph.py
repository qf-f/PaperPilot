from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.runner import trace_node

from app.agents.nodes.qa_node import qa_node
from app.agents.nodes.response_node import response_node
from app.agents.nodes.retrieve_node import retrieve_node
from app.agents.state import PaperAgentState


@lru_cache
def build_knowledge_qa_graph():
    graph = StateGraph(PaperAgentState)
    graph.add_node("retrieve", trace_node("retrieve", retrieve_node))
    graph.add_node("qa", trace_node("qa", qa_node))
    graph.add_node("response", trace_node("response", response_node))

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "qa")
    graph.add_edge("qa", "response")
    graph.add_edge("response", END)
    return graph.compile()


def run_knowledge_qa_graph(input_state: PaperAgentState) -> PaperAgentState:
    graph = build_knowledge_qa_graph()
    result = graph.invoke(input_state)
    return result

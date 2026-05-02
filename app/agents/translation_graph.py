from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.runner import trace_node

from app.agents.nodes.terminology_consistency_node import terminology_consistency_node
from app.agents.nodes.terminology_extract_node import terminology_extract_node
from app.agents.nodes.translation_load_document_node import translation_load_document_node
from app.agents.nodes.translation_merge_node import translation_merge_node
from app.agents.nodes.translation_response_node import translation_response_node
from app.agents.nodes.translation_save_node import translation_save_node
from app.agents.nodes.translation_segment_node import translation_segment_node
from app.agents.state import TranslationState


@lru_cache
def build_translation_graph():
    graph = StateGraph(TranslationState)
    graph.add_node("translation_load_document", trace_node("translation_load_document", translation_load_document_node))
    graph.add_node("terminology_extract", trace_node("terminology_extract", terminology_extract_node))
    graph.add_node("translation_segment", trace_node("translation_segment", translation_segment_node))
    graph.add_node("terminology_consistency", trace_node("terminology_consistency", terminology_consistency_node))
    graph.add_node("translation_merge", trace_node("translation_merge", translation_merge_node))
    graph.add_node("translation_save", trace_node("translation_save", translation_save_node))
    graph.add_node("translation_response", trace_node("translation_response", translation_response_node))

    graph.add_edge(START, "translation_load_document")
    graph.add_edge("translation_load_document", "terminology_extract")
    graph.add_edge("terminology_extract", "translation_segment")
    graph.add_edge("translation_segment", "terminology_consistency")
    graph.add_edge("terminology_consistency", "translation_merge")
    graph.add_edge("translation_merge", "translation_save")
    graph.add_edge("translation_save", "translation_response")
    graph.add_edge("translation_response", END)
    return graph.compile()


def run_translation_graph(input_state: TranslationState) -> TranslationState:
    return build_translation_graph().invoke(input_state)

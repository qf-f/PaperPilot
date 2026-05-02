from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.runner import trace_node

from app.agents.nodes.experiment_design_node import experiment_design_node
from app.agents.nodes.innovation_design_node import innovation_design_node
from app.agents.nodes.load_project_context_node import load_project_context_node
from app.agents.nodes.outline_generation_node import outline_generation_node
from app.agents.nodes.planning_response_node import planning_response_node
from app.agents.nodes.planning_save_node import planning_save_node
from app.agents.nodes.research_problem_node import research_problem_node
from app.agents.nodes.topic_analysis_node import topic_analysis_node
from app.agents.state import PlanningState


@lru_cache
def build_planning_graph():
    graph = StateGraph(PlanningState)
    graph.add_node("load_project_context", trace_node("load_project_context", load_project_context_node))
    graph.add_node("topic_analysis", trace_node("topic_analysis", topic_analysis_node))
    graph.add_node("research_problem", trace_node("research_problem", research_problem_node))
    graph.add_node("innovation_design", trace_node("innovation_design", innovation_design_node))
    graph.add_node("experiment_design", trace_node("experiment_design", experiment_design_node))
    graph.add_node("outline_generation", trace_node("outline_generation", outline_generation_node))
    graph.add_node("planning_save", trace_node("planning_save", planning_save_node))
    graph.add_node("planning_response", trace_node("planning_response", planning_response_node))

    graph.add_edge(START, "load_project_context")
    graph.add_edge("load_project_context", "topic_analysis")
    graph.add_edge("topic_analysis", "research_problem")
    graph.add_edge("research_problem", "innovation_design")
    graph.add_edge("innovation_design", "experiment_design")
    graph.add_edge("experiment_design", "outline_generation")
    graph.add_edge("outline_generation", "planning_save")
    graph.add_edge("planning_save", "planning_response")
    graph.add_edge("planning_response", END)
    return graph.compile()


def run_planning_graph(input_state: PlanningState) -> PlanningState:
    return build_planning_graph().invoke(input_state)

from typing import Any, TypedDict


class PaperAgentState(TypedDict, total=False):
    user_id: str
    project_id: str
    session_id: str
    query: str
    document_ids: list[str]
    top_k: int
    similarity_threshold: float

    retrieved_chunks: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    context_prompt: str

    answer: str
    uncertainty_flag: bool
    error_message: str | None
    trace: list[dict[str, Any]]


class PaperSummaryState(TypedDict, total=False):
    user_id: str
    project_id: str
    document_id: str
    session_id: str | None
    summary_type: str
    project_topic: str | None

    document_info: dict[str, Any]
    chunks: list[dict[str, Any]]
    section_groups: list[dict[str, Any]]
    section_summaries: list[dict[str, Any]]

    final_summary_markdown: str
    final_summary_json: dict[str, Any]
    citations: list[dict[str, Any]]

    output_id: str | None
    error_message: str | None
    trace: list[dict[str, Any]]


class LiteratureSearchState(TypedDict, total=False):
    user_id: str
    project_id: str
    query: str | None
    search_mode: str
    max_results: int
    recent_years: int

    project_info: dict[str, Any]
    generated_queries: list[str]
    raw_results: list[dict[str, Any]]
    normalized_results: list[dict[str, Any]]
    deduped_results: list[dict[str, Any]]
    ranked_results: list[dict[str, Any]]
    saved_literatures: list[dict[str, Any]]

    review_material_markdown: str | None
    output_id: str | None

    error_message: str | None
    trace: list[dict[str, Any]]


class ReferenceState(TypedDict, total=False):
    user_id: str
    project_id: str
    document_id: str | None

    reference_text: str | None
    parsed_references: list[dict[str, Any]]
    deduped_references: list[dict[str, Any]]
    saved_references: list[dict[str, Any]]
    recommended_references: list[dict[str, Any]]

    error_message: str | None
    trace: list[dict[str, Any]]


class PlanningState(TypedDict, total=False):
    user_id: str
    project_id: str
    topic: str
    paper_type: str
    research_direction: str | None
    requirements: str | None

    project_context: dict[str, Any]

    topic_analysis: dict[str, Any]
    research_questions: list[dict[str, Any]]
    research_objectives: list[str]
    research_contents: list[dict[str, Any]]
    innovations: list[dict[str, Any]]
    technical_route: dict[str, Any]
    experiment_plan: dict[str, Any]
    outline: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    next_tasks: list[dict[str, Any]]

    final_markdown: str
    final_json: dict[str, Any]

    output_id: str | None
    error_message: str | None
    trace: list[dict[str, Any]]


class WritingState(TypedDict, total=False):
    user_id: str
    project_id: str
    topic: str | None
    section_type: str
    section_title: str
    plan_output_id: str | None
    requirements: str | None

    project_context: dict[str, Any]
    selected_plan: dict[str, Any] | None
    writing_context: dict[str, Any]

    section_markdown: str
    section_json: dict[str, Any]
    citations: list[dict[str, Any]]
    warnings: list[str]

    output_id: str | None
    error_message: str | None
    trace: list[dict[str, Any]]


class ReviewState(TypedDict, total=False):
    user_id: str
    project_id: str
    target_output_id: str | None
    document_id: str | None
    review_type: str
    requirements: str | None

    target_type: str
    target_id: str
    target_title: str
    target_content: str
    target_json: dict[str, Any]
    target_output_type: str | None

    project_context: dict[str, Any]
    existing_citations: list[dict[str, Any]]

    structure_issues: list[dict[str, Any]]
    citation_issues: list[dict[str, Any]]
    experiment_issues: list[dict[str, Any]]
    writing_issues: list[dict[str, Any]]
    revision_suggestions: list[dict[str, Any]]

    strengths: list[str]
    risks: list[str]
    next_actions: list[str]

    score: int
    review_markdown: str
    review_json: dict[str, Any]

    output_id: str | None
    error_message: str | None
    trace: list[dict[str, Any]]


class TranslationState(TypedDict, total=False):
    user_id: str
    project_id: str
    document_id: str

    translation_mode: str
    output_style: str
    range_type: str
    page_from: int | None
    page_to: int | None
    chunk_from: int | None
    chunk_to: int | None
    requirements: str | None

    document_info: dict[str, Any]
    segments: list[dict[str, Any]]
    existing_terms: list[dict[str, Any]]
    extracted_terms: list[dict[str, Any]]
    term_map: dict[str, str]

    translated_segments: list[dict[str, Any]]
    consistency_warnings: list[str]

    translated_markdown: str
    content_json: dict[str, Any]

    output_id: str | None
    error_message: str | None
    trace: list[dict[str, Any]]

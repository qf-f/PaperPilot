from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="PaperPilot", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/paper_pilot",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    upload_dir: Path = Field(default=Path("storage/uploads"), alias="UPLOAD_DIR")
    parsed_dir: Path = Field(default=Path("storage/parsed"), alias="PARSED_DIR")
    export_dir: Path = Field(default=Path("storage/exports"), alias="EXPORT_DIR")
    summary_dir: Path = Field(default=Path("storage/summaries"), alias="SUMMARY_DIR")

    max_upload_size_mb: int = Field(default=50, alias="MAX_UPLOAD_SIZE_MB")
    chunk_size: int = Field(default=500, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=80, alias="CHUNK_OVERLAP")
    chunk_strategy: str = Field(default="fixed", alias="CHUNK_STRATEGY")

    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    chat_model: str = Field(default="gpt-4o-mini", alias="CHAT_MODEL")
    chat_temperature: float = Field(default=0.2, alias="CHAT_TEMPERATURE")
    chat_max_tokens: int = Field(default=1500, alias="CHAT_MAX_TOKENS")
    openai_timeout_seconds: int = Field(default=120, alias="OPENAI_TIMEOUT_SECONDS")
    llm_rate_limit_enabled: bool = Field(default=True, alias="LLM_RATE_LIMIT_ENABLED")
    llm_rate_limit_per_minute: int = Field(default=120, alias="LLM_RATE_LIMIT_PER_MINUTE")
    llm_prompt_cost_per_1k: float = Field(default=0.0, alias="LLM_PROMPT_COST_PER_1K")
    llm_completion_cost_per_1k: float = Field(default=0.0, alias="LLM_COMPLETION_COST_PER_1K")
    agent_trace_debug: bool = Field(default=False, alias="AGENT_TRACE_DEBUG")

    embedding_base_url: str = Field(default="http://localhost:11434/v1", alias="EMBEDDING_BASE_URL")
    embedding_api_key: str = Field(default="ollama", alias="EMBEDDING_API_KEY")
    embedding_model: str = Field(default="nomic-embed-text", alias="EMBEDDING_MODEL")
    embedding_dim: int = Field(default=768, alias="EMBEDDING_DIM")
    embedding_batch_size: int = Field(default=10, alias="EMBEDDING_BATCH_SIZE")
    embedding_timeout_seconds: int = Field(default=60, alias="EMBEDDING_TIMEOUT_SECONDS")

    rag_top_k: int = Field(default=6, alias="RAG_TOP_K")
    rag_similarity_threshold: float = Field(default=0.25, alias="RAG_SIMILARITY_THRESHOLD")
    rag_max_context_chars: int = Field(default=8000, alias="RAG_MAX_CONTEXT_CHARS")

    summary_section_max_chars: int = Field(default=6000, alias="SUMMARY_SECTION_MAX_CHARS")
    summary_final_max_chars: int = Field(default=10000, alias="SUMMARY_FINAL_MAX_CHARS")

    arxiv_base_url: str = Field(default="http://export.arxiv.org/api/query", alias="ARXIV_BASE_URL")
    crossref_base_url: str = Field(default="https://api.crossref.org/works", alias="CROSSREF_BASE_URL")
    semantic_scholar_base_url: str = Field(
        default="https://api.semanticscholar.org/graph/v1",
        alias="SEMANTIC_SCHOLAR_BASE_URL",
    )
    semantic_scholar_api_key: str = Field(default="", alias="SEMANTIC_SCHOLAR_API_KEY")
    web_search_provider: str = Field(default="none", alias="WEB_SEARCH_PROVIDER")
    web_search_api_key: str = Field(default="", alias="WEB_SEARCH_API_KEY")
    literature_search_max_results: int = Field(default=10, alias="LITERATURE_SEARCH_MAX_RESULTS")
    literature_search_timeout_seconds: int = Field(default=20, alias="LITERATURE_SEARCH_TIMEOUT_SECONDS")
    literature_search_recent_years: int = Field(default=3, alias="LITERATURE_SEARCH_RECENT_YEARS")

    reference_extract_max_chars: int = Field(default=50000, alias="REFERENCE_EXTRACT_MAX_CHARS")
    reference_match_threshold: float = Field(default=0.82, alias="REFERENCE_MATCH_THRESHOLD")
    reference_dedup_threshold: float = Field(default=0.9, alias="REFERENCE_DEDUP_THRESHOLD")

    literature_review_max_items: int = Field(default=20, alias="LITERATURE_REVIEW_MAX_ITEMS")

    default_user_id: str = "00000000-0000-0000-0000-000000000001"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def ensure_storage_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.parsed_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.summary_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_storage_dirs()
    return settings

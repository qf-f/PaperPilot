from importlib import import_module

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


MODEL_MODULES = (
    "app.db.models.project",
    "app.db.models.document",
    "app.db.models.document_chunk",
    "app.db.models.task",
    "app.db.models.chat",
    "app.db.models.agent_run",
    "app.db.models.tool_trace",
    "app.db.models.generated_output",
    "app.db.models.export_task",
    "app.db.models.literature",
    "app.db.models.reference",
    "app.db.models.terminology",
)


def import_all_models() -> None:
    """Import model modules after Base is defined.

    Keeping this explicit avoids circular imports when a single model is
    imported directly, for example AgentRunner -> AgentRun -> Base.
    Alembic and app startup call this to populate Base.metadata.
    """
    for module in MODEL_MODULES:
        import_module(module)

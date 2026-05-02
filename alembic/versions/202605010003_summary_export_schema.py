"""summary and export schema

Revision ID: 202605010003
Revises: 202605010002
Create Date: 2026-05-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202605010003"
down_revision: str | None = "202605010002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generated_outputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("output_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("content_markdown", sa.Text(), nullable=True),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="generating"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["paper_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_generated_outputs_project_id", "generated_outputs", ["project_id"])
    op.create_index("idx_generated_outputs_document_id", "generated_outputs", ["document_id"])
    op.create_index("idx_generated_outputs_output_type", "generated_outputs", ["output_type"])
    op.create_index("idx_generated_outputs_status", "generated_outputs", ["status"])
    op.create_index(
        "idx_generated_outputs_project_output_type",
        "generated_outputs",
        ["project_id", "output_type"],
    )

    op.create_table(
        "export_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("output_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("export_type", sa.String(length=32), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["paper_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["output_id"], ["generated_outputs.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_export_tasks_project_id", "export_tasks", ["project_id"])
    op.create_index("idx_export_tasks_output_id", "export_tasks", ["output_id"])
    op.create_index("idx_export_tasks_status", "export_tasks", ["status"])


def downgrade() -> None:
    op.drop_index("idx_export_tasks_status", table_name="export_tasks")
    op.drop_index("idx_export_tasks_output_id", table_name="export_tasks")
    op.drop_index("idx_export_tasks_project_id", table_name="export_tasks")
    op.drop_table("export_tasks")
    op.drop_index("idx_generated_outputs_project_output_type", table_name="generated_outputs")
    op.drop_index("idx_generated_outputs_status", table_name="generated_outputs")
    op.drop_index("idx_generated_outputs_output_type", table_name="generated_outputs")
    op.drop_index("idx_generated_outputs_document_id", table_name="generated_outputs")
    op.drop_index("idx_generated_outputs_project_id", table_name="generated_outputs")
    op.drop_table("generated_outputs")

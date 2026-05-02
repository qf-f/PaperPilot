"""terminology schema

Revision ID: 202605010005
Revises: 202605010004
Create Date: 2026-05-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202605010005"
down_revision: str | None = "202605010004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "terminologies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_term", sa.String(length=255), nullable=False),
        sa.Column("target_term", sa.String(length=255), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="general"),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="extracted"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["paper_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("project_id", "source_term", name="uq_terminologies_project_source_term"),
    )
    op.create_index("idx_terminologies_project_id", "terminologies", ["project_id"])
    op.create_index("idx_terminologies_document_id", "terminologies", ["document_id"])
    op.create_index("idx_terminologies_source_term", "terminologies", ["source_term"])
    op.create_index("idx_terminologies_target_term", "terminologies", ["target_term"])
    op.create_index("idx_terminologies_category", "terminologies", ["category"])


def downgrade() -> None:
    op.drop_index("idx_terminologies_category", table_name="terminologies")
    op.drop_index("idx_terminologies_target_term", table_name="terminologies")
    op.drop_index("idx_terminologies_source_term", table_name="terminologies")
    op.drop_index("idx_terminologies_document_id", table_name="terminologies")
    op.drop_index("idx_terminologies_project_id", table_name="terminologies")
    op.drop_table("terminologies")

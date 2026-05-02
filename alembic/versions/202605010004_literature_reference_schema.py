"""literature and reference schema

Revision ID: 202605010004
Revises: 202605010003
Create Date: 2026-05-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202605010004"
down_revision: str | None = "202605010003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "literatures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("authors", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("venue", sa.String(length=255), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("categories", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("citation_count", sa.Integer(), nullable=True),
        sa.Column("influential_citation_count", sa.Integer(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("recommendation_reason", sa.Text(), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["paper_projects.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_literatures_project_id", "literatures", ["project_id"])
    op.create_index("idx_literatures_title", "literatures", ["title"])
    op.create_index("idx_literatures_doi", "literatures", ["doi"])
    op.create_index("idx_literatures_year", "literatures", ["year"])
    op.create_index("idx_literatures_source_provider", "literatures", ["source_provider"])
    op.create_index("idx_literatures_relevance_score", "literatures", ["relevance_score"])

    op.create_table(
        "paper_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False, server_default="uploaded_document"),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("authors", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("venue", sa.String(length=255), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("citation_key", sa.String(length=255), nullable=True),
        sa.Column("reference_format", sa.String(length=32), nullable=False, server_default="raw"),
        sa.Column("gb_t_7714", sa.Text(), nullable=True),
        sa.Column("ieee", sa.Text(), nullable=True),
        sa.Column("apa", sa.Text(), nullable=True),
        sa.Column("bibtex", sa.Text(), nullable=True),
        sa.Column("matched_literature_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["paper_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["matched_literature_id"], ["literatures.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_paper_references_project_id", "paper_references", ["project_id"])
    op.create_index("idx_paper_references_document_id", "paper_references", ["document_id"])
    op.create_index("idx_paper_references_title", "paper_references", ["title"])
    op.create_index("idx_paper_references_doi", "paper_references", ["doi"])
    op.create_index("idx_paper_references_year", "paper_references", ["year"])
    op.create_index("idx_paper_references_matched_literature_id", "paper_references", ["matched_literature_id"])


def downgrade() -> None:
    op.drop_index("idx_paper_references_matched_literature_id", table_name="paper_references")
    op.drop_index("idx_paper_references_year", table_name="paper_references")
    op.drop_index("idx_paper_references_doi", table_name="paper_references")
    op.drop_index("idx_paper_references_title", table_name="paper_references")
    op.drop_index("idx_paper_references_document_id", table_name="paper_references")
    op.drop_index("idx_paper_references_project_id", table_name="paper_references")
    op.drop_table("paper_references")
    op.drop_index("idx_literatures_relevance_score", table_name="literatures")
    op.drop_index("idx_literatures_source_provider", table_name="literatures")
    op.drop_index("idx_literatures_year", table_name="literatures")
    op.drop_index("idx_literatures_doi", table_name="literatures")
    op.drop_index("idx_literatures_title", table_name="literatures")
    op.drop_index("idx_literatures_project_id", table_name="literatures")
    op.drop_table("literatures")

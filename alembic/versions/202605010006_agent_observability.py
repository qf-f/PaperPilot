"""agent observability fields

Revision ID: 202605010006
Revises: 202605010005
Create Date: 2026-05-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202605010006"
down_revision: str | None = "202605010005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("agent_runs", sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("agent_runs", sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("agent_runs", sa.Column("estimated_cost", sa.Float(), nullable=False, server_default="0"))
    op.add_column("tool_traces", sa.Column("node_name", sa.String(length=128), nullable=True))
    op.create_index("idx_tool_traces_node_name", "tool_traces", ["node_name"])


def downgrade() -> None:
    op.drop_index("idx_tool_traces_node_name", table_name="tool_traces")
    op.drop_column("tool_traces", "node_name")
    op.drop_column("agent_runs", "estimated_cost")
    op.drop_column("agent_runs", "total_tokens")
    op.drop_column("agent_runs", "completion_tokens")
    op.drop_column("agent_runs", "prompt_tokens")

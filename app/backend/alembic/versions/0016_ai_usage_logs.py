"""ai usage logs

Revision ID: 0016_ai_usage_logs
Revises: 0015_live_safety_constraints
Create Date: 2026-08-13
"""

from alembic import op
import sqlalchemy as sa


revision = "0016_ai_usage_logs"
down_revision = "0015_live_safety_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="gestart"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ai_usage_logs_created_at", "ai_usage_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_usage_logs_created_at", table_name="ai_usage_logs")
    op.drop_table("ai_usage_logs")

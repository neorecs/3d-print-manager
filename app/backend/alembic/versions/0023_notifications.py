"""add notifications

Revision ID: 0023_notifications
Revises: 0022_overview_indexes
"""

from alembic import op
import sqlalchemy as sa


revision = "0023_notifications"
down_revision = "0022_overview_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="wachtend"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("link", sa.String(length=500), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("event_type", "entity_type", "entity_id", "channel", name="uq_notifications_event_channel"),
    )
    op.create_index("ix_notifications_status", "notifications", ["status"])


def downgrade() -> None:
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_table("notifications")

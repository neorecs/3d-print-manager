"""platform import logs

Revision ID: 0009_platform_import_logs
Revises: 0008_accounting_controls
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_platform_import_logs"
down_revision = "0008_accounting_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_import_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform_id", sa.Integer(), sa.ForeignKey("platforms.id"), nullable=False),
        sa.Column("import_type", sa.String(length=60), nullable=False, server_default="orders"),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="nieuw"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("platform_import_logs")

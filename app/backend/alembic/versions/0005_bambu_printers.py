"""bambu printers

Revision ID: 0005_bambu_printers
Revises: 0004_inventory_audit_fields
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0005_bambu_printers"
down_revision = "0004_inventory_audit_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "bambu_printers" in set(inspector.get_table_names()):
        return

    op.create_table(
        "bambu_printers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("serial_number", sa.String(length=255), nullable=True),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("mqtt_port", sa.Integer(), nullable=False, server_default="8883"),
        sa.Column("access_code_encrypted", sa.String(length=2048), nullable=True),
        sa.Column("connection_mode", sa.String(length=50), nullable=False, server_default="lan"),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_status", sa.String(length=50), nullable=False, server_default="onbekend"),
        sa.Column("status_message", sa.String(length=1000), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("bambu_printers")

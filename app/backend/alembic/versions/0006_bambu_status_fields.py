"""bambu status fields

Revision ID: 0006_bambu_status_fields
Revises: 0005_bambu_printers
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0006_bambu_status_fields"
down_revision = "0005_bambu_printers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("bambu_printers")}

    def add_column_if_missing(name: str, column) -> None:
        if name not in columns:
            op.add_column("bambu_printers", column)

    add_column_if_missing("printer_state", sa.Column("printer_state", sa.String(length=100), nullable=True))
    add_column_if_missing("print_progress", sa.Column("print_progress", sa.Integer(), nullable=True))
    add_column_if_missing("nozzle_temperature", sa.Column("nozzle_temperature", sa.Float(), nullable=True))
    add_column_if_missing("bed_temperature", sa.Column("bed_temperature", sa.Float(), nullable=True))
    add_column_if_missing("chamber_temperature", sa.Column("chamber_temperature", sa.Float(), nullable=True))
    add_column_if_missing("current_task", sa.Column("current_task", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("bambu_printers", "current_task")
    op.drop_column("bambu_printers", "chamber_temperature")
    op.drop_column("bambu_printers", "bed_temperature")
    op.drop_column("bambu_printers", "nozzle_temperature")
    op.drop_column("bambu_printers", "print_progress")
    op.drop_column("bambu_printers", "printer_state")

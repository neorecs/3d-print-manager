"""bambu status fields

Revision ID: 0006_bambu_status_fields
Revises: 0005_bambu_printers
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_bambu_status_fields"
down_revision = "0005_bambu_printers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bambu_printers", sa.Column("printer_state", sa.String(length=100), nullable=True))
    op.add_column("bambu_printers", sa.Column("print_progress", sa.Integer(), nullable=True))
    op.add_column("bambu_printers", sa.Column("nozzle_temperature", sa.Float(), nullable=True))
    op.add_column("bambu_printers", sa.Column("bed_temperature", sa.Float(), nullable=True))
    op.add_column("bambu_printers", sa.Column("chamber_temperature", sa.Float(), nullable=True))
    op.add_column("bambu_printers", sa.Column("current_task", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("bambu_printers", "current_task")
    op.drop_column("bambu_printers", "chamber_temperature")
    op.drop_column("bambu_printers", "bed_temperature")
    op.drop_column("bambu_printers", "nozzle_temperature")
    op.drop_column("bambu_printers", "print_progress")
    op.drop_column("bambu_printers", "printer_state")

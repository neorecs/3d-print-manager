"""Store the latest AMS tray snapshot for each Bambu printer.

Revision ID: 0017_bambu_ams_slots
Revises: 0016_ai_usage_logs
"""

from alembic import op
import sqlalchemy as sa


revision = "0017_bambu_ams_slots"
down_revision = "0016_ai_usage_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bambu_printers", sa.Column("ams_slots_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("bambu_printers", "ams_slots_json")

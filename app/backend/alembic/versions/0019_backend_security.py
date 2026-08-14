"""Add revocable user sessions.

Revision ID: 0019_backend_security
Revises: 0018_print_job_printer
"""

from alembic import op
import sqlalchemy as sa


revision = "0019_backend_security"
down_revision = "0018_print_job_printer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("session_version", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    op.drop_column("users", "session_version")

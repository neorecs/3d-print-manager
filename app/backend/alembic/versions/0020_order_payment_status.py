"""store payment status on orders

Revision ID: 0020_order_payment_status
Revises: 0019_backend_security
"""

from alembic import op
import sqlalchemy as sa


revision = "0020_order_payment_status"
down_revision = "0019_backend_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("payment_status", sa.String(length=40), nullable=False, server_default="onbekend"))


def downgrade() -> None:
    op.drop_column("orders", "payment_status")

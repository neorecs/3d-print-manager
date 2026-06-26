"""add inventory movement audit fields

Revision ID: 0004_inventory_audit_fields
Revises: 0003_publication_media
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0004_inventory_audit_fields"
down_revision = "0003_publication_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("inventory_movements")}

    def add_column_if_missing(name: str, column_type) -> None:
        if name not in columns:
            op.add_column("inventory_movements", sa.Column(name, column_type, nullable=True))

    add_column_if_missing("quantity_on_hand_before", sa.Integer())
    add_column_if_missing("quantity_on_hand_after", sa.Integer())
    add_column_if_missing("quantity_reserved_before", sa.Integer())
    add_column_if_missing("quantity_reserved_after", sa.Integer())
    add_column_if_missing("free_stock_before", sa.Integer())
    add_column_if_missing("free_stock_after", sa.Integer())
    add_column_if_missing("source", sa.String(length=120))
    add_column_if_missing("reason", sa.Text())
    add_column_if_missing("performed_by", sa.String(length=120))


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("inventory_movements")}
    for name in [
        "performed_by",
        "reason",
        "source",
        "free_stock_after",
        "free_stock_before",
        "quantity_reserved_after",
        "quantity_reserved_before",
        "quantity_on_hand_after",
        "quantity_on_hand_before",
    ]:
        if name in columns:
            op.drop_column("inventory_movements", name)

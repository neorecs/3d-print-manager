"""cost settings and order profit calculations

Revision ID: 0002_costs
Revises: 0001_initial_schema
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0002_costs"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    if "cost_settings" not in existing_tables:
        op.create_table(
            "cost_settings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("setting_name", sa.String(length=120), nullable=False, unique=True),
            sa.Column("value", sa.Numeric(10, 4), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if "order_profit_calculations" in existing_tables:
        return

    op.create_table(
        "order_profit_calculations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False, unique=True),
        sa.Column("sale_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("filament_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("packaging_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("platform_fee", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("shipping_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("electricity_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("estimated_profit", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("order_profit_calculations")
    op.drop_table("cost_settings")

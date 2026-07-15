"""accounting controls

Revision ID: 0008_accounting_controls
Revises: 0007_accounting_module
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0008_accounting_controls"
down_revision = "0007_accounting_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    sales_columns = {column["name"] for column in inspector.get_columns("accounting_sales")}
    purchase_columns = {column["name"] for column in inspector.get_columns("accounting_purchases")}
    existing_tables = set(inspector.get_table_names())

    if "entry_type" not in sales_columns:
        op.add_column("accounting_sales", sa.Column("entry_type", sa.String(length=40), nullable=False, server_default="sale"))
    if "correction_of_sale_id" not in sales_columns:
        op.add_column("accounting_sales", sa.Column("correction_of_sale_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_accounting_sales_correction_of_sale_id", "accounting_sales", "accounting_sales", ["correction_of_sale_id"], ["id"])

    if "entry_type" not in purchase_columns:
        op.add_column("accounting_purchases", sa.Column("entry_type", sa.String(length=40), nullable=False, server_default="purchase"))
    if "correction_of_purchase_id" not in purchase_columns:
        op.add_column("accounting_purchases", sa.Column("correction_of_purchase_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_accounting_purchases_correction_of_purchase_id", "accounting_purchases", "accounting_purchases", ["correction_of_purchase_id"], ["id"])

    if "accounting_fiscal_settings" not in existing_tables:
        op.create_table(
            "accounting_fiscal_settings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("setting_name", sa.String(length=80), nullable=False, unique=True),
            sa.Column("value", sa.String(length=255), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("accounting_fiscal_settings")
    op.drop_constraint("fk_accounting_purchases_correction_of_purchase_id", "accounting_purchases", type_="foreignkey")
    op.drop_column("accounting_purchases", "correction_of_purchase_id")
    op.drop_column("accounting_purchases", "entry_type")
    op.drop_constraint("fk_accounting_sales_correction_of_sale_id", "accounting_sales", type_="foreignkey")
    op.drop_column("accounting_sales", "correction_of_sale_id")
    op.drop_column("accounting_sales", "entry_type")

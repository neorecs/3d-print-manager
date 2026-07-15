"""accounting module

Revision ID: 0007_accounting_module
Revises: 0006_bambu_status_fields
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0007_accounting_module"
down_revision = "0006_bambu_status_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_tables = set(inspect(op.get_bind()).get_table_names())
    if "accounting_sales" not in existing_tables:
        op.create_table(
            "accounting_sales",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
            sa.Column("platform_id", sa.Integer(), sa.ForeignKey("platforms.id"), nullable=True),
            sa.Column("invoice_number", sa.String(length=80), nullable=True, unique=True),
            sa.Column("invoice_date", sa.Date(), nullable=True),
            sa.Column("customer_name", sa.String(length=255), nullable=True),
            sa.Column("customer_country", sa.String(length=80), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("net_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False, server_default="21"),
            sa.Column("vat_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="EUR"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="concept"),
            sa.Column("source", sa.String(length=60), nullable=False, server_default="manual"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if "accounting_purchases" not in existing_tables:
        op.create_table(
            "accounting_purchases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("supplier_name", sa.String(length=255), nullable=False),
            sa.Column("invoice_number", sa.String(length=120), nullable=True),
            sa.Column("invoice_date", sa.Date(), nullable=True),
            sa.Column("category", sa.String(length=80), nullable=False, server_default="overig"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("net_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False, server_default="21"),
            sa.Column("vat_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="EUR"),
            sa.Column("payment_status", sa.String(length=40), nullable=False, server_default="onbekend"),
            sa.Column("source", sa.String(length=60), nullable=False, server_default="manual"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if "accounting_documents" not in existing_tables:
        op.create_table(
            "accounting_documents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("document_type", sa.String(length=40), nullable=False),
            sa.Column("sale_id", sa.Integer(), sa.ForeignKey("accounting_sales.id"), nullable=True),
            sa.Column("purchase_id", sa.Integer(), sa.ForeignKey("accounting_purchases.id"), nullable=True),
            sa.Column("file_path", sa.String(length=500), nullable=False),
            sa.Column("original_filename", sa.String(length=255), nullable=True),
            sa.Column("mime_type", sa.String(length=120), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="bewaard"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if "vat_periods" not in existing_tables:
        op.create_table(
            "vat_periods",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("period_name", sa.String(length=40), nullable=False, unique=True),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("sales_vat", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("purchase_vat", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("vat_due", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="concept"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("vat_periods")
    op.drop_table("accounting_documents")
    op.drop_table("accounting_purchases")
    op.drop_table("accounting_sales")

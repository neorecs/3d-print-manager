"""product translations

Revision ID: 0010_product_translations
Revises: 0009_platform_import_logs
Create Date: 2026-06-28
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_product_translations"
down_revision = "0009_platform_import_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("language_code", sa.String(length=10), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("short_description", sa.Text(), nullable=True),
        sa.Column("long_description", sa.Text(), nullable=True),
        sa.Column("sales_description", sa.Text(), nullable=True),
        sa.Column("seo_title", sa.String(length=255), nullable=True),
        sa.Column("seo_description", sa.Text(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="concept"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_product_translations_product_language", "product_translations", ["product_id", "language_code"])


def downgrade() -> None:
    op.drop_constraint("uq_product_translations_product_language", "product_translations", type_="unique")
    op.drop_table("product_translations")

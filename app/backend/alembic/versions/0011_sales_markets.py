"""sales markets

Revision ID: 0011_sales_markets
Revises: 0010_product_translations
Create Date: 2026-06-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0011_sales_markets"
down_revision = "0010_product_translations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "sales_markets" not in set(inspector.get_table_names()):
        op.create_table(
            "sales_markets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("country_code", sa.String(length=2), nullable=False),
            sa.Column("country_name", sa.String(length=120), nullable=False),
            sa.Column("primary_language", sa.String(length=10), nullable=False, server_default="nl"),
            sa.Column("additional_languages", sa.String(length=120), nullable=True),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="EUR"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_unique_constraint("uq_sales_markets_country_code", "sales_markets", ["country_code"])
    existing_count = op.get_bind().execute(sa.text("SELECT COUNT(*) FROM sales_markets")).scalar()
    if existing_count:
        return

    op.bulk_insert(
        sa.table(
            "sales_markets",
            sa.column("country_code", sa.String),
            sa.column("country_name", sa.String),
            sa.column("primary_language", sa.String),
            sa.column("additional_languages", sa.String),
            sa.column("currency", sa.String),
            sa.column("active", sa.Boolean),
            sa.column("note", sa.Text),
        ),
        [
            {
                "country_code": "NL",
                "country_name": "Nederland",
                "primary_language": "nl",
                "additional_languages": None,
                "currency": "EUR",
                "active": True,
                "note": "Startmarkt. Nederlandse productteksten zijn leidend.",
            },
            {
                "country_code": "BE",
                "country_name": "Belgie",
                "primary_language": "nl",
                "additional_languages": "fr",
                "currency": "EUR",
                "active": True,
                "note": "Belgische markt. Nederlands als basis, Frans als extra publicatietaal.",
            },
            {
                "country_code": "DE",
                "country_name": "Duitsland",
                "primary_language": "de",
                "additional_languages": None,
                "currency": "EUR",
                "active": True,
                "note": "Duitse markt. Vereist Duitse productteksten voordat je publiceert.",
            },
        ],
    )


def downgrade() -> None:
    op.drop_constraint("uq_sales_markets_country_code", "sales_markets", type_="unique")
    op.drop_table("sales_markets")

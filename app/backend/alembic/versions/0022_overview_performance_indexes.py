"""add overview performance indexes

Revision ID: 0022_overview_indexes
Revises: 0021_order_idempotency
"""

from alembic import op
import sqlalchemy as sa


revision = "0022_overview_indexes"
down_revision = "0021_order_idempotency"
branch_labels = None
depends_on = None


INDEXES = (
    ("ix_products_active_status", "products", ["active", "status"]),
    ("ix_product_variants_product_id", "product_variants", ["product_id"]),
    ("ix_product_inventory_product_id", "product_inventory", ["product_id"]),
    ("ix_product_publications_product_status", "product_platform_publications", ["product_id", "publication_status"]),
    ("ix_orders_status_id", "orders", ["status", "id"]),
    ("ix_orders_payment_status", "orders", ["payment_status"]),
    ("ix_orders_order_date", "orders", ["order_date"]),
    ("ix_order_items_order_id", "order_items", ["order_id"]),
    ("ix_order_items_product_id", "order_items", ["product_id"]),
    ("ix_print_jobs_status_id", "print_jobs", ["status", "id"]),
    ("ix_platform_import_logs_type_started", "platform_import_logs", ["import_type", "started_at"]),
)


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    for name, table, columns in INDEXES:
        existing = {item["name"] for item in inspector.get_indexes(table) if item.get("name")}
        if name not in existing:
            op.create_index(name, table, columns)


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    for name, table, _ in reversed(INDEXES):
        existing = {item["name"] for item in inspector.get_indexes(table) if item.get("name")}
        if name in existing:
            op.drop_index(name, table_name=table)

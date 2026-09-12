"""protect idempotent order processing

Revision ID: 0021_order_idempotency
Revises: 0020_order_payment_status
"""

from alembic import op


revision = "0021_order_idempotency"
down_revision = "0020_order_payment_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    duplicate_jobs = connection.exec_driver_sql(
        "SELECT order_item_id FROM print_jobs WHERE order_item_id IS NOT NULL GROUP BY order_item_id HAVING count(*) > 1 LIMIT 1"
    ).first()
    duplicate_sales = connection.exec_driver_sql(
        "SELECT order_id FROM accounting_sales WHERE order_id IS NOT NULL GROUP BY order_id HAVING count(*) > 1 LIMIT 1"
    ).first()
    if duplicate_jobs or duplicate_sales:
        raise RuntimeError("Dubbele printtaken of verkoopboekingen gevonden. Herstel deze voordat migratie 0021 wordt uitgevoerd.")
    op.create_unique_constraint("uq_print_jobs_order_item", "print_jobs", ["order_item_id"])
    op.create_unique_constraint("uq_accounting_sales_order", "accounting_sales", ["order_id"])


def downgrade() -> None:
    op.drop_constraint("uq_accounting_sales_order", "accounting_sales", type_="unique")
    op.drop_constraint("uq_print_jobs_order_item", "print_jobs", type_="unique")

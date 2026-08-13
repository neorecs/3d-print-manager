"""live safety constraints

Revision ID: 0015_live_safety_constraints
Revises: 0014_product_print_file
Create Date: 2026-08-13
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_live_safety_constraints"
down_revision = "0014_product_print_file"
branch_labels = None
depends_on = None


def _unique_names(inspector, table_name: str) -> set[str]:
    return {item["name"] for item in inspector.get_unique_constraints(table_name) if item.get("name")}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Stop the migration instead of silently choosing which duplicate business record to keep.
    duplicate_checks = (
        ("orders", "platform_id, external_order_id"),
        ("product_inventory", "product_variant_id"),
        ("product_translations", "product_id, language_code"),
        ("product_platform_publications", "product_id, platform_id"),
        ("product_variant_platform_links", "product_variant_id, platform_id"),
    )
    for table_name, columns in duplicate_checks:
        duplicate = bind.execute(sa.text(f"SELECT {columns}, COUNT(*) FROM {table_name} GROUP BY {columns} HAVING COUNT(*) > 1 LIMIT 1")).first()
        if duplicate:
            raise RuntimeError(f"Kan unieke constraint niet toevoegen: dubbele records in {table_name} voor {columns}.")

    unique_constraints = {
        "orders": ("uq_orders_platform_external", ["platform_id", "external_order_id"]),
        "product_inventory": ("uq_product_inventory_variant", ["product_variant_id"]),
        "product_translations": ("uq_product_translation_language", ["product_id", "language_code"]),
        "product_platform_publications": ("uq_product_publication_platform", ["product_id", "platform_id"]),
        "product_variant_platform_links": ("uq_variant_platform_link", ["product_variant_id", "platform_id"]),
    }
    for table_name, (name, columns) in unique_constraints.items():
        if name not in _unique_names(inspector, table_name):
            op.create_unique_constraint(name, table_name, columns)

    invalid_inventory = bind.execute(
        sa.text("SELECT id FROM product_inventory WHERE quantity_on_hand < 0 OR quantity_reserved < 0 OR quantity_reserved > quantity_on_hand LIMIT 1")
    ).first()
    if invalid_inventory:
        raise RuntimeError("Kan voorraadconstraints niet toevoegen: corrigeer eerst ongeldige voorraadregel(s).")
    op.create_check_constraint("ck_product_inventory_on_hand_nonnegative", "product_inventory", "quantity_on_hand >= 0")
    op.create_check_constraint("ck_product_inventory_reserved_nonnegative", "product_inventory", "quantity_reserved >= 0")
    op.create_check_constraint("ck_product_inventory_reserved_lte_on_hand", "product_inventory", "quantity_reserved <= quantity_on_hand")


def downgrade() -> None:
    op.drop_constraint("ck_product_inventory_reserved_lte_on_hand", "product_inventory", type_="check")
    op.drop_constraint("ck_product_inventory_reserved_nonnegative", "product_inventory", type_="check")
    op.drop_constraint("ck_product_inventory_on_hand_nonnegative", "product_inventory", type_="check")
    for table_name, name in (
        ("product_variant_platform_links", "uq_variant_platform_link"),
        ("product_platform_publications", "uq_product_publication_platform"),
        ("product_translations", "uq_product_translation_language"),
        ("product_inventory", "uq_product_inventory_variant"),
        ("orders", "uq_orders_platform_external"),
    ):
        op.drop_constraint(name, table_name, type_="unique")

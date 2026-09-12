from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.utils import to_dict
from domain.statuses import (
    ACCOUNTING_CANCELLED,
    ACCOUNTING_CONCEPT,
    INVENTORY_NONE,
    ORDER_CANCELLED,
    ORDER_NEW,
    ORDER_SHIPPED,
    PRINT_JOB_CANCELLED,
    PRINT_JOB_NEW,
    PRINT_JOB_PLANNED,
)
from inventory.service import add_inventory_movement, inventory_snapshot, link_order_item_by_sku
from models import AccountingSale, Order, OrderItem, Platform, PrintJob, ProductInventory


CANCELLED_EXTERNAL_STATUSES = {"cancelled", "canceled", "voided"}
SHIPPED_EXTERNAL_STATUSES = {"completed", "fulfilled", "shipped"}


def upsert_imported_order(db: Session, platform: Platform, payload: dict) -> dict:
    external_order_id = payload.get("external_order_id")
    if not external_order_id:
        return {"action": "skipped", "order": {"reason": "Order zonder external_order_id overgeslagen"}, "warnings": []}

    order = db.scalar(
        select(Order).where(
            Order.platform_id == platform.id,
            Order.external_order_id == external_order_id,
        ).with_for_update()
    )
    action = "updated" if order else "created"
    if not order:
        order_number = str(payload.get("order_number") or external_order_id).replace("#", "").strip()
        prefix = (platform.type or platform.name or "platform").upper()
        order = Order(
            internal_order_number=f"{prefix}-{platform.id}-{order_number}",
            platform_id=platform.id,
            external_order_id=external_order_id,
            status=ORDER_NEW,
        )
        db.add(order)
        db.flush()

    order.customer_name = payload.get("customer_name")
    order.customer_email = payload.get("customer_email")
    order.order_date = parse_optional_datetime(payload.get("order_date"))
    order.total_amount = payload.get("total_amount")
    order.currency = payload.get("currency") or "EUR"
    order.payment_status = payload.get("payment_status") or "onbekend"

    imported_item_ids = set()
    for item_payload in payload.get("items", []):
        external_item_id = item_payload.get("external_order_item_id")
        if not external_item_id:
            continue
        imported_item_ids.add(str(external_item_id))
        item = db.scalar(
            select(OrderItem).where(
                OrderItem.order_id == order.id,
                OrderItem.external_order_item_id == str(external_item_id),
            ).with_for_update()
        )
        if not item:
            item = OrderItem(order_id=order.id, external_order_item_id=str(external_item_id), quantity_ordered=0)
            db.add(item)
        item.sku = item_payload.get("sku")
        item.quantity_ordered = int(item_payload.get("quantity_ordered") or 0)
        item.unit_sale_price = item_payload.get("unit_sale_price")
        item.inventory_status = item.inventory_status or INVENTORY_NONE
        link_order_item_by_sku(db, item)
    db.flush()

    warnings = []
    external_status = str(payload.get("external_status") or "").strip().lower()
    if external_status in CANCELLED_EXTERNAL_STATUSES:
        warnings.extend(cancel_imported_order(db, order))
    elif external_status in SHIPPED_EXTERNAL_STATUSES and order.status != ORDER_CANCELLED:
        order.status = ORDER_SHIPPED

    existing_item_ids = {
        str(item.external_order_item_id)
        for item in db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
        if item.external_order_item_id
    }
    missing_items = existing_item_ids - imported_item_ids
    if missing_items and external_status not in CANCELLED_EXTERNAL_STATUSES:
        warnings.append("Een eerder geimporteerde orderregel ontbreekt in de platformrespons; controleer deze order handmatig.")
    return {"action": action, "order": to_dict(order), "warnings": warnings}


def cancel_imported_order(db: Session, order: Order) -> list[str]:
    warnings = []
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id).with_for_update()).all()
    for item in items:
        if item.quantity_from_inventory:
            inventory = db.scalar(
                select(ProductInventory).where(
                    ProductInventory.product_variant_id == item.product_variant_id
                ).with_for_update()
            )
            if not inventory or inventory.quantity_reserved < item.quantity_from_inventory:
                warnings.append(f"Reservering van orderregel {item.id} kon niet automatisch worden vrijgegeven.")
            else:
                before = inventory_snapshot(inventory)
                released = item.quantity_from_inventory
                inventory.quantity_reserved -= released
                add_inventory_movement(
                    db,
                    inventory,
                    "reservering_vrijgegeven",
                    released,
                    before=before,
                    order_id=order.id,
                    order_item_id=item.id,
                    note="Platformorder geannuleerd",
                    source="platform_order_cancellation",
                )
                item.quantity_from_inventory = 0
        item.quantity_to_print = 0
        item.inventory_status = INVENTORY_NONE
        jobs = db.scalars(select(PrintJob).where(PrintJob.order_item_id == item.id).with_for_update()).all()
        for job in jobs:
            if job.status in {PRINT_JOB_NEW, PRINT_JOB_PLANNED}:
                job.status = PRINT_JOB_CANCELLED
            elif job.status != PRINT_JOB_CANCELLED:
                warnings.append(f"Printtaak {job.id} was al gestart of verwerkt en vereist handmatige controle.")

    sale = db.scalar(select(AccountingSale).where(AccountingSale.order_id == order.id).with_for_update())
    if sale and sale.status == ACCOUNTING_CONCEPT:
        sale.status = ACCOUNTING_CANCELLED
        sale.note = append_note(sale.note, "Platformorder geannuleerd; conceptboeking automatisch geannuleerd.")
    elif sale and sale.status != ACCOUNTING_CANCELLED:
        warnings.append(f"Verkoopboeking {sale.id} is niet automatisch gecorrigeerd; maak een controleerbare correctieboeking.")
    order.status = ORDER_CANCELLED
    return warnings


def parse_optional_datetime(value: str | None):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def append_note(current: str | None, addition: str) -> str:
    return f"{current.rstrip()} {addition}" if current else addition

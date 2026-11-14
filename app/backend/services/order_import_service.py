from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.utils import to_dict
from domain.statuses import (
    INVENTORY_NONE,
    ORDER_CANCELLED,
    ORDER_NEW,
    ORDER_SHIPPED,
)
from inventory.service import link_order_item_by_sku
from models import Order, OrderItem, Platform, ProductVariant
from services.order_fulfillment import cancel_order, ship_order


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
        item.sku = item_payload.get("sku") or _sku_for_ean(db, item_payload.get("ean"))
        item.quantity_ordered = int(item_payload.get("quantity_ordered") or 0)
        item.unit_sale_price = item_payload.get("unit_sale_price")
        item.inventory_status = item.inventory_status or INVENTORY_NONE
        link_order_item_by_sku(db, item)
    db.flush()

    warnings = []
    external_status = str(payload.get("external_status") or "").strip().lower()
    if external_status in CANCELLED_EXTERNAL_STATUSES:
        warnings.extend(cancel_imported_order(db, order))
    elif external_status in SHIPPED_EXTERNAL_STATUSES and order.status not in {ORDER_CANCELLED, ORDER_SHIPPED}:
        # The platform already shipped it: book reserved stock out, report gaps instead of blocking.
        warnings.extend(ship_order(db, order.id, strict=False, commit=False, performed_by="platform_import")["warnings"])

    existing_item_ids = {
        str(item.external_order_item_id)
        for item in db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
        if item.external_order_item_id
    }
    missing_items = existing_item_ids - imported_item_ids
    if missing_items and external_status not in CANCELLED_EXTERNAL_STATUSES:
        warnings.append("Een eerder geimporteerde orderregel ontbreekt in de platformrespons; controleer deze order handmatig.")
    return {"action": action, "order": to_dict(order), "warnings": warnings}


def _sku_for_ean(db: Session, ean: str | None) -> str | None:
    """Channels such as bol identify products by EAN; map that to our own SKU."""
    if not ean:
        return None
    return db.scalar(select(ProductVariant.sku).where(ProductVariant.ean == str(ean).strip()))


def cancel_imported_order(db: Session, order: Order) -> list[str]:
    if order.status == ORDER_SHIPPED:
        return ["De platformorder is geannuleerd, maar staat hier al als verzonden. Controleer retour en voorraad handmatig."]
    result = cancel_order(db, order.id, performed_by="platform_import", reason="Platformorder geannuleerd", commit=False)
    return result["warnings"]


def parse_optional_datetime(value: str | None):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def append_note(current: str | None, addition: str) -> str:
    return f"{current.rstrip()} {addition}" if current else addition

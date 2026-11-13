"""Order handling after processing: packing, shipping and cancelling.

Shipping consumes the stock that was reserved for the order (both the physical
stock and the reservation go down), so reserved stock no longer stays locked
forever once an order has left the building. Cancelling releases reservations
and cancels print work that has not started yet.
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.utils import to_dict
from domain.statuses import (
    ACCOUNTING_CANCELLED,
    ACCOUNTING_CONCEPT,
    INVENTORY_NONE,
    ORDER_CANCELLED,
    ORDER_NEW,
    ORDER_PACKED,
    ORDER_SHIPPED,
    PRINT_JOB_CANCELLED,
    PRINT_JOB_NEW,
    PRINT_JOB_PLANNED,
    PRINT_JOB_PARTLY_FAILED,
    PRINT_JOB_PRINTED,
    PRINT_JOB_PROCESSED,
)
from inventory.service import add_inventory_movement, inventory_snapshot
from models import AccountingSale, Order, OrderItem, PrintJob, ProductInventory

CLOSED_ORDER_STATUSES = {ORDER_SHIPPED, ORDER_CANCELLED}
FINISHED_PRINT_JOB_STATUSES = {PRINT_JOB_PRINTED, PRINT_JOB_PARTLY_FAILED, PRINT_JOB_PROCESSED}


def _lock_order(db: Session, order_id: int) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update().execution_options(populate_existing=True))
    if not order:
        raise HTTPException(404, "Order niet gevonden")
    return order


def _lock_items(db: Session, order_id: int) -> list[OrderItem]:
    return list(db.scalars(select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.id).with_for_update()).all())


def _lock_inventory(db: Session, item: OrderItem) -> ProductInventory | None:
    return db.scalar(
        select(ProductInventory).where(
            ProductInventory.product_id == item.product_id,
            ProductInventory.product_variant_id == item.product_variant_id,
        ).with_for_update()
    )


def fulfillment_blockers(db: Session, order: Order, items: list[OrderItem]) -> list[str]:
    """Reasons why an order cannot be packed or shipped yet. Empty list means ready."""
    if order.status in CLOSED_ORDER_STATUSES:
        return ["Deze order is al verzonden of geannuleerd."]
    if order.status == ORDER_NEW or not items:
        return ["Verwerk de order eerst, zodat voorraad en printwerk bekend zijn."]
    blockers = []
    for item in items:
        if item.quantity_from_inventory + item.quantity_to_print < item.quantity_ordered:
            blockers.append(f"Orderregel {item.id} is nog niet volledig verwerkt.")
            continue
        if item.quantity_to_print <= 0:
            continue
        job = db.get(PrintJob, item.print_job_id) if item.print_job_id else None
        if not job or job.status not in FINISHED_PRINT_JOB_STATUSES:
            blockers.append(f"Printwerk voor orderregel {item.id} is nog niet klaar.")
        elif (job.quantity_to_order or 0) < item.quantity_to_print:
            blockers.append(f"Voor orderregel {item.id} zijn nog te weinig stuks gelukt.")
    return blockers


def pack_order(db: Session, order_id: int) -> dict:
    try:
        order = _lock_order(db, order_id)
        items = _lock_items(db, order_id)
        blockers = fulfillment_blockers(db, order, items)
        if blockers:
            raise HTTPException(409, " ".join(blockers))
        order.status = ORDER_PACKED
        db.commit()
        return {"status": "packed", "order": to_dict(order), "message": "Order staat op ingepakt."}
    except Exception:
        db.rollback()
        raise


def ship_order(db: Session, order_id: int, *, performed_by: str = "system", strict: bool = True, commit: bool = True) -> dict:
    """Mark an order as shipped and book its reserved stock out.

    strict=False is used for platform imports: the platform already shipped the
    order, so it is recorded even if the app's own print administration lags
    behind. Problems are returned as warnings instead of blocking.
    """
    try:
        order = _lock_order(db, order_id)
        if order.status == ORDER_SHIPPED:
            return {"status": "already_shipped", "order": to_dict(order), "warnings": [], "message": "Order was al verzonden."}
        if order.status == ORDER_CANCELLED:
            raise HTTPException(409, "Een geannuleerde order kan niet worden verzonden.")
        items = _lock_items(db, order_id)
        warnings = fulfillment_blockers(db, order, items)
        if warnings and strict:
            raise HTTPException(409, " ".join(warnings))

        for item in sorted(items, key=lambda line: (line.product_variant_id or 0, line.id)):
            quantity = item.quantity_from_inventory or 0
            if quantity <= 0:
                continue
            inventory = _lock_inventory(db, item)
            if not inventory or inventory.quantity_reserved < quantity or inventory.quantity_on_hand < quantity:
                message = f"Reservering van orderregel {item.id} past niet bij de voorraad; controleer de voorraadbewegingen."
                if strict:
                    raise HTTPException(409, message)
                warnings.append(message)
                continue
            before = inventory_snapshot(inventory)
            inventory.quantity_reserved -= quantity
            inventory.quantity_on_hand -= quantity
            add_inventory_movement(
                db,
                inventory,
                "verzonden",
                -quantity,
                before=before,
                order_id=order.id,
                order_item_id=item.id,
                note="Order verzonden: gereserveerde voorraad afgeboekt",
                source="order_shipment",
                performed_by=performed_by,
            )
        order.status = ORDER_SHIPPED
        if commit:
            db.commit()
        else:
            db.flush()
        return {"status": "shipped", "order": to_dict(order), "warnings": warnings, "message": "Order verzonden; gereserveerde voorraad is afgeboekt."}
    except Exception:
        if commit:
            db.rollback()
        raise


def cancel_order(db: Session, order_id: int, *, performed_by: str = "system", reason: str = "Order geannuleerd", commit: bool = True) -> dict:
    """Cancel an order: release reservations, cancel unstarted print work and concept bookings."""
    try:
        order = _lock_order(db, order_id)
        if order.status == ORDER_CANCELLED:
            return {"status": "already_cancelled", "order": to_dict(order), "warnings": [], "message": "Order was al geannuleerd."}
        if order.status == ORDER_SHIPPED:
            raise HTTPException(409, "Een verzonden order kan niet worden geannuleerd. Maak een retour- of correctieboeking.")
        warnings = []
        items = _lock_items(db, order_id)
        for item in sorted(items, key=lambda line: (line.product_variant_id or 0, line.id)):
            if item.quantity_from_inventory:
                inventory = _lock_inventory(db, item)
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
                        note=reason,
                        source="order_cancellation",
                        performed_by=performed_by,
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
            sale.note = f"{sale.note.rstrip()} {reason}; conceptboeking automatisch geannuleerd." if sale.note else f"{reason}; conceptboeking automatisch geannuleerd."
        elif sale and sale.status != ACCOUNTING_CANCELLED:
            warnings.append(f"Verkoopboeking {sale.id} is niet automatisch gecorrigeerd; maak een controleerbare correctieboeking.")
        order.status = ORDER_CANCELLED
        if commit:
            db.commit()
        else:
            db.flush()
        return {"status": "cancelled", "order": to_dict(order), "warnings": warnings, "message": "Order geannuleerd; reserveringen zijn vrijgegeven."}
    except Exception:
        if commit:
            db.rollback()
        raise

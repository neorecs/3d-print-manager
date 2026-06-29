from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.utils import to_dict
from domain.statuses import (
    INVENTORY_FULL,
    INVENTORY_NONE,
    INVENTORY_PARTIAL,
    ORDER_FULLY_FROM_INVENTORY,
    ORDER_FULLY_TO_PRINT,
    ORDER_NEW,
    ORDER_PARTLY_TO_PRINT,
)
from models import InventoryMovement, Order, OrderItem, ProductInventory, ProductVariant


def get_required(db: Session, model: type, item_id: int):
    item = db.get(model, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return item


def link_order_item_by_sku(db: Session, item: OrderItem) -> None:
    if not item.sku:
        return
    variant = db.scalar(select(ProductVariant).where(ProductVariant.sku == item.sku))
    if variant:
        item.product_variant_id = variant.id
        item.product_id = variant.product_id


def list_product_inventory_rows(db: Session) -> list[dict]:
    rows = []
    for item in db.scalars(select(ProductInventory).order_by(ProductInventory.id)).all():
        data = to_dict(item)
        data["free_stock"] = item.free_stock
        rows.append(data)
    return rows


def inventory_snapshot(inventory: ProductInventory) -> dict[str, int]:
    return {
        "quantity_on_hand": inventory.quantity_on_hand,
        "quantity_reserved": inventory.quantity_reserved,
        "free_stock": inventory.free_stock,
    }


def validate_positive_quantity(quantity: int) -> None:
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Aantal moet groter zijn dan 0")


def add_inventory_movement(
    db: Session,
    inventory: ProductInventory,
    movement_type: str,
    quantity: int,
    *,
    before: dict[str, int] | None = None,
    order_id: int | None = None,
    order_item_id: int | None = None,
    print_job_id: int | None = None,
    note: str | None = None,
    source: str | None = None,
    reason: str | None = None,
    performed_by: str = "system",
) -> InventoryMovement:
    before = before or inventory_snapshot(inventory)
    after = inventory_snapshot(inventory)
    movement = InventoryMovement(
        product_inventory_id=inventory.id,
        movement_type=movement_type,
        quantity=quantity,
        order_id=order_id,
        order_item_id=order_item_id,
        print_job_id=print_job_id,
        note=note,
        quantity_on_hand_before=before["quantity_on_hand"],
        quantity_on_hand_after=after["quantity_on_hand"],
        quantity_reserved_before=before["quantity_reserved"],
        quantity_reserved_after=after["quantity_reserved"],
        free_stock_before=before["free_stock"],
        free_stock_after=after["free_stock"],
        source=source,
        reason=reason or note,
        performed_by=performed_by,
    )
    db.add(movement)
    return movement


def process_order_inventory(db: Session, order: Order) -> dict:
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    results = []

    for item in items:
        link_order_item_by_sku(db, item)
        result = process_order_item_inventory(db, item)
        results.append(result)

    statuses = {result["inventory_status"] for result in results}
    if not results:
        order.status = ORDER_NEW
    elif statuses == {INVENTORY_FULL}:
        order.status = ORDER_FULLY_FROM_INVENTORY
    elif INVENTORY_PARTIAL in statuses:
        order.status = ORDER_PARTLY_TO_PRINT
    elif statuses == {INVENTORY_NONE}:
        order.status = ORDER_FULLY_TO_PRINT
    else:
        order.status = ORDER_PARTLY_TO_PRINT

    db.commit()
    return {"status": "processed", "order": to_dict(order), "items": results}


def process_order_item_inventory(db: Session, item: OrderItem) -> dict:
    if not item.product_id or not item.product_variant_id:
        item.quantity_from_inventory = 0
        item.quantity_to_print = item.quantity_ordered
        item.inventory_status = INVENTORY_NONE
        return to_dict(item)

    inventory = db.scalar(
        select(ProductInventory).where(
            ProductInventory.product_id == item.product_id,
            ProductInventory.product_variant_id == item.product_variant_id,
        )
    )
    if not inventory:
        item.quantity_from_inventory = 0
        item.quantity_to_print = item.quantity_ordered
        item.inventory_status = INVENTORY_NONE
        return to_dict(item)

    if item.quantity_from_inventory > 0:
        before = inventory_snapshot(inventory)
        released = min(inventory.quantity_reserved, item.quantity_from_inventory)
        if released > 0:
            inventory.quantity_reserved -= released
            add_inventory_movement(
                db,
                inventory,
                "reservering_vrijgegeven",
                released,
                before=before,
                order_id=item.order_id,
                order_item_id=item.id,
                note="Herberekening ordervoorraad",
                source="order_inventory_recheck",
            )

    free_stock = max(0, inventory.quantity_on_hand - inventory.quantity_reserved)
    reserve_quantity = min(item.quantity_ordered, free_stock)
    quantity_to_print = item.quantity_ordered - reserve_quantity

    if reserve_quantity > 0:
        before = inventory_snapshot(inventory)
        inventory.quantity_reserved += reserve_quantity
        add_inventory_movement(
            db,
            inventory,
            "gereserveerd_voor_order",
            reserve_quantity,
            before=before,
            order_id=item.order_id,
            order_item_id=item.id,
            note="Automatische ordervoorraadcontrole",
            source="order_inventory_check",
        )

    item.quantity_from_inventory = reserve_quantity
    item.quantity_to_print = quantity_to_print
    if reserve_quantity == item.quantity_ordered:
        item.inventory_status = INVENTORY_FULL
    elif reserve_quantity > 0:
        item.inventory_status = INVENTORY_PARTIAL
    else:
        item.inventory_status = INVENTORY_NONE

    data = to_dict(item)
    data["free_stock_before_reservation"] = free_stock
    data["product_inventory_id"] = inventory.id
    return data


def adjust_product_inventory(db: Session, inventory: ProductInventory, quantity: int) -> dict:
    before = inventory_snapshot(inventory)
    new_quantity_on_hand = inventory.quantity_on_hand + quantity
    if new_quantity_on_hand < 0:
        raise HTTPException(status_code=400, detail="Voorraad op hand mag niet negatief worden")
    if new_quantity_on_hand < inventory.quantity_reserved:
        raise HTTPException(status_code=400, detail="Vrije voorraad mag niet negatief worden")
    inventory.quantity_on_hand += quantity
    add_inventory_movement(
        db,
        inventory,
        "correctie",
        quantity,
        before=before,
        source="manual_inventory_adjustment",
        reason="Handmatige voorraadcorrectie",
    )
    db.commit()
    return to_dict(inventory)


def reserve_product_inventory(db: Session, inventory: ProductInventory, quantity: int) -> dict:
    validate_positive_quantity(quantity)
    if inventory.free_stock < quantity:
        raise HTTPException(status_code=400, detail="Niet genoeg vrije voorraad")
    before = inventory_snapshot(inventory)
    inventory.quantity_reserved += quantity
    add_inventory_movement(
        db,
        inventory,
        "gereserveerd_voor_order",
        quantity,
        before=before,
        source="manual_inventory_reservation",
        reason="Handmatige reservering",
    )
    db.commit()
    return to_dict(inventory)


def release_product_inventory(db: Session, inventory: ProductInventory, quantity: int) -> dict:
    validate_positive_quantity(quantity)
    before = inventory_snapshot(inventory)
    inventory.quantity_reserved = max(0, inventory.quantity_reserved - quantity)
    released = before["quantity_reserved"] - inventory.quantity_reserved
    add_inventory_movement(
        db,
        inventory,
        "reservering_vrijgegeven",
        released,
        before=before,
        source="manual_inventory_release",
        reason="Handmatige reservering vrijgegeven",
    )
    db.commit()
    return to_dict(inventory)

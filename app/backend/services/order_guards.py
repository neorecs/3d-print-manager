from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.statuses import (
    ORDER_NEW, ORDER_CHECKED, ORDER_FULLY_FROM_INVENTORY, ORDER_PARTLY_TO_PRINT,
    ORDER_FULLY_TO_PRINT, ORDER_PLANNED, PRINT_JOB_NEW, PRINT_JOB_PLANNED,
)
from models import Order, OrderItem, PrintJob


def require_reprocessable_order(db: Session, order_id: int) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update().execution_options(populate_existing=True))
    if not order:
        raise HTTPException(404, "Order niet gevonden")
    if order.status not in {
        ORDER_NEW, ORDER_CHECKED, ORDER_FULLY_FROM_INVENTORY, ORDER_PARTLY_TO_PRINT,
        ORDER_FULLY_TO_PRINT, ORDER_PLANNED,
    }:
        raise HTTPException(409, "Deze order is al verder verwerkt of afgesloten. Gebruik een gerichte correctie.")
    started = db.scalar(
        select(PrintJob.id).join(OrderItem, PrintJob.order_item_id == OrderItem.id)
        .where(OrderItem.order_id == order_id, PrintJob.status.notin_([PRINT_JOB_NEW, PRINT_JOB_PLANNED]))
    )
    if started:
        raise HTTPException(409, "Er is al printwerk gestart of verwerkt. De reservering en printtaken worden niet opnieuw berekend.")
    return order

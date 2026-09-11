from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.utils import to_dict
from domain.statuses import ORDER_PLANNED, PRINT_JOB_NEW
from inventory.service import link_order_item_by_sku, process_order_inventory
from models import OrderItem, PrintJob, PrintBatchItem, ProductVariant
from services.accounting_service import create_accounting_sale_from_order
from services.order_guards import require_reprocessable_order


def sync_print_jobs(db: Session, order_id: int) -> dict:
    order = require_reprocessable_order(db, order_id)
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.id).with_for_update()).all()
    created, updated, removed = [], [], []
    for item in items:
        jobs = db.scalars(select(PrintJob).where(PrintJob.order_item_id == item.id).with_for_update()).all()
        if len(jobs) > 1:
            raise HTTPException(409, "Deze orderregel heeft meerdere printtaken. Controleer de printplanning.")
        job = jobs[0] if jobs else None
        if item.quantity_to_print < 0:
            raise HTTPException(409, "Ongeldig printtekort op de orderregel")
        if job and job.quantity_needed != item.quantity_to_print:
            in_batch = db.scalar(select(PrintBatchItem.id).where(PrintBatchItem.print_job_id == job.id))
            if in_batch or job.bambu_studio_opened_at:
                raise HTTPException(409, "Printwerk is al gebundeld of aangeboden aan Studio. Controleer de planning voordat je aantallen wijzigt.")
        if not item.quantity_to_print:
            if job:
                item.print_job_id = None
                db.flush()
                extra = max(0, job.quantity_planned - job.quantity_needed)
                if extra:
                    variant = db.get(ProductVariant, job.product_variant_id)
                    job.order_item_id = None
                    job.quantity_needed = 0
                    job.quantity_planned = extra
                    job.quantity_to_order = 0
                    job.quantity_to_inventory = extra
                    job.estimated_print_time_minutes = int(variant.estimated_print_time_minutes * extra) if variant and variant.estimated_print_time_minutes is not None else None
                    job.estimated_filament_grams = int(variant.estimated_filament_grams * extra) if variant and variant.estimated_filament_grams is not None else None
                else:
                    removed.append(job.id)
                    db.delete(job)
            continue
        variant = db.get(ProductVariant, item.product_variant_id)
        if not variant or variant.product_id != item.product_id:
            raise HTTPException(409, f"Orderregel {item.id} heeft geen geldige productvariant")
        if job and (job.product_variant_id != item.product_variant_id or job.product_id != item.product_id):
            raise HTTPException(409, "De bestaande printtaak hoort bij een andere productvariant")
        is_new = job is None
        if is_new:
            job = PrintJob(order_item_id=item.id, product_id=item.product_id,
                           product_variant_id=variant.id, status=PRINT_JOB_NEW,
                           quantity_planned=0, quantity_needed=0)
            db.add(job)
        extra = max(0, job.quantity_planned - job.quantity_needed)
        job.quantity_needed = item.quantity_to_print
        job.quantity_planned = item.quantity_to_print + extra
        job.quantity_to_order = item.quantity_to_print
        job.quantity_to_inventory = extra
        job.color, job.material = variant.color, variant.material
        job.estimated_print_time_minutes = int(variant.estimated_print_time_minutes * job.quantity_planned) if variant.estimated_print_time_minutes is not None else None
        job.estimated_filament_grams = int(variant.estimated_filament_grams * job.quantity_planned) if variant.estimated_filament_grams is not None else None
        db.flush()
        item.print_job_id = job.id
        (created if is_new else updated).append(to_dict(job))
    if created or updated:
        order.status = ORDER_PLANNED
    db.flush()
    return {"status": "created", "created": created, "updated": updated, "removed": removed}


def process_order(db: Session, order_id: int, *, include_accounting: bool = True) -> dict:
    """One transaction, safe to retry after a lost response or legacy partial processing."""
    try:
        order = require_reprocessable_order(db, order_id)
        items = db.scalars(select(OrderItem).where(OrderItem.order_id == order_id).with_for_update()).all()
        if not items:
            raise HTTPException(409, "De order heeft nog geen orderregels")
        for item in items:
            link_order_item_by_sku(db, item)
            variant = db.get(ProductVariant, item.product_variant_id) if item.product_variant_id else None
            if not variant or variant.product_id != item.product_id or item.quantity_ordered <= 0:
                raise HTTPException(409, f"Controleer productkoppeling en aantal van orderregel {item.id}")
        db.flush()
        inventory = process_order_inventory(db, order, commit=False)
        jobs = sync_print_jobs(db, order_id)
        sale = create_accounting_sale_from_order(db, order, commit=False) if include_accounting else None
        db.commit()
        return {"status": "processed", "order": to_dict(order), "inventory": inventory,
                "print_jobs": jobs, "accounting_sale": sale,
                "message": "Order verwerkt: voorraad en printplanning zijn bijgewerkt." + (" Verkoopboeking is vastgelegd." if include_accounting else "")}
    except Exception:
        db.rollback()
        raise

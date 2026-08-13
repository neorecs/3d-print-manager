from fastapi import APIRouter
from api.routes_shared import *
from domain.statuses import (
    ORDER_PRINTED,
    PRINT_JOB_FAILED,
    PRINT_JOB_NEW,
    PRINT_JOB_PARTLY_FAILED,
    PRINT_JOB_PLANNED,
    PRINT_JOB_PRINTED,
    PRINT_JOB_PROCESSED,
    RECOMMENDATION_ACCEPTED,
    RECOMMENDATION_ADJUSTED,
    RECOMMENDATION_CONVERTED,
    RECOMMENDATION_IGNORED,
    RECOMMENDATION_NEW,
)
from services.bambu_studio_service import batch_export_download_response, export_print_batch_for_bambu_studio

router = APIRouter()

@router.get("/print-jobs")
def list_print_jobs(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(PrintJob).order_by(PrintJob.id)).all())


@router.post("/print-jobs")
def create_print_job(payload: PrintJobCreate, db: Session = Depends(get_db)):
    item = PrintJob(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.put("/print-jobs/{item_id}")
def update_print_job(item_id: int, payload: PrintJobCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, PrintJob, item_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    return to_dict(item)


@router.post("/print-jobs/{item_id}/complete")
def complete_print_job(item_id: int, payload: PrintJobComplete, db: Session = Depends(get_db)):
    item = get_or_404(db, PrintJob, item_id)
    if payload.quantity_succeeded < 0 or payload.quantity_failed < 0:
        raise HTTPException(status_code=400, detail="Aantallen mogen niet negatief zijn")

    quantity_to_order = payload.quantity_to_order
    if quantity_to_order is None:
        quantity_to_order = min(payload.quantity_succeeded, item.quantity_needed)
    if quantity_to_order > payload.quantity_succeeded:
        raise HTTPException(status_code=400, detail="Aantal naar order kan niet hoger zijn dan aantal gelukt")

    already_processed = item.status in {PRINT_JOB_PRINTED, PRINT_JOB_PARTLY_FAILED, PRINT_JOB_FAILED, PRINT_JOB_PROCESSED}
    previous_to_inventory = item.quantity_to_inventory if already_processed else 0
    previous_failed = item.quantity_failed if already_processed else 0
    item.quantity_succeeded = payload.quantity_succeeded
    item.quantity_failed = payload.quantity_failed
    item.quantity_to_order = quantity_to_order
    item.quantity_to_inventory = max(0, payload.quantity_succeeded - quantity_to_order)
    if payload.quantity_succeeded == 0 and payload.quantity_failed > 0:
        item.status = PRINT_JOB_FAILED
    elif payload.quantity_failed > 0:
        item.status = PRINT_JOB_PARTLY_FAILED
    else:
        item.status = PRINT_JOB_PRINTED

    inventory = ensure_product_inventory_for_print_job(db, item)
    inventory_delta = item.quantity_to_inventory - previous_to_inventory
    failed_delta = item.quantity_failed - previous_failed

    if inventory_delta != 0:
        before = inventory_snapshot(inventory)
        inventory.quantity_on_hand = max(0, inventory.quantity_on_hand + inventory_delta)
        add_inventory_movement(
            db,
            inventory,
            "print_gereed" if inventory_delta > 0 else "correctie",
            inventory_delta,
            before=before,
            order_id=get_order_id_for_print_job(db, item),
            order_item_id=item.order_item_id,
            print_job_id=item.id,
            note="Extra gelukte prints naar vrije voorraad" if inventory_delta > 0 else "Printresultaat gecorrigeerd",
            source="print_result",
        )
    if failed_delta != 0:
        before = inventory_snapshot(inventory)
        add_inventory_movement(
            db,
            inventory,
            "afgekeurd" if failed_delta > 0 else "correctie",
            failed_delta,
            before=before,
            order_id=get_order_id_for_print_job(db, item),
            order_item_id=item.order_item_id,
            print_job_id=item.id,
            note="Mislukte prints geregistreerd" if failed_delta > 0 else "Mislukte prints gecorrigeerd",
            source="print_result",
        )

    update_order_status_after_print(db, item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


def ensure_product_inventory_for_print_job(db: Session, print_job: PrintJob) -> ProductInventory:
    inventory = db.scalar(
        select(ProductInventory).where(
            ProductInventory.product_id == print_job.product_id,
            ProductInventory.product_variant_id == print_job.product_variant_id,
        )
    )
    if inventory:
        return inventory

    inventory = ProductInventory(
        product_id=print_job.product_id,
        product_variant_id=print_job.product_variant_id,
        color=print_job.color,
        material=print_job.material,
        quantity_on_hand=0,
        quantity_reserved=0,
        minimum_stock_level=0,
        location="Automatisch",
    )
    db.add(inventory)
    db.flush()
    return inventory


def get_order_id_for_print_job(db: Session, print_job: PrintJob) -> int | None:
    if not print_job.order_item_id:
        return None
    order_item = db.get(OrderItem, print_job.order_item_id)
    return order_item.order_id if order_item else None


def update_order_status_after_print(db: Session, print_job: PrintJob) -> None:
    order_id = get_order_id_for_print_job(db, print_job)
    if not order_id:
        return
    order = db.get(Order, order_id)
    if not order:
        return
    jobs = db.scalars(
        select(PrintJob)
        .join(OrderItem, PrintJob.order_item_id == OrderItem.id)
        .where(OrderItem.order_id == order_id)
    ).all()
    if jobs and all(job.status in {PRINT_JOB_PRINTED, PRINT_JOB_PARTLY_FAILED} for job in jobs):
        order.status = ORDER_PRINTED


@router.get("/print-batches")
def list_print_batches(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(PrintBatch).order_by(PrintBatch.id)).all())


@router.get("/planning/batch-suggestions")
@router.get("/print-batches/suggestions")
def suggest_print_batches(db: Session = Depends(get_db)):
    jobs = db.scalars(
        select(PrintJob)
        .where(PrintJob.status.in_([PRINT_JOB_NEW, PRINT_JOB_PLANNED]))
        .order_by(PrintJob.material, PrintJob.color, PrintJob.id)
    ).all()
    groups: dict[tuple[str, str], dict] = {}

    for job in jobs:
        material = job.material or "onbekend"
        color = job.color or "onbekend"
        key = (material, color)
        group = groups.setdefault(
            key,
            {
                "suggestion_key": f"{material}|{color}",
                "batch_name": f"{material} - {color}",
                "material": material,
                "color": color,
                "print_job_ids": [],
                "job_count": 0,
                "quantity_needed": 0,
                "quantity_planned": 0,
                "quantity_to_order": 0,
                "quantity_to_inventory": 0,
                "estimated_total_print_time_minutes": 0,
                "estimated_total_filament_grams": 0,
                "products": [],
                "reason": "",
                "priority_score": 0,
            },
        )
        product = db.get(Product, job.product_id)
        variant = db.get(ProductVariant, job.product_variant_id)
        quantity_planned = job.quantity_planned or job.quantity_needed
        quantity_to_order = min(job.quantity_to_order or job.quantity_needed, quantity_planned)
        quantity_to_inventory = max(0, quantity_planned - quantity_to_order)

        group["print_job_ids"].append(job.id)
        group["job_count"] += 1
        group["quantity_needed"] += job.quantity_needed
        group["quantity_planned"] += quantity_planned
        group["quantity_to_order"] += quantity_to_order
        group["quantity_to_inventory"] += quantity_to_inventory
        group["estimated_total_print_time_minutes"] += job.estimated_print_time_minutes or 0
        group["estimated_total_filament_grams"] += job.estimated_filament_grams or 0
        group["products"].append(
            {
                "print_job_id": job.id,
                "product": product.name if product else "",
                "variant": variant.variant_name if variant else "",
                "sku": variant.sku if variant else "",
                "quantity_planned": quantity_planned,
                "quantity_to_order": quantity_to_order,
                "quantity_to_inventory": quantity_to_inventory,
                "print_file_path": product.print_file_path if product and product.print_file_path else (variant.print_file_path if variant else ""),
            }
        )

    suggestions = []
    for group in groups.values():
        group["priority_score"] = (
            group["quantity_to_order"] * 3
            + group["quantity_to_inventory"]
            + round((group["estimated_total_print_time_minutes"] or 0) / 60, 2)
        )
        group["reason"] = (
            f"{group['job_count']} printtaken met hetzelfde materiaal en dezelfde kleur. "
            f"{group['quantity_to_order']} stuks voor orders, "
            f"{group['quantity_to_inventory']} stuks voor vrije voorraad."
        )
        suggestions.append(group)

    return sorted(suggestions, key=lambda item: (-item["priority_score"], item["material"], item["color"]))


@router.post("/print-batches")
def create_print_batch(payload: PrintBatchCreate, db: Session = Depends(get_db)):
    item = PrintBatch(
        batch_name=payload.batch_name,
        planned_date=date.fromisoformat(payload.planned_date) if payload.planned_date else None,
        material=payload.material,
        color=payload.color,
        status=PRINT_JOB_PLANNED,
    )
    db.add(item)
    db.flush()

    total_time = 0
    total_filament = 0
    for print_job_id in payload.print_job_ids:
        job = get_or_404(db, PrintJob, print_job_id)
        quantity = job.quantity_planned or job.quantity_needed
        db.add(PrintBatchItem(print_batch_id=item.id, print_job_id=job.id, quantity_in_batch=quantity))
        total_time += job.estimated_print_time_minutes or 0
        total_filament += job.estimated_filament_grams or 0
        if item.material is None:
            item.material = job.material
        if item.color is None:
            item.color = job.color

    item.estimated_total_print_time_minutes = total_time
    item.estimated_total_filament_grams = total_filament
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/print-batches/{item_id}")
def get_print_batch(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, PrintBatch, item_id)
    data = to_dict(item)
    batch_items = db.scalars(select(PrintBatchItem).where(PrintBatchItem.print_batch_id == item_id)).all()
    data["items"] = list_rows(batch_items)
    return data


@router.post("/print-batches/{item_id}/export")
def export_print_batch(item_id: int, db: Session = Depends(get_db)):
    batch = get_or_404(db, PrintBatch, item_id)
    return export_print_batch_for_bambu_studio(db, batch)


@router.get("/print-batches/{item_id}/export/download")
def download_print_batch_export(item_id: int, db: Session = Depends(get_db)):
    batch = get_or_404(db, PrintBatch, item_id)
    return batch_export_download_response(db, batch)


@router.get("/analytics/sales-trends")
def sales_trends(period_days: int = 30, db: Session = Depends(get_db)):
    rows = build_sales_analysis(db, period_days)
    snapshots = []
    for row in rows:
        snapshots.append(
            {
                "product_id": row["product_id"],
                "product_variant_id": row["product_variant_id"],
                "product": row["product"],
                "variant": row["variant"],
                "period_days": period_days,
                "quantity_sold": row["quantity_sold"],
                "average_weekly_sales": row["average_weekly_sales"],
                "revenue": row["revenue"],
                "estimated_profit": row["estimated_profit"],
            }
        )
    return snapshots


@router.get("/analytics/top-products")
def top_products(period_days: int = 30, db: Session = Depends(get_db)):
    rows = build_sales_analysis(db, period_days)
    grouped = {}
    for row in rows:
        key = row["product_id"]
        item = grouped.setdefault(
            key,
            {
                "product_id": row["product_id"],
                "product": row["product"],
                "quantity_sold": 0,
                "revenue": 0.0,
                "estimated_profit": 0.0,
            },
        )
        item["quantity_sold"] += row["quantity_sold"]
        item["revenue"] += row["revenue"]
        item["estimated_profit"] += row["estimated_profit"]
    return sorted(grouped.values(), key=lambda item: item["quantity_sold"], reverse=True)


@router.get("/analytics/top-colors")
def top_colors(period_days: int = 30, db: Session = Depends(get_db)):
    return group_sales_dimension(db, period_days, "color")


@router.get("/analytics/top-materials")
def top_materials(period_days: int = 30, db: Session = Depends(get_db)):
    return group_sales_dimension(db, period_days, "material")


def build_sales_analysis(db: Session, period_days: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
    order_items = db.scalars(
        select(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.order_date.is_(None) | (Order.order_date >= cutoff))
    ).all()
    grouped = {}
    for item in order_items:
        if not item.product_id or not item.product_variant_id:
            continue
        product = db.get(Product, item.product_id)
        variant = db.get(ProductVariant, item.product_variant_id)
        if not product or not variant:
            continue
        key = (item.product_id, item.product_variant_id)
        row = grouped.setdefault(
            key,
            {
                "product_id": item.product_id,
                "product_variant_id": item.product_variant_id,
                "product": product.name,
                "variant": variant.variant_name,
                "color": variant.color,
                "material": variant.material,
                "quantity_sold": 0,
                "revenue": 0.0,
                "estimated_profit": 0.0,
            },
        )
        revenue = float(item.unit_sale_price or variant.default_sale_price or 0) * item.quantity_ordered
        row["quantity_sold"] += item.quantity_ordered
        row["revenue"] += revenue
        row["estimated_profit"] += estimate_item_profit(db, item, variant, revenue)

    for row in grouped.values():
        row["revenue"] = round(row["revenue"], 2)
        row["estimated_profit"] = round(row["estimated_profit"], 2)
        row["average_weekly_sales"] = round(row["quantity_sold"] / max(period_days / 7, 1), 2)
    return sorted(grouped.values(), key=lambda item: item["quantity_sold"], reverse=True)


def estimate_item_profit(db: Session, item: OrderItem, variant: ProductVariant, revenue: float) -> float:
    grams = float(variant.estimated_filament_grams or 0) * item.quantity_ordered
    filament_cost = grams * get_filament_price_per_gram(db, variant.material, variant.color)
    variant_cost = float(variant.cost_price or 0) * item.quantity_ordered
    return revenue - filament_cost - variant_cost


def group_sales_dimension(db: Session, period_days: int, dimension: str) -> list[dict]:
    rows = build_sales_analysis(db, period_days)
    grouped = {}
    for row in rows:
        key = row.get(dimension) or "onbekend"
        item = grouped.setdefault(
            key,
            {
                dimension: key,
                "quantity_sold": 0,
                "revenue": 0.0,
                "estimated_profit": 0.0,
            },
        )
        item["quantity_sold"] += row["quantity_sold"]
        item["revenue"] += row["revenue"]
        item["estimated_profit"] += row["estimated_profit"]
    for item in grouped.values():
        item["revenue"] = round(item["revenue"], 2)
        item["estimated_profit"] = round(item["estimated_profit"], 2)
    return sorted(grouped.values(), key=lambda item: item["quantity_sold"], reverse=True)


@router.get("/stock-recommendations")
def list_stock_recommendations(db: Session = Depends(get_db)):
    rows = []
    for item in db.scalars(select(StockRecommendation).order_by(StockRecommendation.id.desc())).all():
        data = to_dict(item)
        product = db.get(Product, item.product_id)
        variant = db.get(ProductVariant, item.product_variant_id)
        data["product"] = product.name if product else "-"
        data["variant"] = variant.variant_name if variant else "-"
        data["sku"] = variant.sku if variant else "-"
        data["color"] = variant.color if variant else "-"
        data["material"] = variant.material if variant else "-"
        rows.append(data)
    return rows


@router.post("/stock-recommendations/generate")
def generate_stock_recommendations(payload: StockRecommendationGenerate | None = None, db: Session = Depends(get_db)):
    payload = payload or StockRecommendationGenerate()
    rows = build_sales_analysis(db, payload.period_days)
    generated = []
    updated = []

    for row in rows:
        current_free_stock = get_free_stock_for_variant(db, row["product_id"], row["product_variant_id"])
        expected_sales = int(round(row["average_weekly_sales"] * payload.weeks_ahead))
        recommended_stock_level = expected_sales + payload.safety_stock
        recommended_print_quantity = max(0, recommended_stock_level - current_free_stock)
        if recommended_print_quantity <= 0:
            continue

        reason = (
            f"Gemiddelde weekverkoop {row['average_weekly_sales']} x {payload.weeks_ahead} week/weken "
            f"= {expected_sales}, plus veiligheidsvoorraad {payload.safety_stock}, "
            f"min vrije voorraad {current_free_stock}."
        )
        existing = db.scalar(
            select(StockRecommendation).where(
                StockRecommendation.product_id == row["product_id"],
                StockRecommendation.product_variant_id == row["product_variant_id"],
                StockRecommendation.status.in_([RECOMMENDATION_NEW, RECOMMENDATION_ADJUSTED]),
            )
        )
        if existing:
            existing.current_free_stock = current_free_stock
            existing.expected_sales = expected_sales
            existing.safety_stock = payload.safety_stock
            existing.recommended_stock_level = recommended_stock_level
            existing.recommended_print_quantity = recommended_print_quantity
            existing.reason = reason
            updated.append(existing)
        else:
            existing = StockRecommendation(
                product_id=row["product_id"],
                product_variant_id=row["product_variant_id"],
                current_free_stock=current_free_stock,
                expected_sales=expected_sales,
                safety_stock=payload.safety_stock,
                recommended_stock_level=recommended_stock_level,
                recommended_print_quantity=recommended_print_quantity,
                reason=reason,
                status=RECOMMENDATION_NEW,
            )
            db.add(existing)
            generated.append(existing)

    db.commit()
    return {
        "status": "generated",
        "generated_count": len(generated),
        "updated_count": len(updated),
        "recommendations": list_stock_recommendations(db),
    }


def get_free_stock_for_variant(db: Session, product_id: int, product_variant_id: int) -> int:
    inventory = db.scalar(
        select(ProductInventory).where(
            ProductInventory.product_id == product_id,
            ProductInventory.product_variant_id == product_variant_id,
        )
    )
    return inventory.free_stock if inventory else 0


@router.post("/stock-recommendations/{item_id}/accept")
def accept_stock_recommendation(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, StockRecommendation, item_id)
    item.status = RECOMMENDATION_ACCEPTED
    db.commit()
    return to_dict(item)


@router.put("/stock-recommendations/{item_id}")
def update_stock_recommendation(item_id: int, payload: StockRecommendationUpdate, db: Session = Depends(get_db)):
    item = get_or_404(db, StockRecommendation, item_id)
    if payload.safety_stock < 0 or payload.recommended_print_quantity < 0:
        raise HTTPException(status_code=400, detail="Aantallen mogen niet negatief zijn")
    item.safety_stock = payload.safety_stock
    item.recommended_print_quantity = payload.recommended_print_quantity
    item.recommended_stock_level = item.current_free_stock + payload.recommended_print_quantity
    explanation = payload.reason or "Handmatig aangepast door gebruiker."
    item.reason = (
        f"{explanation} Advies aangepast naar {payload.recommended_print_quantity} extra printen "
        f"met veiligheidsvoorraad {payload.safety_stock}."
    )
    item.status = RECOMMENDATION_ADJUSTED
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.post("/stock-recommendations/{item_id}/ignore")
def ignore_stock_recommendation(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, StockRecommendation, item_id)
    item.status = RECOMMENDATION_IGNORED
    db.commit()
    return to_dict(item)


@router.post("/stock-recommendations/{item_id}/convert-to-print-job")
def convert_stock_recommendation(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, StockRecommendation, item_id)
    variant = db.get(ProductVariant, item.product_variant_id)
    print_job = PrintJob(
        product_id=item.product_id,
        product_variant_id=item.product_variant_id,
        color=variant.color if variant else None,
        material=variant.material if variant else None,
        quantity_needed=item.recommended_print_quantity,
        quantity_planned=item.recommended_print_quantity,
        quantity_to_order=0,
        quantity_to_inventory=item.recommended_print_quantity,
        estimated_print_time_minutes=int((variant.estimated_print_time_minutes or 0) * item.recommended_print_quantity)
        if variant
        else None,
        estimated_filament_grams=int((variant.estimated_filament_grams or 0) * item.recommended_print_quantity)
        if variant
        else None,
        status=PRINT_JOB_NEW,
    )
    item.status = RECOMMENDATION_CONVERTED
    db.add(print_job)
    db.commit()
    db.refresh(print_job)
    return to_dict(print_job)


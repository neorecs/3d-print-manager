from fastapi import APIRouter
from api.routes_shared import *
from domain.statuses import INVENTORY_NONE, ORDER_NEW, ORDER_PLANNED, PRINT_JOB_NEW

router = APIRouter()

@router.get("/orders")
def list_orders(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(Order).order_by(Order.id)).all())


@router.post("/orders")
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    item = Order(**order_payload(payload))
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/orders/{item_id}")
def get_order(item_id: int, db: Session = Depends(get_db)):
    order = get_or_404(db, Order, item_id)
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == item_id)).all()
    data = to_dict(order)
    data["items"] = list_rows(items)
    return data


@router.put("/orders/{item_id}")
def update_order(item_id: int, payload: OrderCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, Order, item_id)
    for key, value in order_payload(payload).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return to_dict(item)


def order_payload(payload: OrderCreate) -> dict:
    data = payload.model_dump()
    if data.get("order_date"):
        data["order_date"] = datetime.fromisoformat(data["order_date"].replace("Z", "+00:00"))
    else:
        data["order_date"] = None
    return data


@router.get("/order-items")
def list_order_items(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(OrderItem).order_by(OrderItem.id)).all())


@router.post("/order-items")
def create_order_item(payload: OrderItemCreate, db: Session = Depends(get_db)):
    item = OrderItem(**payload.model_dump())
    link_order_item_by_sku(db, item)
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.put("/order-items/{item_id}")
def update_order_item(item_id: int, payload: OrderItemCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, OrderItem, item_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    link_order_item_by_sku(db, item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.post("/orders/import/etsy")
def import_etsy_orders(
    since: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    since_dt = parse_optional_datetime(since) if since else None
    platforms = db.scalars(select(Platform).where(Platform.type == "etsy", Platform.active.is_(True)).order_by(Platform.id)).all()
    if not platforms:
        order = create_dummy_order(db, platform_type="etsy")
        return {"status": "dummy_etsy_import_complete", "created": 1, "updated": 0, "skipped": 0, "orders": [to_dict(order)]}

    created = []
    updated = []
    skipped = []
    errors = []
    for platform in platforms:
        connector = get_platform_connector(db, platform)
        status = connector.status()
        if connector.live_mode and status.missing_credentials:
            errors.append({"platform_id": platform.id, "platform": platform.name, "message": f"Ontbrekende Etsy credentials: {', '.join(status.missing_credentials)}"})
            continue
        result = connector.import_orders(limit=limit, since=since_dt.isoformat() if since_dt else None)
        if not result.get("success"):
            errors.append({"platform_id": platform.id, "platform": platform.name, "message": result.get("message", "Etsy import mislukt")})
            continue
        for payload in result.get("orders", []):
            imported = upsert_imported_order(db, platform, payload)
            if imported["action"] == "created":
                created.append(imported["order"])
            elif imported["action"] == "updated":
                updated.append(imported["order"])
            else:
                skipped.append(imported["order"])

    db.commit()
    return {
        "status": "etsy_import_complete" if not errors else "etsy_import_completed_with_errors",
        "created": len(created),
        "updated": len(updated),
        "skipped": len(skipped),
        "errors": errors,
        "orders": created + updated + skipped,
    }


@router.post("/orders/import/shopify")
def import_shopify_orders(
    since: str | None = Query(None),
    limit: int = Query(100, ge=1, le=250),
    page_size: int = Query(50, ge=1, le=50),
    db: Session = Depends(get_db),
):
    since_dt = parse_optional_datetime(since) if since else None
    platforms = db.scalars(select(Platform).where(Platform.type == "shopify", Platform.active.is_(True)).order_by(Platform.id)).all()
    if not platforms:
        order = create_dummy_order(db, platform_type="shopify")
        return {"status": "dummy_shopify_import_complete", "created": 1, "updated": 0, "skipped": 0, "orders": [to_dict(order)]}

    created = []
    updated = []
    skipped = []
    errors = []

    for platform in platforms:
        log = PlatformImportLog(
            platform_id=platform.id,
            import_type="orders",
            status="bezig",
            started_at=datetime.now(timezone.utc),
            since=since_dt,
        )
        db.add(log)
        db.flush()
        platform_created = 0
        platform_updated = 0
        platform_skipped = 0
        platform_errors = []
        connector = get_platform_connector(db, platform)
        status = connector.status()
        if connector.live_mode and status.missing_credentials:
            error = {"platform_id": platform.id, "platform": platform.name, "message": f"Ontbrekende Shopify credentials: {', '.join(status.missing_credentials)}"}
            errors.append(error)
            platform_errors.append(error["message"])
            finish_import_log(log, "fout", platform_created, platform_updated, platform_skipped, platform_errors)
            continue
        result = connector.import_orders(limit=limit, since=since_dt.isoformat() if since_dt else None, page_size=page_size)
        if not result.get("success"):
            error = {"platform_id": platform.id, "platform": platform.name, "message": result.get("message", "Shopify import mislukt")}
            errors.append(error)
            platform_errors.append(error["message"])
            finish_import_log(log, "fout", platform_created, platform_updated, platform_skipped, platform_errors)
            continue
        for payload in result.get("orders", []):
            imported = upsert_imported_order(db, platform, payload)
            if imported["action"] == "created":
                created.append(imported["order"])
                platform_created += 1
            elif imported["action"] == "updated":
                updated.append(imported["order"])
                platform_updated += 1
            else:
                skipped.append(imported["order"])
                platform_skipped += 1
        platform_message = result.get("message") or ""
        if result.get("has_next_page"):
            platform_message = f"{platform_message} Importlimiet bereikt; er zijn mogelijk nog meer Shopify orders."
        finish_import_log(log, "klaar", platform_created, platform_updated, platform_skipped, platform_errors, platform_message)

    db.commit()
    return {
        "status": "shopify_import_complete" if not errors else "shopify_import_completed_with_errors",
        "created": len(created),
        "updated": len(updated),
        "skipped": len(skipped),
        "errors": errors,
        "orders": created + updated + skipped,
    }


@router.get("/orders/import-logs")
def list_order_import_logs(db: Session = Depends(get_db)):
    rows = db.scalars(select(PlatformImportLog).where(PlatformImportLog.import_type == "orders").order_by(PlatformImportLog.started_at.desc().nullslast(), PlatformImportLog.id.desc()).limit(20)).all()
    return list_rows(rows)


def finish_import_log(
    log: PlatformImportLog,
    status: str,
    created_count: int,
    updated_count: int,
    skipped_count: int,
    errors: list[str],
    message: str | None = None,
) -> None:
    log.status = status
    log.finished_at = datetime.now(timezone.utc)
    log.created_count = created_count
    log.updated_count = updated_count
    log.skipped_count = skipped_count
    log.error_count = len(errors)
    default_message = f"{created_count} nieuw, {updated_count} bijgewerkt, {skipped_count} overgeslagen"
    if errors:
        log.message = "; ".join(errors)
    elif message:
        log.message = f"{default_message}. {message}".strip()
    else:
        log.message = default_message


def upsert_imported_order(db: Session, platform: Platform, payload: dict) -> dict:
    external_order_id = payload.get("external_order_id")
    if not external_order_id:
        return {"action": "skipped", "order": {"reason": "Order zonder external_order_id overgeslagen"}}

    order = db.scalar(select(Order).where(Order.platform_id == platform.id, Order.external_order_id == external_order_id))
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

    for item_payload in payload.get("items", []):
        external_item_id = item_payload.get("external_order_item_id")
        if not external_item_id:
            continue
        item = db.scalar(select(OrderItem).where(OrderItem.order_id == order.id, OrderItem.external_order_item_id == external_item_id))
        if not item:
            item = OrderItem(order_id=order.id, external_order_item_id=external_item_id, quantity_ordered=0)
            db.add(item)
        item.sku = item_payload.get("sku")
        item.quantity_ordered = int(item_payload.get("quantity_ordered") or 0)
        item.unit_sale_price = item_payload.get("unit_sale_price")
        item.inventory_status = item.inventory_status or INVENTORY_NONE
        link_order_item_by_sku(db, item)

    return {"action": action, "order": to_dict(order)}


def parse_optional_datetime(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def create_dummy_order(db: Session, platform_type: str) -> Order:
    seed_dummy_data(db)
    platform = db.scalar(select(Platform).where(Platform.type == platform_type).order_by(Platform.id))
    variant = db.scalar(select(ProductVariant).order_by(ProductVariant.id))
    if not platform or not variant:
        raise HTTPException(status_code=400, detail="Dummydata mist platform of productvariant")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    order = Order(
        internal_order_number=f"{platform_type.upper()}-{timestamp}",
        platform_id=platform.id,
        external_order_id=f"{platform_type.upper()}-DEMO-{timestamp}",
        customer_name=f"Demo {platform.name} klant",
        customer_email=f"demo-{platform_type}@example.com",
        order_date=datetime.now(timezone.utc),
        total_amount=19.90,
        currency="EUR",
        status=ORDER_NEW,
    )
    db.add(order)
    db.flush()

    item = OrderItem(
        order_id=order.id,
        external_order_item_id=f"{platform_type.upper()}-LINE-{timestamp}",
        sku=variant.sku,
        quantity_ordered=2,
        unit_sale_price=variant.default_sale_price,
        inventory_status=INVENTORY_NONE,
    )
    link_order_item_by_sku(db, item)
    db.add(item)
    db.commit()
    db.refresh(order)
    return order


@router.post("/orders/{item_id}/link-items")
def link_order_items(item_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Order, item_id)
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == item_id)).all()
    linked = 0
    for item in items:
        before = item.product_variant_id
        link_order_item_by_sku(db, item)
        if item.product_variant_id and item.product_variant_id != before:
            linked += 1
    db.commit()
    return {"status": "linked", "linked_count": linked, "item_count": len(items)}


@router.post("/orders/{item_id}/process-inventory")
def process_order_inventory(item_id: int, db: Session = Depends(get_db)):
    order = get_or_404(db, Order, item_id)
    return process_order_inventory_service(db, order)


@router.post("/orders/{item_id}/create-print-jobs")
def create_print_jobs_for_order(item_id: int, db: Session = Depends(get_db)):
    order = get_or_404(db, Order, item_id)
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == item_id)).all()
    created = []
    updated = []

    for item in items:
        if item.quantity_to_print <= 0:
            continue
        if not item.product_id or not item.product_variant_id:
            link_order_item_by_sku(db, item)
        if not item.product_id or not item.product_variant_id:
            continue

        variant = db.get(ProductVariant, item.product_variant_id)
        existing = db.scalar(select(PrintJob).where(PrintJob.order_item_id == item.id))
        quantity_planned = item.quantity_to_print
        estimated_time = None
        estimated_filament = None
        if variant:
            if variant.estimated_print_time_minutes is not None:
                estimated_time = int(variant.estimated_print_time_minutes * quantity_planned)
            if variant.estimated_filament_grams is not None:
                estimated_filament = int(variant.estimated_filament_grams * quantity_planned)

        if existing:
            existing.quantity_needed = item.quantity_to_print
            existing.quantity_planned = max(existing.quantity_planned, item.quantity_to_print)
            existing.quantity_to_order = item.quantity_to_print
            existing.quantity_to_inventory = max(0, existing.quantity_planned - existing.quantity_to_order)
            existing.estimated_print_time_minutes = estimated_time
            existing.estimated_filament_grams = estimated_filament
            item.print_job_id = existing.id
            updated.append(to_dict(existing))
            continue

        print_job = PrintJob(
            order_item_id=item.id,
            product_id=item.product_id,
            product_variant_id=item.product_variant_id,
            color=variant.color if variant else None,
            material=variant.material if variant else None,
            quantity_needed=item.quantity_to_print,
            quantity_planned=quantity_planned,
            quantity_to_order=item.quantity_to_print,
            quantity_to_inventory=0,
            estimated_print_time_minutes=estimated_time,
            estimated_filament_grams=estimated_filament,
            status=PRINT_JOB_NEW,
        )
        db.add(print_job)
        db.flush()
        item.print_job_id = print_job.id
        created.append(to_dict(print_job))

    if created or updated:
        order.status = ORDER_PLANNED
    db.commit()
    return {"status": "created", "created": created, "updated": updated}


@router.post("/orders/{item_id}/create-accounting-sale")
def create_order_accounting_sale(item_id: int, db: Session = Depends(get_db)):
    order = get_or_404(db, Order, item_id)
    return create_accounting_sale_from_order(db, order)



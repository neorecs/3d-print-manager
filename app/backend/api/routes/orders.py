from fastapi import APIRouter
from api.routes_shared import *
from domain.statuses import INVENTORY_NONE, ORDER_NEW, ORDER_PLANNED, PRINT_JOB_NEW
from sqlalchemy.exc import IntegrityError
from services.order_guards import require_reprocessable_order
from services.order_processing import process_order
from services.order_fulfillment import cancel_order, pack_order, ship_order
from services.order_import_service import upsert_imported_order as upsert_imported_order_service
from services.order_import_runner import finish_import_log, import_platform_orders  # noqa: F401

router = APIRouter()

@router.get("/orders")
def list_orders(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(Order).order_by(Order.id)).all())


@router.post("/orders")
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    item = Order(**order_payload(payload))
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Er bestaat al een order met dit interne of externe ordernummer.") from exc
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
    values = order_payload(payload)
    # Status changes only go through the pack/ship/cancel actions, which also book stock.
    values.pop("status", None)
    for key, value in values.items():
        setattr(item, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="De gewijzigde order botst met een bestaand ordernummer.") from exc
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


def _import_orders_for_type(db: Session, platform_type: str, since: str | None, limit: int, page_size: int = 50) -> dict:
    since_dt = parse_optional_datetime(since) if since else None
    platforms = db.scalars(select(Platform).where(Platform.type == platform_type, Platform.active.is_(True)).order_by(Platform.id)).all()
    if not platforms:
        order = create_dummy_order(db, platform_type=platform_type)
        return {"status": f"dummy_{platform_type}_import_complete", "created": 1, "updated": 0, "skipped": 0, "orders": [to_dict(order)]}

    created, updated, skipped, errors, warnings = [], [], [], [], []
    for platform in platforms:
        summary = import_platform_orders(db, platform, since=since_dt, limit=limit, page_size=page_size)
        created.extend(summary["created"])
        updated.extend(summary["updated"])
        skipped.extend(summary["skipped"])
        warnings.extend(summary["warnings"])
        errors.extend({"platform_id": platform.id, "platform": platform.name, "message": message} for message in summary["errors"])

    label = platform_type.capitalize()
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Een {label}-order is gelijktijdig al geimporteerd. Vernieuw het overzicht.") from exc
    return {
        "status": f"{platform_type}_import_complete" if not errors else f"{platform_type}_import_completed_with_errors",
        "created": len(created),
        "updated": len(updated),
        "skipped": len(skipped),
        "errors": errors,
        "warnings": warnings,
        "orders": created + updated + skipped,
    }


@router.post("/orders/import/etsy")
def import_etsy_orders(
    since: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return _import_orders_for_type(db, "etsy", since, limit)


@router.post("/orders/import/bol")
def import_bol_orders(
    since: str | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return _import_orders_for_type(db, "bol", since, limit)


@router.post("/orders/import/shopify")
def import_shopify_orders(
    since: str | None = Query(None),
    limit: int = Query(100, ge=1, le=250),
    page_size: int = Query(50, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return _import_orders_for_type(db, "shopify", since, limit, page_size)


@router.get("/orders/import-logs")
def list_order_import_logs(db: Session = Depends(get_db)):
    rows = db.scalars(select(PlatformImportLog).where(PlatformImportLog.import_type == "orders").order_by(PlatformImportLog.started_at.desc().nullslast(), PlatformImportLog.id.desc()).limit(20)).all()
    return list_rows(rows)


def upsert_imported_order(db: Session, platform: Platform, payload: dict) -> dict:
    return upsert_imported_order_service(db, platform, payload)


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
    require_reprocessable_order(db, item_id)
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


@router.post("/orders/{item_id}/process")
def process_complete_order(item_id: int, db: Session = Depends(get_db)):
    return process_order(db, item_id)


@router.post("/orders/{item_id}/create-print-jobs")
def create_print_jobs_for_order(item_id: int, db: Session = Depends(get_db)):
    return process_order(db, item_id, include_accounting=False)["print_jobs"]


@router.post("/orders/{item_id}/create-accounting-sale")
def create_order_accounting_sale(item_id: int, db: Session = Depends(get_db)):
    order = get_or_404(db, Order, item_id)
    return create_accounting_sale_from_order(db, order)




def _actor(request: Request) -> str:
    return getattr(request.state, "user_email", None) or "system"


@router.post("/orders/{item_id}/pack")
def pack_order_route(item_id: int, db: Session = Depends(get_db)):
    return pack_order(db, item_id)


@router.post("/orders/{item_id}/ship")
def ship_order_route(item_id: int, request: Request, db: Session = Depends(get_db)):
    return ship_order(db, item_id, performed_by=_actor(request))


@router.post("/orders/{item_id}/cancel")
def cancel_order_route(item_id: int, request: Request, db: Session = Depends(get_db)):
    return cancel_order(db, item_id, performed_by=_actor(request))

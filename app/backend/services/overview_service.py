from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import ceil

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from api.utils import list_rows, to_dict
from domain.statuses import (
    ORDER_CANCELLED,
    ORDER_PACKED,
    ORDER_PARTLY_TO_PRINT,
    ORDER_FULLY_TO_PRINT,
    ORDER_PLANNED,
    ORDER_SHIPPED,
    PRINT_JOB_CANCELLED,
    PRINT_JOB_PROCESSED,
    PUBLICATION_PUBLISHED,
    PUBLICATION_SYNC_NEEDED,
)
from models import (
    BambuPrinter,
    FilamentSpool,
    Order,
    OrderItem,
    Platform,
    PlatformImportLog,
    PrintJob,
    Product,
    ProductInventory,
    ProductPlatformPublication,
    ProductVariant,
)
from services.bambu_printers import public_bambu_printer_dict


def _page(total: int, requested: int, page_size: int) -> tuple[int, int]:
    page_count = max(1, ceil(total / page_size))
    return min(requested, page_count), page_count


def _catalog_condition(view: str):
    archived = or_(Product.active.is_(False), Product.status == "gearchiveerd")
    if view == "archief":
        return archived
    if view == "alle":
        return True
    return and_(Product.active.is_(True), Product.status != "gearchiveerd")


def catalog_overview(db: Session, page: int, page_size: int, view: str) -> dict:
    condition = _catalog_condition(view)
    total = int(db.scalar(select(func.count(Product.id)).where(condition)) or 0)
    page, page_count = _page(total, page, page_size)
    products = db.scalars(
        select(Product).where(condition).order_by(Product.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    product_ids = [item.id for item in products]

    variants = db.scalars(select(ProductVariant).where(ProductVariant.product_id.in_(product_ids)).order_by(ProductVariant.id)).all() if product_ids else []
    inventory = db.scalars(select(ProductInventory).where(ProductInventory.product_id.in_(product_ids)).order_by(ProductInventory.id)).all() if product_ids else []
    publications = db.scalars(select(ProductPlatformPublication).where(ProductPlatformPublication.product_id.in_(product_ids)).order_by(ProductPlatformPublication.id)).all() if product_ids else []

    variants_by_product: dict[int, list] = {product_id: [] for product_id in product_ids}
    inventory_by_product: dict[int, list] = {product_id: [] for product_id in product_ids}
    publications_by_product: dict[int, list] = {product_id: [] for product_id in product_ids}
    for item in variants:
        variants_by_product[item.product_id].append(to_dict(item))
    for item in inventory:
        inventory_by_product[item.product_id].append(to_dict(item))
    for item in publications:
        publications_by_product[item.product_id].append(to_dict(item))

    variant_count = int(db.scalar(select(func.count(ProductVariant.id)).join(Product, Product.id == ProductVariant.product_id).where(condition)) or 0)
    low_stock_count = int(db.scalar(
        select(func.count(func.distinct(ProductInventory.product_id)))
        .join(Product, Product.id == ProductInventory.product_id)
        .where(condition, ProductInventory.quantity_on_hand - ProductInventory.quantity_reserved <= ProductInventory.minimum_stock_level)
    ) or 0)
    published_count = int(db.scalar(
        select(func.count(func.distinct(ProductPlatformPublication.product_id)))
        .join(Product, Product.id == ProductPlatformPublication.product_id)
        .where(condition, ProductPlatformPublication.publication_status == PUBLICATION_PUBLISHED)
    ) or 0)
    difference = func.coalesce(ProductVariant.default_sale_price, 0) - func.coalesce(ProductVariant.cost_price, 0)
    margin_potential = float(db.scalar(
        select(func.coalesce(func.sum(case((difference > 0, difference), else_=0)), 0))
        .select_from(ProductVariant)
        .join(Product, Product.id == ProductVariant.product_id)
        .where(condition)
    ) or 0)

    return {
        "rows": [
            {
                "product": to_dict(product),
                "variants": variants_by_product[product.id],
                "inventory": inventory_by_product[product.id],
                "publications": publications_by_product[product.id],
            }
            for product in products
        ],
        "metrics": {
            "products": total,
            "variants": variant_count,
            "low_stock": low_stock_count,
            "published": published_count,
            "margin_potential": margin_potential,
        },
        "page": page,
        "page_size": page_size,
        "page_count": page_count,
        "total": total,
        "view": view,
    }


def _order_condition(status: str):
    if status == "alle":
        return True
    if status == "betaald":
        return Order.payment_status == "betaald"
    if status == "in-productie":
        return Order.status.in_((ORDER_PARTLY_TO_PRINT, ORDER_FULLY_TO_PRINT, ORDER_PLANNED))
    if status == "klaar":
        return Order.status == ORDER_PACKED
    return Order.status == status


def orders_overview(db: Session, page: int, page_size: int, status: str) -> dict:
    condition = _order_condition(status)
    total = int(db.scalar(select(func.count(Order.id)).where(condition)) or 0)
    page, page_count = _page(total, page, page_size)
    orders = db.scalars(
        select(Order).where(condition).order_by(Order.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    order_ids = [item.id for item in orders]
    items = db.scalars(select(OrderItem).where(OrderItem.order_id.in_(order_ids)).order_by(OrderItem.id)).all() if order_ids else []
    item_ids = [item.id for item in items]
    jobs = db.scalars(select(PrintJob).where(PrintJob.order_item_id.in_(item_ids)).order_by(PrintJob.id)).all() if item_ids else []
    platforms = db.scalars(select(Platform).order_by(Platform.id)).all()
    logs = db.scalars(
        select(PlatformImportLog)
        .where(PlatformImportLog.import_type == "orders")
        .order_by(PlatformImportLog.started_at.desc().nullslast(), PlatformImportLog.id.desc())
        .limit(8)
    ).all()

    metrics_row = db.execute(select(
        func.count(Order.id),
        func.coalesce(func.sum(case((Order.status == "nieuw", 1), else_=0)), 0),
        func.coalesce(func.sum(case((Order.payment_status == "betaald", 1), else_=0)), 0),
        func.coalesce(func.sum(case((Order.status.in_((ORDER_PARTLY_TO_PRINT, ORDER_FULLY_TO_PRINT, ORDER_PLANNED)), 1), else_=0)), 0),
        func.coalesce(func.sum(case((Order.status == ORDER_PACKED, 1), else_=0)), 0),
        func.coalesce(func.sum(case((Order.status == ORDER_SHIPPED, 1), else_=0)), 0),
        func.coalesce(func.sum(case((Order.status == ORDER_CANCELLED, 1), else_=0)), 0),
        func.coalesce(func.sum(Order.total_amount), 0),
    )).one()
    return {
        "orders": list_rows(orders),
        "order_items": list_rows(items),
        "print_jobs": list_rows(jobs),
        "platforms": list_rows(platforms),
        "import_logs": list_rows(logs),
        "metrics": {
            "total": int(metrics_row[0]),
            "new": int(metrics_row[1]),
            "paid": int(metrics_row[2]),
            "production": int(metrics_row[3]),
            "packed": int(metrics_row[4]),
            "shipped": int(metrics_row[5]),
            "cancelled": int(metrics_row[6]),
            "revenue": float(metrics_row[7]),
        },
        "page": page,
        "page_size": page_size,
        "page_count": page_count,
        "total": total,
        "status": status,
    }


def dashboard_overview(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    month_start = today_start.replace(day=1)
    next_month = month_start.replace(year=month_start.year + 1, month=1) if month_start.month == 12 else month_start.replace(month=month_start.month + 1)
    year_start = month_start.replace(month=1)
    next_year = year_start.replace(year=year_start.year + 1)

    order_metrics = db.execute(select(
        func.count(Order.id),
        func.coalesce(func.sum(case((~Order.status.in_((ORDER_SHIPPED, ORDER_CANCELLED, "afgerond")), 1), else_=0)), 0),
        func.coalesce(func.sum(case((and_(Order.order_date >= today_start, Order.order_date < tomorrow_start), 1), else_=0)), 0),
        func.coalesce(func.sum(case((Order.status == "nieuw", 1), else_=0)), 0),
        func.coalesce(func.sum(case((Order.status.in_((ORDER_PARTLY_TO_PRINT, ORDER_FULLY_TO_PRINT, ORDER_PLANNED)), 1), else_=0)), 0),
        func.coalesce(func.sum(case((Order.status == ORDER_PACKED, 1), else_=0)), 0),
        func.coalesce(func.sum(case((Order.status == ORDER_SHIPPED, 1), else_=0)), 0),
        func.coalesce(func.sum(case((Order.status == ORDER_CANCELLED, 1), else_=0)), 0),
        func.coalesce(func.sum(case((and_(Order.order_date >= month_start, Order.order_date < next_month), Order.total_amount), else_=0)), 0),
    )).one()
    month_cases = [
        func.coalesce(func.sum(case((and_(Order.order_date >= year_start.replace(month=month), Order.order_date < (next_year if month == 12 else year_start.replace(month=month + 1))), Order.total_amount), else_=0)), 0)
        for month in range(1, 13)
    ]
    monthly_revenue = [float(value) for value in db.execute(select(*month_cases)).one()]

    free_stock = ProductInventory.quantity_on_hand - ProductInventory.quantity_reserved
    inventory_metrics = db.execute(select(
        func.coalesce(func.sum(free_stock * func.coalesce(ProductVariant.cost_price, 0)), 0),
        func.coalesce(func.sum(case((free_stock <= ProductInventory.minimum_stock_level, 1), else_=0)), 0),
    ).select_from(ProductInventory).join(ProductVariant, ProductVariant.id == ProductInventory.product_variant_id)).one()
    low_inventory_rows = db.execute(
        select(ProductInventory, Product.internal_title, Product.name)
        .join(Product, Product.id == ProductInventory.product_id)
        .where(free_stock <= ProductInventory.minimum_stock_level)
        .order_by(free_stock.asc(), ProductInventory.id)
        .limit(5)
    ).all()

    open_job_condition = ~PrintJob.status.in_((PRINT_JOB_PROCESSED, PRINT_JOB_CANCELLED))
    print_metrics = db.execute(select(
        func.coalesce(func.sum(case((open_job_condition, PrintJob.estimated_print_time_minutes), else_=0)), 0),
        func.coalesce(func.sum(case((open_job_condition, PrintJob.estimated_filament_grams), else_=0)), 0),
    )).one()
    open_jobs = db.scalars(select(PrintJob).where(open_job_condition).order_by(PrintJob.id.desc()).limit(5)).all()

    filament_metrics = db.execute(select(
        func.count(FilamentSpool.id),
        func.coalesce(func.sum(case((and_(FilamentSpool.active.is_(True), FilamentSpool.remaining_weight_grams <= FilamentSpool.minimum_remaining_grams), 1), else_=0)), 0),
        func.count(func.distinct(case((FilamentSpool.active.is_(True), FilamentSpool.color)))),
    )).one()
    sync_needed = int(db.scalar(select(func.count(ProductPlatformPublication.id)).where(ProductPlatformPublication.publication_status == PUBLICATION_SYNC_NEEDED)) or 0)
    top_products = db.execute(
        select(Product.id, Product.internal_title, Product.name, func.sum(OrderItem.quantity_ordered).label("sold"))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.id, Product.internal_title, Product.name)
        .order_by(func.sum(OrderItem.quantity_ordered).desc(), Product.id)
        .limit(5)
    ).all()
    printers = db.scalars(select(BambuPrinter).order_by(BambuPrinter.id)).all()

    return {
        "metrics": {
            "orders_total": int(order_metrics[0]),
            "open_orders": int(order_metrics[1]),
            "orders_today": int(order_metrics[2]),
            "order_new": int(order_metrics[3]),
            "order_production": int(order_metrics[4]),
            "order_packed": int(order_metrics[5]),
            "order_shipped": int(order_metrics[6]),
            "order_cancelled": int(order_metrics[7]),
            "monthly_revenue": float(order_metrics[8]),
            "inventory_value": float(inventory_metrics[0]),
            "low_inventory": int(inventory_metrics[1]),
            "open_print_minutes": int(print_metrics[0]),
            "planned_filament_grams": float(print_metrics[1]),
            "filament_rolls": int(filament_metrics[0]),
            "low_filament": int(filament_metrics[1]),
            "active_filament_colors": int(filament_metrics[2]),
            "sync_needed": sync_needed,
        },
        "monthly_revenue": monthly_revenue,
        "printers": [public_bambu_printer_dict(item) for item in printers],
        "top_products": [
            {"product_id": row[0], "label": row[1] or row[2], "sold": int(row[3] or 0)} for row in top_products
        ],
        "low_inventory": [
            {
                "product_id": row[0].product_id,
                "variant_id": row[0].product_variant_id,
                "label": row[1] or row[2],
                "free_stock": row[0].quantity_on_hand - row[0].quantity_reserved,
                "minimum_stock": row[0].minimum_stock_level,
            }
            for row in low_inventory_rows
        ],
        "open_print_jobs": list_rows(open_jobs),
    }


def search_overview(db: Session, query: str, limit: int) -> dict:
    needle = f"%{query.strip()}%"
    products = db.scalars(
        select(Product).where(or_(Product.name.ilike(needle), Product.internal_title.ilike(needle), Product.internal_category.ilike(needle))).order_by(Product.id).limit(limit)
    ).all()
    variants = db.scalars(
        select(ProductVariant).where(or_(ProductVariant.sku.ilike(needle), ProductVariant.variant_name.ilike(needle), ProductVariant.color.ilike(needle), ProductVariant.material.ilike(needle))).order_by(ProductVariant.id).limit(limit)
    ).all()
    variant_product_ids = {item.product_id for item in variants}
    missing_product_ids = variant_product_ids - {item.id for item in products}
    if missing_product_ids and len(products) < limit:
        products.extend(db.scalars(select(Product).where(Product.id.in_(missing_product_ids)).limit(limit - len(products))).all())
    orders = db.scalars(
        select(Order).where(or_(Order.internal_order_number.ilike(needle), Order.external_order_id.ilike(needle), Order.customer_name.ilike(needle))).order_by(Order.id.desc()).limit(limit)
    ).all()
    printers = db.scalars(
        select(BambuPrinter).where(or_(BambuPrinter.name.ilike(needle), BambuPrinter.model.ilike(needle), BambuPrinter.host.ilike(needle), BambuPrinter.location.ilike(needle))).order_by(BambuPrinter.id).limit(limit)
    ).all()
    return {"products": list_rows(products[:limit]), "orders": list_rows(orders), "printers": [public_bambu_printer_dict(item) for item in printers]}

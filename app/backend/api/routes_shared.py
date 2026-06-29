import csv
import io
import re
import shutil
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.utils import list_rows, to_dict
from connectors.factory import get_platform_connector
from core.config import get_settings
from core.credentials import encrypt_credential, generate_credential_key, is_encrypted_credential
from database import get_db
from models import (
    AccountingDocument,
    AccountingFiscalSetting,
    AccountingPurchase,
    AccountingSale,
    BambuPrinter,
    CostSetting,
    FilamentSpool,
    InventoryMovement,
    Order,
    OrderItem,
    OrderProfitCalculation,
    Platform,
    PlatformCredential,
    PlatformImportLog,
    PrintBatch,
    PrintBatchItem,
    PrintJob,
    Product,
    ProductInventory,
    ProductMedia,
    ProductPlatformPublication,
    ProductPublicationMedia,
    ProductTag,
    ProductTranslation,
    ProductVariant,
    ProductVariantPlatformLink,
    SalesMarket,
    StockRecommendation,
    TrendSnapshot,
    VatPeriod,
)
from schemas.common import (
    AccountingPurchaseCreate,
    AccountingCorrectionCreate,
    AccountingFiscalSettingCreate,
    AccountingSaleCreate,
    VatPeriodCloseCreate,
    BambuPrinterCreate,
    CostSettingCreate,
    AIProductDraftRequest,
    FilamentSpoolCreate,
    OrderCreate,
    OrderItemCreate,
    PlatformCreate,
    PlatformCredentialCreate,
    PrintBatchCreate,
    PrintJobComplete,
    PrintJobCreate,
    ProductCreate,
    ProductInventoryCreate,
    ProductMediaCreate,
    ProductPlatformPublicationCreate,
    ProductPublicationMediaBulkUpdate,
    ProductTranslationCreate,
    ProductTranslationGenerate,
    ProductTagCreate,
    ProductVariantCreate,
    SalesMarketCreate,
    StockRecommendationGenerate,
    StockRecommendationUpdate,
)
from services.ai_product_assistant import generate_ai_product_draft, generate_product_translation
from services.bambu_printers import public_bambu_printer_dict, refresh_bambu_mqtt_status, test_bambu_lan_connection
from publishing.service import (
    mark_product_publications_sync_needed,
    publish_publication,
    sync_publication,
    validate_publication_record,
)
from inventory.service import (
    add_inventory_movement,
    adjust_product_inventory as adjust_inventory_stock,
    inventory_snapshot,
    link_order_item_by_sku,
    list_product_inventory_rows,
    process_order_inventory as process_order_inventory_service,
    release_product_inventory as release_inventory_stock,
    reserve_product_inventory as reserve_inventory_stock,
)
from services.dummy_data import seed_dummy_data

# Routers live in api/routes/*.py after the phase 1 split.

UPLOAD_ROOT = Path("uploads/product_media")
ACCOUNTING_UPLOAD_ROOT = Path("uploads/accounting_documents")
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_ACCOUNTING_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}


def get_or_404(db: Session, model: type, item_id: int):
    item = db.get(model, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return item


def public_credential_dict(credential: PlatformCredential) -> dict:
    data = to_dict(credential)
    data.pop("encrypted_value", None)
    data["has_value"] = bool(credential.encrypted_value)
    data["encrypted"] = is_encrypted_credential(credential.encrypted_value)
    return data


def parse_optional_date(value: str | None):
    if not value:
        return None
    return date.fromisoformat(value)


def fill_vat_amounts(data: dict) -> dict:
    net_amount = float(data.get("net_amount") or 0)
    vat_rate = float(data.get("vat_rate") or 0)
    vat_amount = data.get("vat_amount")
    gross_amount = data.get("gross_amount")
    if vat_amount is None:
        vat_amount = round(net_amount * vat_rate / 100, 2)
    if gross_amount is None:
        gross_amount = round(net_amount + float(vat_amount), 2)
    data["vat_amount"] = vat_amount
    data["gross_amount"] = gross_amount
    return data


def csv_download(filename: str, fieldnames: list[str], rows: list[dict]) -> Response:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def parse_date_range(start_date: str | None = None, end_date: str | None = None) -> tuple[date | None, date | None]:
    start = parse_optional_date(start_date)
    end = parse_optional_date(end_date)
    if start and end and start > end:
        raise HTTPException(status_code=400, detail="Startdatum mag niet na einddatum liggen")
    return start, end


def accounting_sales_query(start: date | None = None, end: date | None = None):
    query = select(AccountingSale)
    if start:
        query = query.where(AccountingSale.invoice_date >= start)
    if end:
        query = query.where(AccountingSale.invoice_date <= end)
    return query


def accounting_purchases_query(start: date | None = None, end: date | None = None):
    query = select(AccountingPurchase)
    if start:
        query = query.where(AccountingPurchase.invoice_date >= start)
    if end:
        query = query.where(AccountingPurchase.invoice_date <= end)
    return query


def accounting_vat_summary_data(db: Session, start: date | None = None, end: date | None = None) -> dict:
    sales = db.scalars(accounting_sales_query(start, end)).all()
    purchases = db.scalars(accounting_purchases_query(start, end)).all()
    sales_net = sum(float(item.net_amount or 0) for item in sales)
    sales_vat = sum(float(item.vat_amount or 0) for item in sales)
    purchase_net = sum(float(item.net_amount or 0) for item in purchases)
    purchase_vat = sum(float(item.vat_amount or 0) for item in purchases)
    missing_sale_docs = sum(1 for item in sales if not db.scalar(select(AccountingDocument.id).where(AccountingDocument.sale_id == item.id, AccountingDocument.status != "gearchiveerd")))
    missing_purchase_docs = sum(1 for item in purchases if not db.scalar(select(AccountingDocument.id).where(AccountingDocument.purchase_id == item.id, AccountingDocument.status != "gearchiveerd")))
    return {
        "sales_net": round(sales_net, 2),
        "sales_vat": round(sales_vat, 2),
        "purchase_net": round(purchase_net, 2),
        "purchase_vat": round(purchase_vat, 2),
        "vat_due": round(sales_vat - purchase_vat, 2),
        "sales_count": len(sales),
        "purchase_count": len(purchases),
        "missing_document_count": missing_sale_docs + missing_purchase_docs,
        "note": "Controlehulpmiddel voor administratie. Laat fiscale keuzes controleren door boekhouder/fiscalist.",
    }


def calculate_order_gross_amount(db: Session, order: Order) -> float:
    if order.total_amount is not None:
        return round(float(order.total_amount), 2)

    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    return round(sum(float(item.unit_sale_price or 0) * int(item.quantity_ordered or 0) for item in items), 2)


def create_accounting_sale_from_order(db: Session, order: Order) -> dict:
    existing = db.scalar(select(AccountingSale).where(AccountingSale.order_id == order.id))
    if existing:
        data = to_dict(existing)
        data["created"] = False
        data["message"] = "Verkoopboeking bestond al voor deze order."
        return data

    gross_amount = calculate_order_gross_amount(db, order)
    if gross_amount <= 0:
        raise HTTPException(status_code=400, detail="Order heeft geen positief bedrag om te boeken")

    vat_rate = 21.0
    net_amount = round(gross_amount / (1 + vat_rate / 100), 2)
    vat_amount = round(gross_amount - net_amount, 2)
    invoice_number = order.internal_order_number
    if db.scalar(select(AccountingSale.id).where(AccountingSale.invoice_number == invoice_number)):
        invoice_number = f"{order.internal_order_number}-{order.id}"

    item = AccountingSale(
        order_id=order.id,
        platform_id=order.platform_id,
        invoice_number=invoice_number,
        invoice_date=order.order_date.date() if order.order_date else date.today(),
        customer_name=order.customer_name,
        description=f"Verkooporder {order.internal_order_number}",
        net_amount=net_amount,
        vat_rate=vat_rate,
        vat_amount=vat_amount,
        gross_amount=round(gross_amount, 2),
        currency=order.currency or "EUR",
        status="concept",
        source="order_import",
        note=(
            "Automatisch gemaakt vanuit order. Btw voorlopig berekend met standaardtarief 21%; "
            "controleer platform, land en btw-regime voordat je dit gebruikt voor aangifte."
        ),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    data = to_dict(item)
    data["created"] = True
    data["message"] = "Verkoopboeking aangemaakt vanuit order."
    return data



def get_filament_price_per_gram(db: Session, material: str | None, color: str | None) -> float:
    query = select(FilamentSpool).where(FilamentSpool.active.is_(True))
    if material:
        query = query.where(FilamentSpool.material == material)
    if color:
        query = query.where(FilamentSpool.color == color)
    spool = db.scalar(query.order_by(FilamentSpool.price_per_gram))
    if not spool and material:
        spool = db.scalar(
            select(FilamentSpool)
            .where(FilamentSpool.active.is_(True), FilamentSpool.material == material)
            .order_by(FilamentSpool.price_per_gram)
        )
    if not spool:
        spool = db.scalar(select(FilamentSpool).where(FilamentSpool.active.is_(True)).order_by(FilamentSpool.price_per_gram))
    return float(spool.price_per_gram) if spool else 0.0


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
    PrintBatch,
    PrintBatchItem,
    PrintJob,
    Product,
    ProductInventory,
    ProductMedia,
    ProductPlatformPublication,
    ProductPublicationMedia,
    ProductTag,
    ProductVariant,
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
    ProductTagCreate,
    ProductVariantCreate,
    StockRecommendationGenerate,
    StockRecommendationUpdate,
)
from services.ai_product_assistant import generate_ai_product_draft
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

router = APIRouter()

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


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/credentials/generate-key")
def generate_credentials_key() -> dict[str, str]:
    return {"credential_encryption_key": generate_credential_key()}


@router.get("/ai/product-draft/status")
def ai_product_draft_status() -> dict[str, object]:
    settings = get_settings()
    return {
        "enabled": settings.ai_openai_enabled,
        "configured": bool(settings.openai_api_key),
        "model": settings.openai_product_model,
        "ready": settings.ai_openai_enabled and bool(settings.openai_api_key),
        "note": "Echte AI gebruikt OpenAI API-tegoed en valt niet binnen ChatGPT Plus.",
    }


@router.post("/ai/product-draft/generate")
def ai_generate_product_draft(payload: AIProductDraftRequest) -> dict[str, object]:
    return generate_ai_product_draft(payload, get_settings())


@router.post("/seed")
def seed(db: Session = Depends(get_db)) -> dict[str, str]:
    seed_dummy_data(db)
    return {"status": "seeded"}


@router.get("/accounting/sales")
def list_accounting_sales(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
):
    start, end = parse_date_range(start_date, end_date)
    rows = db.scalars(accounting_sales_query(start, end).order_by(AccountingSale.invoice_date.desc().nullslast(), AccountingSale.id.desc())).all()
    return list_rows(rows)


@router.post("/accounting/sales")
def create_accounting_sale(payload: AccountingSaleCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["invoice_date"] = parse_optional_date(data.get("invoice_date"))
    item = AccountingSale(**fill_vat_amounts(data))
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.post("/accounting/sales/{item_id}/credit")
def credit_accounting_sale(item_id: int, payload: AccountingCorrectionCreate, db: Session = Depends(get_db)):
    original = get_or_404(db, AccountingSale, item_id)
    if original.entry_type in {"credit", "correction"}:
        raise HTTPException(status_code=400, detail="Deze boeking is zelf al een correctie")
    if original.status == "gecorrigeerd" or db.scalar(select(AccountingSale.id).where(AccountingSale.correction_of_sale_id == original.id)):
        raise HTTPException(status_code=400, detail="Deze verkoopboeking is al gecorrigeerd")
    correction_date = parse_optional_date(payload.correction_date) or date.today()
    item = AccountingSale(
        order_id=original.order_id,
        platform_id=original.platform_id,
        invoice_number=f"CR-{original.invoice_number or original.id}",
        invoice_date=correction_date,
        customer_name=original.customer_name,
        customer_country=original.customer_country,
        description=f"Credit/correctie op verkoopboeking {original.invoice_number or original.id}",
        net_amount=-float(original.net_amount or 0),
        vat_rate=float(original.vat_rate or 0),
        vat_amount=-float(original.vat_amount or 0),
        gross_amount=-float(original.gross_amount or 0),
        currency=original.currency,
        status="geboekt",
        source="correction",
        entry_type="credit",
        correction_of_sale_id=original.id,
        note=payload.reason,
    )
    original.status = "gecorrigeerd"
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/accounting/purchases")
def list_accounting_purchases(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
):
    start, end = parse_date_range(start_date, end_date)
    rows = db.scalars(accounting_purchases_query(start, end).order_by(AccountingPurchase.invoice_date.desc().nullslast(), AccountingPurchase.id.desc())).all()
    return list_rows(rows)


@router.post("/accounting/purchases")
def create_accounting_purchase(payload: AccountingPurchaseCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["invoice_date"] = parse_optional_date(data.get("invoice_date"))
    item = AccountingPurchase(**fill_vat_amounts(data))
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.post("/accounting/purchases/{item_id}/correction")
def correct_accounting_purchase(item_id: int, payload: AccountingCorrectionCreate, db: Session = Depends(get_db)):
    original = get_or_404(db, AccountingPurchase, item_id)
    if original.entry_type in {"credit", "correction"}:
        raise HTTPException(status_code=400, detail="Deze boeking is zelf al een correctie")
    if original.payment_status == "gecorrigeerd" or db.scalar(select(AccountingPurchase.id).where(AccountingPurchase.correction_of_purchase_id == original.id)):
        raise HTTPException(status_code=400, detail="Deze inkoopboeking is al gecorrigeerd")
    correction_date = parse_optional_date(payload.correction_date) or date.today()
    item = AccountingPurchase(
        supplier_name=original.supplier_name,
        invoice_number=f"COR-{original.invoice_number or original.id}",
        invoice_date=correction_date,
        category=original.category,
        description=f"Correctie op inkoopboeking {original.invoice_number or original.id}",
        net_amount=-float(original.net_amount or 0),
        vat_rate=float(original.vat_rate or 0),
        vat_amount=-float(original.vat_amount or 0),
        gross_amount=-float(original.gross_amount or 0),
        currency=original.currency,
        payment_status="gecorrigeerd",
        source="correction",
        entry_type="correction",
        correction_of_purchase_id=original.id,
        note=payload.reason,
    )
    original.payment_status = "gecorrigeerd"
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/accounting/documents")
def list_accounting_documents(db: Session = Depends(get_db)):
    rows = db.scalars(select(AccountingDocument).order_by(AccountingDocument.created_at.desc(), AccountingDocument.id.desc())).all()
    return list_rows(rows)


@router.post("/accounting/documents/{item_id}/archive")
def archive_accounting_document(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, AccountingDocument, item_id)
    item.status = "gearchiveerd"
    item.note = f"{item.note or ''}\nGearchiveerd op {date.today().isoformat()}.".strip()
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.post("/accounting/documents/upload")
def upload_accounting_document(
    file: UploadFile = File(...),
    document_type: str = Form("bon"),
    sale_id: int | None = Form(None),
    purchase_id: int | None = Form(None),
    note: str | None = Form(None),
    db: Session = Depends(get_db),
):
    if sale_id:
        get_or_404(db, AccountingSale, sale_id)
    if purchase_id:
        get_or_404(db, AccountingPurchase, purchase_id)
    if not sale_id and not purchase_id:
        raise HTTPException(status_code=400, detail="Koppel het document aan een verkoop- of inkoopboeking")
    if file.content_type not in ALLOWED_ACCOUNTING_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Alleen PDF, JPG, PNG en WEBP zijn toegestaan")

    original_name = Path(file.filename or "upload").name
    extension = Path(original_name).suffix.lower()
    if extension not in {".pdf", ".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Bestandstype wordt niet ondersteund")

    target_group = "purchase" if purchase_id else "sale"
    target_id = purchase_id or sale_id
    target_dir = ACCOUNTING_UPLOAD_ROOT / target_group / str(target_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{extension}"
    target_path = target_dir / filename
    with target_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    item = AccountingDocument(
        document_type=document_type,
        sale_id=sale_id,
        purchase_id=purchase_id,
        file_path=f"/uploads/accounting_documents/{target_group}/{target_id}/{filename}",
        original_filename=original_name,
        mime_type=file.content_type,
        status="bewaard",
        note=note,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/accounting/vat-summary")
def accounting_vat_summary(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
):
    start, end = parse_date_range(start_date, end_date)
    return accounting_vat_summary_data(db, start, end)


@router.get("/accounting/sales/export.csv")
def export_accounting_sales(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
):
    start, end = parse_date_range(start_date, end_date)
    rows = db.scalars(accounting_sales_query(start, end).order_by(AccountingSale.invoice_date, AccountingSale.id)).all()
    fieldnames = [
        "id",
        "order_id",
        "platform_id",
        "invoice_number",
        "invoice_date",
        "customer_name",
        "customer_country",
        "description",
        "net_amount",
        "vat_rate",
        "vat_amount",
        "gross_amount",
        "currency",
        "status",
        "source",
        "entry_type",
        "correction_of_sale_id",
        "note",
    ]
    return csv_download("verkoopboek.csv", fieldnames, [to_dict(item) for item in rows])


@router.get("/accounting/purchases/export.csv")
def export_accounting_purchases(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
):
    start, end = parse_date_range(start_date, end_date)
    rows = db.scalars(accounting_purchases_query(start, end).order_by(AccountingPurchase.invoice_date, AccountingPurchase.id)).all()
    fieldnames = [
        "id",
        "supplier_name",
        "invoice_number",
        "invoice_date",
        "category",
        "description",
        "net_amount",
        "vat_rate",
        "vat_amount",
        "gross_amount",
        "currency",
        "payment_status",
        "source",
        "entry_type",
        "correction_of_purchase_id",
        "note",
    ]
    return csv_download("inkoopboek.csv", fieldnames, [to_dict(item) for item in rows])


@router.get("/accounting/vat-summary/export.csv")
def export_accounting_vat_summary(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
):
    start, end = parse_date_range(start_date, end_date)
    fieldnames = ["sales_net", "sales_vat", "purchase_net", "purchase_vat", "vat_due", "sales_count", "purchase_count", "missing_document_count", "note"]
    return csv_download("btw-samenvatting.csv", fieldnames, [accounting_vat_summary_data(db, start, end)])


@router.get("/accounting/vat-periods")
def list_vat_periods(db: Session = Depends(get_db)):
    rows = db.scalars(select(VatPeriod).order_by(VatPeriod.start_date.desc())).all()
    return list_rows(rows)


@router.post("/accounting/vat-periods/close")
def close_vat_period(payload: VatPeriodCloseCreate, db: Session = Depends(get_db)):
    start, end = parse_date_range(payload.start_date, payload.end_date)
    if not start or not end:
        raise HTTPException(status_code=400, detail="Start- en einddatum zijn verplicht")
    summary = accounting_vat_summary_data(db, start, end)
    item = db.scalar(select(VatPeriod).where(VatPeriod.period_name == payload.period_name))
    if item and item.status == "afgesloten":
        raise HTTPException(status_code=400, detail="Deze btw-periode is al afgesloten")
    if not item:
        item = VatPeriod(period_name=payload.period_name, start_date=start, end_date=end)
        db.add(item)
    item.start_date = start
    item.end_date = end
    item.sales_vat = summary["sales_vat"]
    item.purchase_vat = summary["purchase_vat"]
    item.vat_due = summary["vat_due"]
    item.status = "afgesloten"
    item.note = payload.note or summary["note"]
    db.commit()
    db.refresh(item)
    return to_dict(item)


def seed_default_fiscal_settings(db: Session) -> None:
    defaults = {
        "btw_regime": ("standaard", "Voorlopig standaard btw-regime; controleer dit met boekhouder/fiscalist."),
        "kor_enabled": ("false", "Kleineondernemersregeling niet actief tenzij bewust aangezet."),
        "default_country": ("NL", "Standaardland voor btw-controle."),
        "eu_sales_enabled": ("false", "EU-verkoopregels later expliciet controleren."),
        "default_vat_rate": ("21", "Standaard btw-percentage voor voorlopige boekingen."),
    }
    for name, (value, note) in defaults.items():
        if not db.scalar(select(AccountingFiscalSetting).where(AccountingFiscalSetting.setting_name == name)):
            db.add(AccountingFiscalSetting(setting_name=name, value=value, note=note))
    db.commit()


@router.get("/accounting/fiscal-settings")
def list_accounting_fiscal_settings(db: Session = Depends(get_db)):
    seed_default_fiscal_settings(db)
    rows = db.scalars(select(AccountingFiscalSetting).order_by(AccountingFiscalSetting.setting_name)).all()
    return list_rows(rows)


@router.post("/accounting/fiscal-settings")
def upsert_accounting_fiscal_setting(payload: AccountingFiscalSettingCreate, db: Session = Depends(get_db)):
    item = db.scalar(select(AccountingFiscalSetting).where(AccountingFiscalSetting.setting_name == payload.setting_name))
    if not item:
        item = AccountingFiscalSetting(setting_name=payload.setting_name, value=payload.value, note=payload.note)
        db.add(item)
    else:
        item.value = payload.value
        item.note = payload.note
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/bambu/printers")
def list_bambu_printers(db: Session = Depends(get_db)):
    printers = db.scalars(select(BambuPrinter).order_by(BambuPrinter.name)).all()
    return [public_bambu_printer_dict(printer) for printer in printers]


@router.post("/bambu/printers")
def create_bambu_printer(payload: BambuPrinterCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    access_code = data.pop("access_code", None)
    item = BambuPrinter(**data)
    if access_code:
        item.access_code_encrypted = encrypt_credential(access_code)
    db.add(item)
    db.commit()
    db.refresh(item)
    return public_bambu_printer_dict(item)


@router.put("/bambu/printers/{item_id}")
def update_bambu_printer(item_id: int, payload: BambuPrinterCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, BambuPrinter, item_id)
    data = payload.model_dump()
    access_code = data.pop("access_code", None)
    for key, value in data.items():
        setattr(item, key, value)
    if access_code:
        item.access_code_encrypted = encrypt_credential(access_code)
    db.commit()
    db.refresh(item)
    return public_bambu_printer_dict(item)


@router.post("/bambu/printers/{item_id}/test-connection")
def test_bambu_printer_connection(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, BambuPrinter, item_id)
    return test_bambu_lan_connection(db, item)


@router.post("/bambu/printers/{item_id}/refresh-status")
def refresh_bambu_printer_status(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, BambuPrinter, item_id)
    return refresh_bambu_mqtt_status(db, item)


@router.get("/platforms")
def list_platforms(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(Platform).order_by(Platform.id)).all())


@router.post("/platforms")
def create_platform(payload: PlatformCreate, db: Session = Depends(get_db)):
    item = Platform(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.put("/platforms/{item_id}")
def update_platform(item_id: int, payload: PlatformCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, Platform, item_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/platforms/{platform_id}/credentials")
def list_platform_credentials(platform_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Platform, platform_id)
    credentials = db.scalars(
        select(PlatformCredential).where(PlatformCredential.platform_id == platform_id).order_by(PlatformCredential.key_name)
    ).all()
    return [public_credential_dict(credential) for credential in credentials]


@router.post("/platforms/{platform_id}/credentials")
def create_platform_credential(
    platform_id: int, payload: PlatformCredentialCreate, db: Session = Depends(get_db)
):
    get_or_404(db, Platform, platform_id)
    key_name = payload.key_name.strip().lower()
    if not key_name:
        raise HTTPException(status_code=400, detail="Credential key_name is verplicht")
    existing = db.scalar(
        select(PlatformCredential).where(
            PlatformCredential.platform_id == platform_id,
            PlatformCredential.key_name == key_name,
        )
    )
    if existing:
        existing.encrypted_value = encrypt_credential(payload.encrypted_value)
        db.commit()
        db.refresh(existing)
        return public_credential_dict(existing)
    item = PlatformCredential(platform_id=platform_id, key_name=key_name, encrypted_value=encrypt_credential(payload.encrypted_value))
    db.add(item)
    db.commit()
    db.refresh(item)
    return public_credential_dict(item)


@router.delete("/platform-credentials/{item_id}")
def delete_platform_credential(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, PlatformCredential, item_id)
    db.delete(item)
    db.commit()
    return {"status": "deleted"}


@router.get("/platforms/{platform_id}/connector-status")
def platform_connector_status(platform_id: int, db: Session = Depends(get_db)):
    platform = get_or_404(db, Platform, platform_id)
    connector = get_platform_connector(db, platform)
    status = connector.status()
    return {
        "platform_id": platform.id,
        "platform": platform.name,
        "platform_type": status.platform_type,
        "mode": status.mode,
        "required_credentials": status.required_credentials,
        "configured_credentials": status.configured_credentials,
        "missing_credentials": status.missing_credentials,
        "ready_for_live": status.ready_for_live,
    }


@router.get("/products")
def list_products(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(Product).order_by(Product.id)).all())


@router.post("/products")
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    item = Product(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/products/{item_id}")
def get_product(item_id: int, db: Session = Depends(get_db)):
    return to_dict(get_or_404(db, Product, item_id))


@router.put("/products/{item_id}")
def update_product(item_id: int, payload: ProductCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, Product, item_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    mark_product_publications_sync_needed(db, item.id)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/product-variants")
def list_product_variants(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(ProductVariant).order_by(ProductVariant.id)).all())


@router.post("/product-variants")
def create_product_variant(payload: ProductVariantCreate, db: Session = Depends(get_db)):
    item = ProductVariant(**payload.model_dump())
    db.add(item)
    mark_product_publications_sync_needed(db, item.product_id)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.put("/product-variants/{item_id}")
def update_product_variant(item_id: int, payload: ProductVariantCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductVariant, item_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    mark_product_publications_sync_needed(db, item.product_id)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/products/{product_id}/media")
def list_product_media(product_id: int, db: Session = Depends(get_db)):
    query = select(ProductMedia).where(ProductMedia.product_id == product_id).order_by(ProductMedia.sort_order)
    return list_rows(db.scalars(query).all())


@router.post("/products/{product_id}/media")
def create_product_media(product_id: int, payload: ProductMediaCreate, db: Session = Depends(get_db)):
    get_or_404(db, Product, product_id)
    if payload.is_primary:
        clear_primary_product_media(db, product_id)
    item = ProductMedia(product_id=product_id, **payload.model_dump())
    db.add(item)
    mark_product_publications_sync_needed(db, product_id)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.post("/products/{product_id}/media/upload")
def upload_product_media(
    product_id: int,
    file: UploadFile = File(...),
    alt_text: str | None = Form(None),
    sort_order: int = Form(0),
    is_primary: bool = Form(False),
    db: Session = Depends(get_db),
):
    get_or_404(db, Product, product_id)
    if file.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Alleen JPG, PNG, WEBP en GIF afbeeldingen zijn toegestaan")

    original_name = Path(file.filename or "upload").name
    extension = Path(original_name).suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        raise HTTPException(status_code=400, detail="Bestandstype wordt niet ondersteund")

    target_dir = UPLOAD_ROOT / str(product_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{extension}"
    target_path = target_dir / filename
    with target_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    if is_primary:
        clear_primary_product_media(db, product_id)
    item = ProductMedia(
        product_id=product_id,
        file_path=f"/uploads/product_media/{product_id}/{filename}",
        media_type="image",
        alt_text=alt_text,
        sort_order=sort_order,
        is_primary=is_primary,
    )
    db.add(item)
    mark_product_publications_sync_needed(db, product_id)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.put("/product-media/{item_id}")
def update_product_media(item_id: int, payload: ProductMediaCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductMedia, item_id)
    if payload.is_primary:
        clear_primary_product_media(db, item.product_id, exclude_media_id=item.id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    mark_product_publications_sync_needed(db, item.product_id)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.delete("/product-media/{item_id}")
def delete_product_media(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductMedia, item_id)
    product_id = item.product_id
    delete_uploaded_media_file(item.file_path)
    db.delete(item)
    mark_product_publications_sync_needed(db, product_id)
    db.commit()
    return {"status": "deleted"}


def clear_primary_product_media(db: Session, product_id: int, exclude_media_id: int | None = None) -> None:
    query = select(ProductMedia).where(ProductMedia.product_id == product_id, ProductMedia.is_primary.is_(True))
    for item in db.scalars(query).all():
        if exclude_media_id is None or item.id != exclude_media_id:
            item.is_primary = False


def delete_uploaded_media_file(file_path: str | None) -> None:
    if not file_path or not file_path.startswith("/uploads/product_media/"):
        return
    relative_path = file_path.removeprefix("/uploads/")
    target = Path("uploads") / relative_path
    try:
        resolved_root = UPLOAD_ROOT.resolve()
        resolved_target = target.resolve()
        if resolved_root in resolved_target.parents and resolved_target.is_file():
            resolved_target.unlink()
    except OSError:
        return


@router.get("/products/{product_id}/tags")
def list_product_tags(product_id: int, db: Session = Depends(get_db)):
    query = select(ProductTag).where(ProductTag.product_id == product_id).order_by(ProductTag.tag)
    return list_rows(db.scalars(query).all())


@router.post("/products/{product_id}/tags")
def create_product_tag(product_id: int, payload: ProductTagCreate, db: Session = Depends(get_db)):
    item = ProductTag(product_id=product_id, tag=payload.tag.strip())
    if not item.tag:
        raise HTTPException(status_code=400, detail="Tag is verplicht")
    db.add(item)
    mark_product_publications_sync_needed(db, product_id)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.delete("/product-tags/{item_id}")
def delete_product_tag(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductTag, item_id)
    product_id = item.product_id
    db.delete(item)
    mark_product_publications_sync_needed(db, product_id)
    db.commit()
    return {"status": "deleted"}


@router.get("/products/{product_id}/publications")
def list_product_publications(product_id: int, db: Session = Depends(get_db)):
    query = select(ProductPlatformPublication).where(ProductPlatformPublication.product_id == product_id)
    return list_rows(db.scalars(query).all())


@router.post("/products/{product_id}/publications")
def create_product_publication(
    product_id: int, payload: ProductPlatformPublicationCreate, db: Session = Depends(get_db)
):
    item = ProductPlatformPublication(product_id=product_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.put("/product-publications/{item_id}")
def update_product_publication(
    item_id: int, payload: ProductPlatformPublicationCreate, db: Session = Depends(get_db)
):
    item = get_or_404(db, ProductPlatformPublication, item_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/product-publications/{item_id}/media")
def list_publication_media(item_id: int, db: Session = Depends(get_db)):
    publication = get_or_404(db, ProductPlatformPublication, item_id)
    product_media = db.scalars(
        select(ProductMedia).where(ProductMedia.product_id == publication.product_id).order_by(ProductMedia.sort_order)
    ).all()
    links = {
        link.product_media_id: link
        for link in db.scalars(
            select(ProductPublicationMedia).where(ProductPublicationMedia.product_publication_id == publication.id)
        ).all()
    }
    rows = []
    for media in product_media:
        link = links.get(media.id)
        data = to_dict(media)
        data["selected"] = bool(link and link.active)
        data["publication_media_id"] = link.id if link else None
        data["publication_sort_order"] = link.sort_order if link else media.sort_order
        rows.append(data)
    return rows


@router.put("/product-publications/{item_id}/media")
def update_publication_media(
    item_id: int, payload: ProductPublicationMediaBulkUpdate, db: Session = Depends(get_db)
):
    publication = get_or_404(db, ProductPlatformPublication, item_id)
    allowed_media_ids = {
        item.id for item in db.scalars(select(ProductMedia).where(ProductMedia.product_id == publication.product_id)).all()
    }
    for payload_item in payload.items:
        if payload_item.product_media_id not in allowed_media_ids:
            raise HTTPException(status_code=400, detail="Media-item hoort niet bij dit product")

    existing = db.scalars(
        select(ProductPublicationMedia).where(ProductPublicationMedia.product_publication_id == publication.id)
    ).all()
    for item in existing:
        db.delete(item)
    for payload_item in payload.items:
        db.add(
            ProductPublicationMedia(
                product_publication_id=publication.id,
                product_media_id=payload_item.product_media_id,
                sort_order=payload_item.sort_order,
                active=payload_item.active,
            )
        )
    if publication.publication_status == "gepubliceerd":
        publication.publication_status = "synchronisatie_nodig"
    db.commit()
    return list_publication_media(item_id, db)


@router.post("/product-publications/{item_id}/publish")
def publish_product_publication(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductPlatformPublication, item_id)
    return publish_publication(db, item)


@router.post("/product-publications/{item_id}/sync")
def sync_product_publication(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductPlatformPublication, item_id)
    return sync_publication(db, item)


@router.post("/product-publications/{item_id}/pause")
def pause_product_publication(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductPlatformPublication, item_id)
    item.publication_status = "gepauzeerd"
    db.commit()
    return to_dict(item)


@router.get("/product-publications/{item_id}/check")
def check_product_publication(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductPlatformPublication, item_id)
    return validate_publication_record(db, item)


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
def import_etsy_orders(db: Session = Depends(get_db)):
    order = create_dummy_order(db, platform_type="etsy")
    return {"status": "dummy_etsy_import_complete", "order": to_dict(order)}


@router.post("/orders/import/shopify")
def import_shopify_orders(db: Session = Depends(get_db)):
    platforms = db.scalars(select(Platform).where(Platform.type == "shopify", Platform.active.is_(True)).order_by(Platform.id)).all()
    if not platforms:
        order = create_dummy_order(db, platform_type="shopify")
        return {"status": "dummy_shopify_import_complete", "created": 1, "updated": 0, "skipped": 0, "orders": [to_dict(order)]}

    created = []
    updated = []
    skipped = []
    errors = []

    for platform in platforms:
        connector = get_platform_connector(db, platform)
        status = connector.status()
        if connector.live_mode and status.missing_credentials:
            errors.append({"platform_id": platform.id, "platform": platform.name, "message": f"Ontbrekende Shopify credentials: {', '.join(status.missing_credentials)}"})
            continue
        result = connector.import_orders(limit=25)
        if not result.get("success"):
            errors.append({"platform_id": platform.id, "platform": platform.name, "message": result.get("message", "Shopify import mislukt")})
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
        "status": "shopify_import_complete" if not errors else "shopify_import_completed_with_errors",
        "created": len(created),
        "updated": len(updated),
        "skipped": len(skipped),
        "errors": errors,
        "orders": created + updated + skipped,
    }


def upsert_imported_order(db: Session, platform: Platform, payload: dict) -> dict:
    external_order_id = payload.get("external_order_id")
    if not external_order_id:
        return {"action": "skipped", "order": {"reason": "Order zonder external_order_id overgeslagen"}}

    order = db.scalar(select(Order).where(Order.platform_id == platform.id, Order.external_order_id == external_order_id))
    action = "updated" if order else "created"
    if not order:
        order_number = str(payload.get("order_number") or external_order_id).replace("#", "").strip()
        order = Order(
            internal_order_number=f"SHOPIFY-{platform.id}-{order_number}",
            platform_id=platform.id,
            external_order_id=external_order_id,
            status="nieuw",
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
        item.inventory_status = item.inventory_status or "niet_op_voorraad"
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
        status="nieuw",
    )
    db.add(order)
    db.flush()

    item = OrderItem(
        order_id=order.id,
        external_order_item_id=f"{platform_type.upper()}-LINE-{timestamp}",
        sku=variant.sku,
        quantity_ordered=2,
        unit_sale_price=variant.default_sale_price,
        inventory_status="niet_op_voorraad",
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
            status="nieuw",
        )
        db.add(print_job)
        db.flush()
        item.print_job_id = print_job.id
        created.append(to_dict(print_job))

    if created or updated:
        order.status = "ingepland"
    db.commit()
    return {"status": "created", "created": created, "updated": updated}


@router.post("/orders/{item_id}/create-accounting-sale")
def create_order_accounting_sale(item_id: int, db: Session = Depends(get_db)):
    order = get_or_404(db, Order, item_id)
    return create_accounting_sale_from_order(db, order)


@router.get("/inventory/products")
def list_product_inventory(db: Session = Depends(get_db)):
    return list_product_inventory_rows(db)


@router.post("/inventory/products")
def create_product_inventory(payload: ProductInventoryCreate, db: Session = Depends(get_db)):
    item = ProductInventory(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.put("/inventory/products/{item_id}")
def update_product_inventory(item_id: int, payload: ProductInventoryCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductInventory, item_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    data = to_dict(item)
    data["free_stock"] = item.free_stock
    return data


@router.get("/inventory/movements")
def list_inventory_movements(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(InventoryMovement).order_by(InventoryMovement.id.desc())).all())


@router.post("/inventory/products/{item_id}/adjust")
def adjust_product_inventory(item_id: int, quantity: int, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductInventory, item_id)
    return adjust_inventory_stock(db, item, quantity)


@router.post("/inventory/products/{item_id}/reserve")
def reserve_product_inventory(item_id: int, quantity: int, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductInventory, item_id)
    return reserve_inventory_stock(db, item, quantity)


@router.post("/inventory/products/{item_id}/release")
def release_product_inventory(item_id: int, quantity: int, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductInventory, item_id)
    return release_inventory_stock(db, item, quantity)


@router.get("/filament")
def list_filament(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(FilamentSpool).order_by(FilamentSpool.id)).all())


@router.post("/filament")
def create_filament(payload: FilamentSpoolCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["price_per_gram"] = data["purchase_price"] / data["initial_weight_grams"]
    item = FilamentSpool(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.put("/filament/{item_id}")
def update_filament(item_id: int, payload: FilamentSpoolCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, FilamentSpool, item_id)
    data = payload.model_dump()
    data["price_per_gram"] = data["purchase_price"] / data["initial_weight_grams"]
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    return to_dict(item)


@router.post("/filament/{item_id}/adjust")
def adjust_filament(item_id: int, remaining_weight_grams: float, db: Session = Depends(get_db)):
    item = get_or_404(db, FilamentSpool, item_id)
    item.remaining_weight_grams = remaining_weight_grams
    db.commit()
    return to_dict(item)


@router.get("/cost-settings")
def list_cost_settings(db: Session = Depends(get_db)):
    seed_default_cost_settings(db)
    return list_rows(db.scalars(select(CostSetting).order_by(CostSetting.setting_name)).all())


@router.post("/cost-settings")
def create_cost_setting(payload: CostSettingCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(CostSetting).where(CostSetting.setting_name == payload.setting_name))
    if existing:
        existing.value = payload.value
        db.commit()
        db.refresh(existing)
        return to_dict(existing)
    item = CostSetting(setting_name=payload.setting_name, value=payload.value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.put("/cost-settings/{item_id}")
def update_cost_setting(item_id: int, payload: CostSettingCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, CostSetting, item_id)
    item.setting_name = payload.setting_name
    item.value = payload.value
    db.commit()
    db.refresh(item)
    return to_dict(item)


def seed_default_cost_settings(db: Session) -> None:
    defaults = {
        "packaging_cost_per_order": 0.75,
        "platform_fee_percent": 6.5,
        "platform_fee_fixed": 0.30,
        "shipping_cost_per_order": 0.00,
        "electricity_cost_per_hour": 0.35,
    }
    changed = False
    for name, value in defaults.items():
        if not db.scalar(select(CostSetting).where(CostSetting.setting_name == name)):
            db.add(CostSetting(setting_name=name, value=value))
            changed = True
    if changed:
        db.commit()


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

    already_processed = item.status in {"geprint", "deels_mislukt", "mislukt", "verwerkt"}
    previous_to_inventory = item.quantity_to_inventory if already_processed else 0
    previous_failed = item.quantity_failed if already_processed else 0
    item.quantity_succeeded = payload.quantity_succeeded
    item.quantity_failed = payload.quantity_failed
    item.quantity_to_order = quantity_to_order
    item.quantity_to_inventory = max(0, payload.quantity_succeeded - quantity_to_order)
    if payload.quantity_succeeded == 0 and payload.quantity_failed > 0:
        item.status = "mislukt"
    elif payload.quantity_failed > 0:
        item.status = "deels_mislukt"
    else:
        item.status = "geprint"

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
    if jobs and all(job.status in {"geprint", "deels_mislukt"} for job in jobs):
        order.status = "geprint"


@router.get("/print-batches")
def list_print_batches(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(PrintBatch).order_by(PrintBatch.id)).all())


@router.get("/planning/batch-suggestions")
@router.get("/print-batches/suggestions")
def suggest_print_batches(db: Session = Depends(get_db)):
    jobs = db.scalars(
        select(PrintJob)
        .where(PrintJob.status.in_(["nieuw", "gepland"]))
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
                "print_file_path": variant.print_file_path if variant else "",
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
        status="gepland",
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
    rows = build_batch_export_rows(db, batch)
    if not rows:
        raise HTTPException(status_code=400, detail="Batch bevat geen printtaken")

    export_date = (batch.planned_date or date.today()).isoformat()
    batch_slug = slugify(batch.batch_name)
    export_dir = Path("exports") / "PrintJobs" / export_date / batch_slug
    export_dir.mkdir(parents=True, exist_ok=True)

    production_csv = export_dir / "productielijst.csv"
    orders_csv = export_dir / "orderoverzicht.csv"
    markdown_file = export_dir / "productielijst.md"

    write_csv(production_csv, rows)
    write_csv(
        orders_csv,
        [
            {
                "order_number": row["order_number"],
                "job_id": row["job_id"],
                "sku": row["sku"],
                "product": row["product"],
                "variant": row["variant"],
                "quantity_in_batch": row["quantity_in_batch"],
                "quantity_to_order": row["quantity_to_order"],
                "quantity_to_inventory": row["quantity_to_inventory"],
            }
            for row in rows
        ],
    )
    markdown_file.write_text(build_batch_markdown(batch, rows), encoding="utf-8")

    return {
        "status": "exported",
        "batch_id": batch.id,
        "export_dir": str(export_dir),
        "files": {
            "productielijst_csv": str(production_csv),
            "orderoverzicht_csv": str(orders_csv),
            "productielijst_markdown": str(markdown_file),
        },
        "row_count": len(rows),
    }


def build_batch_export_rows(db: Session, batch: PrintBatch) -> list[dict]:
    batch_items = db.scalars(select(PrintBatchItem).where(PrintBatchItem.print_batch_id == batch.id)).all()
    rows = []
    for batch_item in batch_items:
        job = db.get(PrintJob, batch_item.print_job_id)
        if not job:
            continue
        product = db.get(Product, job.product_id)
        variant = db.get(ProductVariant, job.product_variant_id)
        order_item = db.get(OrderItem, job.order_item_id) if job.order_item_id else None
        order = db.get(Order, order_item.order_id) if order_item else None
        rows.append(
            {
                "batch_id": batch.id,
                "batch_name": batch.batch_name,
                "job_id": job.id,
                "order_number": order.internal_order_number if order else "voorraadproductie",
                "product": product.name if product else "",
                "variant": variant.variant_name if variant else "",
                "sku": variant.sku if variant else "",
                "color": job.color or (variant.color if variant else ""),
                "material": job.material or (variant.material if variant else ""),
                "quantity_in_batch": batch_item.quantity_in_batch,
                "quantity_needed": job.quantity_needed,
                "quantity_planned": job.quantity_planned,
                "quantity_to_order": job.quantity_to_order,
                "quantity_to_inventory": job.quantity_to_inventory,
                "estimated_print_time_minutes": job.estimated_print_time_minutes,
                "estimated_filament_grams": job.estimated_filament_grams,
                "print_file_path": variant.print_file_path if variant else "",
            }
        )
    return sorted(rows, key=lambda row: (row["material"], row["color"], row["product"], row["variant"]))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_batch_markdown(batch: PrintBatch, rows: list[dict]) -> str:
    lines = [
        f"# Productielijst - {batch.batch_name}",
        "",
        f"- Batch ID: {batch.id}",
        f"- Geplande datum: {batch.planned_date or '-'}",
        f"- Materiaal: {batch.material or '-'}",
        f"- Kleur: {batch.color or '-'}",
        f"- Geschatte printtijd minuten: {batch.estimated_total_print_time_minutes or 0}",
        f"- Geschat filament gram: {batch.estimated_total_filament_grams or 0}",
        "",
    ]
    current_group = None
    for row in rows:
        group = (row["material"], row["color"])
        if group != current_group:
            lines.extend(["", f"## {row['material'] or '-'} - {row['color'] or '-'}", ""])
            current_group = group
        lines.append(
            f"- {row['quantity_in_batch']}x {row['product']} / {row['variant']} "
            f"({row['sku']}) - order: {row['order_number']} - bestand: {row['print_file_path'] or '-'}"
        )
    lines.append("")
    return "\n".join(lines)


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower())
    return value.strip("-") or "batch"


@router.get("/orders/{item_id}/profit")
def get_order_profit(item_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Order, item_id)
    calculation = db.scalar(select(OrderProfitCalculation).where(OrderProfitCalculation.order_id == item_id))
    if not calculation:
        calculation = calculate_order_profit(db, item_id)
        db.commit()
        db.refresh(calculation)
    return to_dict(calculation)


@router.post("/orders/{item_id}/recalculate-profit")
def recalculate_order_profit(item_id: int, db: Session = Depends(get_db)):
    calculation = calculate_order_profit(db, item_id)
    db.commit()
    db.refresh(calculation)
    return to_dict(calculation)


def calculate_order_profit(db: Session, order_id: int) -> OrderProfitCalculation:
    order = get_or_404(db, Order, order_id)
    seed_default_cost_settings(db)
    settings = {
        item.setting_name: float(item.value)
        for item in db.scalars(select(CostSetting)).all()
    }
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order_id)).all()

    sale_amount = sum(float(item.unit_sale_price or 0) * item.quantity_ordered for item in items)
    if sale_amount == 0 and order.total_amount is not None:
        sale_amount = float(order.total_amount)

    filament_cost = 0.0
    electricity_hours = 0.0
    for item in items:
        if not item.product_variant_id:
            continue
        variant = db.get(ProductVariant, item.product_variant_id)
        if not variant:
            continue
        grams = float(variant.estimated_filament_grams or 0) * item.quantity_ordered
        filament_cost += grams * get_filament_price_per_gram(db, variant.material, variant.color)
        electricity_hours += ((variant.estimated_print_time_minutes or 0) * item.quantity_ordered) / 60

    packaging_cost = settings.get("packaging_cost_per_order", 0)
    platform_fee = sale_amount * (settings.get("platform_fee_percent", 0) / 100) + settings.get("platform_fee_fixed", 0)
    shipping_cost = settings.get("shipping_cost_per_order", 0)
    electricity_cost = electricity_hours * settings.get("electricity_cost_per_hour", 0)
    estimated_profit = sale_amount - filament_cost - packaging_cost - platform_fee - shipping_cost - electricity_cost

    calculation = db.scalar(select(OrderProfitCalculation).where(OrderProfitCalculation.order_id == order_id))
    if not calculation:
        calculation = OrderProfitCalculation(order_id=order_id)
        db.add(calculation)

    calculation.sale_amount = round(sale_amount, 2)
    calculation.filament_cost = round(filament_cost, 2)
    calculation.packaging_cost = round(packaging_cost, 2)
    calculation.platform_fee = round(platform_fee, 2)
    calculation.shipping_cost = round(shipping_cost, 2)
    calculation.electricity_cost = round(electricity_cost, 2)
    calculation.estimated_profit = round(estimated_profit, 2)
    return calculation


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
                StockRecommendation.status.in_(["nieuw", "aangepast"]),
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
                status="nieuw",
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
    item.status = "geaccepteerd"
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
    item.status = "aangepast"
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.post("/stock-recommendations/{item_id}/ignore")
def ignore_stock_recommendation(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, StockRecommendation, item_id)
    item.status = "genegeerd"
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
        status="nieuw",
    )
    item.status = "omgezet_naar_printtaak"
    db.add(print_job)
    db.commit()
    db.refresh(print_job)
    return to_dict(print_job)

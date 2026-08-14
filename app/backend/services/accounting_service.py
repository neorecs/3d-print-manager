import csv
import io
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.utils import to_dict
from domain.statuses import ACCOUNTING_CLOSED, ACCOUNTING_CONCEPT, ACCOUNTING_DOCUMENT_ARCHIVED
from models import (
    AccountingDocument,
    AccountingFiscalSetting,
    AccountingPurchase,
    AccountingSale,
    CostSetting,
    FilamentSpool,
    Order,
    OrderItem,
    OrderProfitCalculation,
    ProductVariant,
    VatPeriod,
)


CENT = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def parse_optional_date(value: str | None):
    if not value:
        return None
    return date.fromisoformat(value)


def parse_date_range(start_date: str | None = None, end_date: str | None = None) -> tuple[date | None, date | None]:
    start = parse_optional_date(start_date)
    end = parse_optional_date(end_date)
    if start and end and start > end:
        raise HTTPException(status_code=400, detail="Startdatum mag niet na einddatum liggen")
    return start, end


def fill_vat_amounts(data: dict) -> dict:
    net_amount = money(data.get("net_amount"))
    vat_rate = Decimal(str(data.get("vat_rate") or 0))
    vat_amount = data.get("vat_amount")
    gross_amount = data.get("gross_amount")
    if vat_amount is None:
        vat_amount = (net_amount * vat_rate / Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)
    else:
        vat_amount = money(vat_amount)
    if gross_amount is None:
        gross_amount = net_amount + vat_amount
    data["net_amount"] = net_amount
    data["vat_rate"] = vat_rate
    data["vat_amount"] = money(vat_amount)
    data["gross_amount"] = money(gross_amount)
    return data


def ensure_accounting_date_open(db: Session, entry_date: date | None) -> None:
    if not entry_date:
        return
    closed = db.scalar(
        select(VatPeriod).where(
            VatPeriod.status == ACCOUNTING_CLOSED,
            VatPeriod.start_date <= entry_date,
            VatPeriod.end_date >= entry_date,
        )
    )
    if closed:
        raise HTTPException(
            status_code=409,
            detail=f"Btw-periode {closed.period_name} is afgesloten. Boek een correctie in een open periode.",
        )


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
    sales_net = sum((money(item.net_amount) for item in sales), Decimal("0"))
    sales_vat = sum((money(item.vat_amount) for item in sales), Decimal("0"))
    purchase_net = sum((money(item.net_amount) for item in purchases), Decimal("0"))
    purchase_vat = sum((money(item.vat_amount) for item in purchases), Decimal("0"))
    missing_sale_docs = sum(1 for item in sales if not db.scalar(select(AccountingDocument.id).where(AccountingDocument.sale_id == item.id, AccountingDocument.status != ACCOUNTING_DOCUMENT_ARCHIVED)))
    missing_purchase_docs = sum(1 for item in purchases if not db.scalar(select(AccountingDocument.id).where(AccountingDocument.purchase_id == item.id, AccountingDocument.status != ACCOUNTING_DOCUMENT_ARCHIVED)))
    return {
        "sales_net": float(money(sales_net)),
        "sales_vat": float(money(sales_vat)),
        "purchase_net": float(money(purchase_net)),
        "purchase_vat": float(money(purchase_vat)),
        "vat_due": float(money(sales_vat - purchase_vat)),
        "sales_count": len(sales),
        "purchase_count": len(purchases),
        "missing_document_count": missing_sale_docs + missing_purchase_docs,
        "note": "Controlehulpmiddel voor administratie. Laat fiscale keuzes controleren door boekhouder/fiscalist.",
    }


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


def calculate_order_gross_amount(db: Session, order: Order) -> Decimal:
    if order.total_amount is not None:
        return money(order.total_amount)
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    return money(sum((money(item.unit_sale_price) * int(item.quantity_ordered or 0) for item in items), Decimal("0")))


def create_accounting_sale_from_order(db: Session, order: Order) -> dict:
    existing = db.scalar(select(AccountingSale).where(AccountingSale.order_id == order.id))
    if existing:
        data = to_dict(existing)
        data["created"] = False
        data["message"] = "Verkoopboeking bestond al voor deze order."
        return data

    invoice_date = order.order_date.date() if order.order_date else date.today()
    ensure_accounting_date_open(db, invoice_date)
    gross_amount = calculate_order_gross_amount(db, order)
    if gross_amount <= 0:
        raise HTTPException(status_code=400, detail="Order heeft geen positief bedrag om te boeken")

    vat_setting = db.scalar(select(AccountingFiscalSetting).where(AccountingFiscalSetting.setting_name == "default_vat_rate"))
    vat_rate = Decimal(vat_setting.value) if vat_setting else Decimal("21")
    net_amount = money(gross_amount / (Decimal("1") + vat_rate / Decimal("100")))
    vat_amount = money(gross_amount - net_amount)
    invoice_number = order.internal_order_number
    if db.scalar(select(AccountingSale.id).where(AccountingSale.invoice_number == invoice_number)):
        invoice_number = f"{order.internal_order_number}-{order.id}"

    item = AccountingSale(
        order_id=order.id,
        platform_id=order.platform_id,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        customer_name=order.customer_name,
        description=f"Verkooporder {order.internal_order_number}",
        net_amount=net_amount,
        vat_rate=vat_rate,
        vat_amount=vat_amount,
        gross_amount=money(gross_amount),
        currency=order.currency or "EUR",
        status=ACCOUNTING_CONCEPT,
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
    spool = db.scalar(query.order_by(FilamentSpool.remaining_weight_grams.desc()))
    if spool and spool.price_per_gram is not None:
        return float(spool.price_per_gram)
    fallback = db.scalar(select(CostSetting).where(CostSetting.setting_name == "fallback_filament_price_per_gram"))
    return float(fallback.value) if fallback else 0.02


def calculate_order_profit(db: Session, order_id: int) -> OrderProfitCalculation:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    seed_default_cost_settings(db)
    settings = {item.setting_name: float(item.value) for item in db.scalars(select(CostSetting)).all()}
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

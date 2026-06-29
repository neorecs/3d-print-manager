import csv
import io
from datetime import date

from fastapi import HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.utils import to_dict
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
)


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

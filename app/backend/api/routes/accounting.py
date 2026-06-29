from fastapi import APIRouter
from api.routes_shared import *

router = APIRouter()

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




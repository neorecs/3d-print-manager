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




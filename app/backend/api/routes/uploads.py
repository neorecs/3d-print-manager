from fastapi import APIRouter
from api.routes_shared import *
from api.routes.products import clear_primary_product_media

router = APIRouter()

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



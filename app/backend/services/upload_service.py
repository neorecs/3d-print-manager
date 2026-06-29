import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.utils import to_dict
from domain.statuses import ACCOUNTING_DOCUMENT_STORED
from models import AccountingDocument, AccountingPurchase, AccountingSale, Product, ProductMedia
from publishing.service import mark_product_publications_sync_needed


UPLOAD_ROOT = Path("uploads/product_media")
ACCOUNTING_UPLOAD_ROOT = Path("uploads/accounting_documents")
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_ACCOUNTING_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}


def upload_accounting_document_file(
    db: Session,
    file: UploadFile,
    document_type: str,
    sale_id: int | None,
    purchase_id: int | None,
    note: str | None,
) -> dict:
    if sale_id and not db.get(AccountingSale, sale_id):
        raise HTTPException(status_code=404, detail="AccountingSale not found")
    if purchase_id and not db.get(AccountingPurchase, purchase_id):
        raise HTTPException(status_code=404, detail="AccountingPurchase not found")
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
        status=ACCOUNTING_DOCUMENT_STORED,
        note=note,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


def upload_product_media_file(
    db: Session,
    product_id: int,
    file: UploadFile,
    alt_text: str | None,
    sort_order: int,
    is_primary: bool,
    clear_primary,
) -> dict:
    if not db.get(Product, product_id):
        raise HTTPException(status_code=404, detail="Product not found")
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
        clear_primary(db, product_id)
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

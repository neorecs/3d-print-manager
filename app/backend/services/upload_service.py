import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.utils import to_dict
from domain.statuses import ACCOUNTING_DOCUMENT_STORED
from models import AccountingDocument, AccountingPurchase, AccountingSale, Product, ProductMedia
from publishing.service import mark_product_publications_sync_needed
from core.config import get_settings


UPLOAD_ROOT = Path("uploads/product_media")
ACCOUNTING_UPLOAD_ROOT = Path("uploads/accounting_documents")
PRODUCT_PRINT_FILE_ROOT = Path("uploads/product_print_files")
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_ACCOUNTING_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}
ALLOWED_PRODUCT_FILE_SUFFIXES = (
    ".gcode.3mf",
    "_gcode.3mf",
    ".zip.amf",
    ".3mf",
    ".stl",
    ".stp",
    ".step",
    ".svg",
    ".amf",
    ".obj",
    ".gltf",
    ".glb",
    ".fbx",
    ".oltp",
    ".gcode",
)


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
    _copy_upload_limited(file, target_path, get_settings().upload_accounting_max_bytes, "Administratiedocument")

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
    _copy_upload_limited(file, target_path, get_settings().upload_image_max_bytes, "Productafbeelding")

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


def upload_product_print_file(db: Session, product_id: int, file: UploadFile) -> dict:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    original_name = Path(file.filename or "model.3mf").name
    if not is_supported_product_file(original_name):
        raise HTTPException(
            status_code=400,
            detail=(
                "Dit bestandstype wordt niet ondersteund door Bambu Studio. "
                "Gebruik 3MF, STL, STEP/STP, SVG, AMF, OBJ, GLTF/GLB, FBX, OLTP of G-code."
            ),
        )

    target_dir = PRODUCT_PRINT_FILE_ROOT / str(product_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_print_filename(original_name)
    filename = f"{uuid.uuid4().hex}-{safe_name}"
    target_path = target_dir / filename
    _copy_upload_limited(file, target_path, get_settings().upload_print_file_max_bytes, "Printbestand")

    delete_uploaded_product_print_file(product.print_file_path)
    product.print_file_path = f"/uploads/product_print_files/{product_id}/{filename}"
    mark_product_publications_sync_needed(db, product_id)
    db.commit()
    db.refresh(product)
    return {
        "ok": True,
        "product_id": product.id,
        "print_file_path": product.print_file_path,
        "original_filename": original_name,
        "message": "Printbestand gekoppeld aan product.",
        "product": to_dict(product),
    }


def delete_uploaded_product_print_file(file_path: str | None) -> None:
    if not file_path or not file_path.startswith("/uploads/product_print_files/"):
        return
    relative_path = file_path.removeprefix("/uploads/")
    target = Path("uploads") / relative_path
    try:
        resolved_root = PRODUCT_PRINT_FILE_ROOT.resolve()
        resolved_target = target.resolve()
        if resolved_root in resolved_target.parents and resolved_target.is_file():
            resolved_target.unlink()
    except OSError:
        return


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


def _safe_print_filename(filename: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in "._-" else "-" for char in filename.strip())
    return cleaned.strip(".-") or "model.3mf"


def is_supported_product_file(filename: str) -> bool:
    return filename.lower().endswith(ALLOWED_PRODUCT_FILE_SUFFIXES)


def _copy_upload_limited(file: UploadFile, target_path: Path, maximum_bytes: int, label: str) -> int:
    size = 0
    try:
        with target_path.open("wb") as output:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > maximum_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"{label} is te groot. Maximum is {maximum_bytes // (1024 * 1024)} MB.",
                    )
                output.write(chunk)
    except Exception:
        target_path.unlink(missing_ok=True)
        raise
    return size

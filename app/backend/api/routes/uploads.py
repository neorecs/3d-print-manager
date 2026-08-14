import mimetypes
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from api.routes_shared import *
from api.routes.products import clear_primary_product_media
from services.upload_service import upload_accounting_document_file, upload_product_media_file

router = APIRouter()


@router.get("/secure-files/{file_path:path}")
def secure_uploaded_file(file_path: str):
    upload_root = Path("uploads").resolve()
    target = (upload_root / file_path).resolve()
    if upload_root not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="Bestand niet gevonden")
    media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return FileResponse(target, media_type=media_type, headers={"Cache-Control": "private, no-store"})

@router.post("/accounting/documents/upload")
def upload_accounting_document(
    file: UploadFile = File(...),
    document_type: str = Form("bon"),
    sale_id: int | None = Form(None),
    purchase_id: int | None = Form(None),
    note: str | None = Form(None),
    db: Session = Depends(get_db),
):
    return upload_accounting_document_file(db, file, document_type, sale_id, purchase_id, note)

@router.post("/products/{product_id}/media/upload")
def upload_product_media(
    product_id: int,
    file: UploadFile = File(...),
    alt_text: str | None = Form(None),
    sort_order: int = Form(0),
    is_primary: bool = Form(False),
    db: Session = Depends(get_db),
):
    return upload_product_media_file(db, product_id, file, alt_text, sort_order, is_primary, clear_primary_product_media)



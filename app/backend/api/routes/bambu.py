from fastapi import APIRouter
from api.routes_shared import *
from models import PrinterBridge

router = APIRouter()


def _check_connection(db: Session, data: dict) -> None:
    mode = (data.get("connection_mode") or "lan").lower()
    if mode not in {"lan", "bridge"}:
        raise HTTPException(status_code=400, detail="Kies verbinding 'lan' of 'bridge'.")
    data["connection_mode"] = mode
    if mode != "bridge":
        data["bridge_id"] = None
        return
    bridge = db.get(PrinterBridge, data.get("bridge_id")) if data.get("bridge_id") else None
    if bridge is None or bridge.revoked:
        raise HTTPException(status_code=400, detail="Kies een actieve bridge voor een printer buiten je eigen netwerk.")

@router.get("/bambu/printers")
def list_bambu_printers(db: Session = Depends(get_db)):
    printers = db.scalars(select(BambuPrinter).order_by(BambuPrinter.name)).all()
    return [public_bambu_printer_dict(printer) for printer in printers]


@router.post("/bambu/printers")
def create_bambu_printer(payload: BambuPrinterCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    access_code = data.pop("access_code", None)
    _check_connection(db, data)
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
    _check_connection(db, data)
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


@router.post("/bambu/printers/{item_id}/print-preflight")
def bambu_print_preflight(item_id: int, payload: BambuPrintStartRequest, db: Session = Depends(get_db)):
    item = get_or_404(db, BambuPrinter, item_id)
    return preflight_bambu_print_start(db, item, payload.local_upload_path)


@router.post("/bambu/printers/{item_id}/print-files/upload")
def bambu_print_file_upload(item_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    get_or_404(db, BambuPrinter, item_id)
    return save_bambu_print_upload(file)


@router.post("/bambu/printers/{item_id}/start-print")
def bambu_start_print(item_id: int, payload: BambuPrintStartRequest, db: Session = Depends(get_db)):
    item = get_or_404(db, BambuPrinter, item_id)
    return start_bambu_remote_print(db, item, payload)



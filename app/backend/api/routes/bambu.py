from fastapi import APIRouter
from api.routes_shared import *

router = APIRouter()

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



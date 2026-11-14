from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import BambuPrinter, BridgeCommand, PrinterBridge
from services.bridge_service import authenticate_bridge, command_file, create_bridge, handle_sync, public_bridge_dict, queue_command

router = APIRouter(tags=["bridges"])

PRINTER_ACTIONS = {"pause", "resume", "stop"}


class BridgeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class PrinterAction(BaseModel):
    action: str


# ----- management (normal signed-in user) ------------------------------------------
@router.get("/bridges")
def list_bridges(db: Session = Depends(get_db)) -> list[dict]:
    return [public_bridge_dict(db, bridge) for bridge in db.scalars(select(PrinterBridge).order_by(PrinterBridge.name)).all()]


@router.post("/bridges")
def add_bridge(payload: BridgeCreate, db: Session = Depends(get_db)) -> dict:
    bridge, token = create_bridge(db, payload.name)
    # The token is shown exactly once; only its hash is stored.
    return {**public_bridge_dict(db, bridge), "token": token}


@router.post("/bridges/{bridge_id}/revoke")
def revoke_bridge(bridge_id: int, db: Session = Depends(get_db)) -> dict:
    bridge = db.get(PrinterBridge, bridge_id)
    if bridge is None:
        raise HTTPException(status_code=404, detail="Bridge niet gevonden.")
    bridge.revoked = True
    for command in db.scalars(select(BridgeCommand).where(BridgeCommand.bridge_id == bridge.id, BridgeCommand.status.in_(["wachtrij", "opgehaald"]))).all():
        command.status = "mislukt"
        command.result_message = "Bridge ingetrokken."
    db.commit()
    return public_bridge_dict(db, bridge)


@router.post("/bambu/printers/{printer_id}/bridge-action")
def bridge_printer_action(printer_id: int, payload: PrinterAction, db: Session = Depends(get_db)) -> dict:
    printer = db.get(BambuPrinter, printer_id)
    if printer is None:
        raise HTTPException(status_code=404, detail="Printer niet gevonden.")
    if payload.action not in PRINTER_ACTIONS:
        raise HTTPException(status_code=400, detail="Kies pauzeren, hervatten of stoppen.")
    command = queue_command(db, printer, payload.action)
    return {"command_id": command.id, "status": command.status}


@router.get("/bambu/printers/{printer_id}/bridge-commands")
def bridge_printer_commands(printer_id: int, db: Session = Depends(get_db)) -> list[dict]:
    commands = db.scalars(select(BridgeCommand).where(BridgeCommand.printer_id == printer_id).order_by(BridgeCommand.id.desc()).limit(10)).all()
    return [
        {"id": item.id, "kind": item.kind, "status": item.status, "result_message": item.result_message, "created_at": item.created_at.isoformat()}
        for item in commands
    ]


# ----- the agent itself (bridge token instead of a user session) ----------------------
@router.post("/bridge-agent/sync")
async def bridge_agent_sync(request: Request, db: Session = Depends(get_db)) -> dict:
    bridge = authenticate_bridge(db, request.headers.get("authorization"))
    try:
        body = await request.json()
    except ValueError:
        body = {}
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else None)
    return handle_sync(db, bridge, body if isinstance(body, dict) else {}, client_ip)


@router.get("/bridge-agent/files/{command_id}")
def bridge_agent_file(command_id: int, request: Request, db: Session = Depends(get_db)) -> FileResponse:
    bridge = authenticate_bridge(db, request.headers.get("authorization"))
    path = command_file(db, bridge, command_id)
    return FileResponse(path, media_type="application/octet-stream", filename=path.name)

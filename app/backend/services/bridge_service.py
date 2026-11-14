"""Bambu printers outside the local network, via a bridge agent.

Bambu's LAN mode only works inside the printer's own network. A bridge is a small
agent (ops/bambu-bridge) on a computer in that network. It keeps an MQTT
connection to its printers and syncs with this app over outgoing HTTPS:

    agent -> POST /bridge-agent/sync  {reports, results}
    app   -> {printers, commands}

So no port has to be opened at the remote location, and the app never needs to
reach that network. Commands are queued here and picked up on the next sync.
"""

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.credentials import decrypt_credential
from models import BambuPrinter, BridgeCommand, PrinterBridge

TOKEN_PREFIX = "pmb_"
ONLINE_WINDOW = timedelta(seconds=90)
COMMAND_KINDS = {"pushall", "pause", "resume", "stop", "print"}
STALE_PICKED_AFTER = timedelta(minutes=10)
MAX_COMMANDS_PER_SYNC = 10


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_bridge(db: Session, name: str) -> tuple[PrinterBridge, str]:
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    bridge = PrinterBridge(name=name.strip() or "Bridge", token_hash=hash_token(token), token_hint=token[-6:], created_at=_now())
    db.add(bridge)
    db.commit()
    db.refresh(bridge)
    return bridge, token


def bridge_online(bridge: PrinterBridge | None, now: datetime | None = None) -> bool:
    seen = _aware(bridge.last_seen_at) if bridge else None
    return bool(bridge and not bridge.revoked and seen and (now or _now()) - seen <= ONLINE_WINDOW)


def public_bridge_dict(db: Session, bridge: PrinterBridge) -> dict:
    printers = db.scalars(select(BambuPrinter).where(BambuPrinter.bridge_id == bridge.id).order_by(BambuPrinter.name)).all()
    return {
        "id": bridge.id,
        "name": bridge.name,
        "token_hint": f"…{bridge.token_hint}",
        "agent_version": bridge.agent_version,
        "last_seen_at": bridge.last_seen_at.isoformat() if bridge.last_seen_at else None,
        "online": bridge_online(bridge),
        "revoked": bridge.revoked,
        "printers": [{"id": printer.id, "name": printer.name} for printer in printers],
    }


def authenticate_bridge(db: Session, authorization: str | None) -> PrinterBridge:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token.startswith(TOKEN_PREFIX):
        raise HTTPException(status_code=401, detail="Ongeldige bridge-token.")
    bridge = db.scalar(select(PrinterBridge).where(PrinterBridge.token_hash == hash_token(token)))
    if bridge is None or bridge.revoked or not hmac.compare_digest(bridge.token_hash, hash_token(token)):
        raise HTTPException(status_code=401, detail="Ongeldige bridge-token.")
    return bridge


def queue_command(db: Session, printer: BambuPrinter, kind: str, payload: dict | None = None) -> BridgeCommand:
    if kind not in COMMAND_KINDS:
        raise HTTPException(status_code=400, detail=f"Onbekend bridge-commando: {kind}")
    if printer.connection_mode != "bridge" or printer.bridge_id is None:
        raise HTTPException(status_code=400, detail="Deze printer is niet via een bridge gekoppeld.")
    if kind == "pushall":
        waiting = db.scalar(
            select(BridgeCommand).where(BridgeCommand.printer_id == printer.id, BridgeCommand.kind == "pushall", BridgeCommand.status == "wachtrij")
        )
        if waiting is not None:
            return waiting
    command = BridgeCommand(
        bridge_id=printer.bridge_id,
        printer_id=printer.id,
        kind=kind,
        payload_json=json.dumps(payload, separators=(",", ":")) if payload else None,
        created_at=_now(),
    )
    db.add(command)
    db.commit()
    db.refresh(command)
    return command


def bridge_status_note(db: Session, printer: BambuPrinter) -> str:
    bridge = db.get(PrinterBridge, printer.bridge_id) if printer.bridge_id else None
    if bridge is None:
        return "Geen bridge gekozen voor deze printer."
    if not bridge_online(bridge):
        return f"Bridge '{bridge.name}' is offline; de opdracht wordt uitgevoerd zodra hij weer verbinding maakt."
    return f"Opdracht staat klaar voor bridge '{bridge.name}' en wordt binnen enkele seconden uitgevoerd."


def _printer_config(printer: BambuPrinter) -> dict:
    return {
        "id": printer.id,
        "name": printer.name,
        "host": printer.host,
        "mqtt_port": int(printer.mqtt_port or 8883),
        "serial_number": (printer.serial_number or "").strip(),
        # The agent needs the LAN access code to talk to the printer; it only travels over the
        # authenticated HTTPS sync and is never written to disk by the agent.
        "access_code": decrypt_credential(printer.access_code_encrypted) if printer.access_code_encrypted else "",
    }


def _command_dict(command: BridgeCommand) -> dict:
    payload = json.loads(command.payload_json) if command.payload_json else {}
    data = {"id": command.id, "printer_id": command.printer_id, "kind": command.kind, "payload": payload}
    if command.kind == "print":
        data["file_url"] = f"/bridge-agent/files/{command.id}"
    return data


def handle_sync(db: Session, bridge: PrinterBridge, body: dict, client_ip: str | None = None) -> dict:
    from services.bambu_printers import apply_bambu_status_payload

    now = _now()
    bridge.last_seen_at = now
    bridge.agent_version = str(body.get("agent_version") or "")[:50] or None
    bridge.last_ip = (client_ip or "")[:64] or None
    printers = {printer.id: printer for printer in db.scalars(select(BambuPrinter).where(BambuPrinter.bridge_id == bridge.id, BambuPrinter.active.is_(True))).all()}

    for report in body.get("reports") or []:
        printer = printers.get(report.get("printer_id")) if isinstance(report, dict) else None
        if printer is None:
            continue
        if report.get("error"):
            printer.last_status = "bridge_fout"
            printer.status_message = f"Bridge: {str(report['error'])[:900]}"
            continue
        if isinstance(report.get("payload"), dict):
            apply_bambu_status_payload(printer, report["payload"])
            printer.status_message = f"Status via bridge '{bridge.name}'."

    for result in body.get("results") or []:
        command = db.get(BridgeCommand, result.get("command_id")) if isinstance(result, dict) else None
        if command is None or command.bridge_id != bridge.id:
            continue
        command.status = "geslaagd" if result.get("ok") else "mislukt"
        command.result_message = str(result.get("message") or "")[:1000] or None
        command.finished_at = now
        printer = printers.get(command.printer_id)
        if printer is not None and command.kind == "print":
            printer.last_status = "printstart_verzonden" if result.get("ok") else "printstart_mislukt"
            printer.status_message = command.result_message or ("Printstart via bridge verzonden." if result.get("ok") else "Printstart via bridge mislukt.")

    # Commands picked up long ago without a result: the agent restarted. Offer them again,
    # except print starts, which must never run twice by accident.
    for command in db.scalars(select(BridgeCommand).where(BridgeCommand.bridge_id == bridge.id, BridgeCommand.status == "opgehaald")).all():
        if _aware(command.picked_at) and now - _aware(command.picked_at) > STALE_PICKED_AFTER:
            if command.kind == "print":
                command.status = "mislukt"
                command.result_message = "Geen bevestiging van de bridge ontvangen. Controleer de printer voordat je opnieuw start."
                command.finished_at = now
            else:
                command.status = "wachtrij"
    db.flush()

    commands = db.scalars(
        select(BridgeCommand)
        .where(BridgeCommand.bridge_id == bridge.id, BridgeCommand.status == "wachtrij")
        .order_by(BridgeCommand.id)
        .limit(MAX_COMMANDS_PER_SYNC)
    ).all()
    for command in commands:
        command.status = "opgehaald"
        command.picked_at = now
    response = {
        "poll_seconds": 10,
        "printers": [_printer_config(printer) for printer in printers.values()],
        "commands": [_command_dict(command) for command in commands],
    }
    db.commit()
    return response


def command_file(db: Session, bridge: PrinterBridge, command_id: int) -> Path:
    command = db.get(BridgeCommand, command_id)
    if command is None or command.bridge_id != bridge.id or command.kind != "print" or command.status != "opgehaald":
        raise HTTPException(status_code=404, detail="Bestand niet gevonden.")
    payload = json.loads(command.payload_json or "{}")
    root = Path("uploads").resolve()
    path = (root / str(payload.get("local_upload_path") or "").removeprefix("/uploads/")).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Printbestand niet gevonden op de server.")
    return path

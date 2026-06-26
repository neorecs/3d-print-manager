import socket
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import BambuPrinter


def public_bambu_printer_dict(printer: BambuPrinter) -> dict:
    return {
        "id": printer.id,
        "name": printer.name,
        "model": printer.model,
        "serial_number": printer.serial_number,
        "host": printer.host,
        "mqtt_port": printer.mqtt_port,
        "has_access_code": bool(printer.access_code_encrypted),
        "connection_mode": printer.connection_mode,
        "location": printer.location,
        "active": printer.active,
        "last_status": printer.last_status,
        "status_message": printer.status_message,
        "last_seen_at": printer.last_seen_at.isoformat() if printer.last_seen_at else None,
        "created_at": printer.created_at.isoformat() if printer.created_at else None,
        "updated_at": printer.updated_at.isoformat() if printer.updated_at else None,
    }


def test_bambu_lan_connection(db: Session, printer: BambuPrinter, timeout_seconds: float = 3.0) -> dict:
    if not printer.active:
        printer.last_status = "inactief"
        printer.status_message = "Printer staat inactief in de app."
        db.commit()
        db.refresh(printer)
        return public_bambu_printer_dict(printer)

    try:
        with socket.create_connection((printer.host, int(printer.mqtt_port or 8883)), timeout=timeout_seconds):
            printer.last_status = "bereikbaar"
            printer.status_message = f"LAN-poort {printer.mqtt_port} is bereikbaar. MQTT-statusfeed wordt later uitgebreid."
            printer.last_seen_at = datetime.now(timezone.utc)
    except OSError as exc:
        printer.last_status = "niet_bereikbaar"
        printer.status_message = f"Geen verbinding met {printer.host}:{printer.mqtt_port}. Controleer IP, LAN mode en netwerk. Details: {exc}"

    db.commit()
    db.refresh(printer)
    return public_bambu_printer_dict(printer)

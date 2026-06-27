import json
import socket
import ssl
import threading
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.credentials import decrypt_credential
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
        "printer_state": printer.printer_state,
        "print_progress": printer.print_progress,
        "nozzle_temperature": printer.nozzle_temperature,
        "bed_temperature": printer.bed_temperature,
        "chamber_temperature": printer.chamber_temperature,
        "current_task": printer.current_task,
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


def refresh_bambu_mqtt_status(db: Session, printer: BambuPrinter, timeout_seconds: float = 8.0) -> dict:
    if not printer.serial_number:
        raise HTTPException(
            status_code=400,
            detail="Serienummer ontbreekt. Vul het Bambu serienummer in voordat MQTT-status kan worden opgehaald.",
        )
    if not printer.access_code_encrypted:
        raise HTTPException(
            status_code=400,
            detail="Access code ontbreekt. Vul de Bambu LAN access code in voordat MQTT-status kan worden opgehaald.",
        )

    access_code = decrypt_credential(printer.access_code_encrypted)
    serial = printer.serial_number.strip()
    topic = f"device/{serial}/report"
    received: dict[str, object] = {}
    error: dict[str, str] = {}
    done = threading.Event()

    def on_connect(client, _userdata, _flags, reason_code, _properties=None):
        if int(reason_code) != 0:
            error["message"] = f"MQTT verbinding geweigerd: {reason_code}"
            done.set()
            return
        client.subscribe(topic)

    def on_message(client, _userdata, message):
        try:
            received["payload"] = json.loads(message.payload.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            error["message"] = f"MQTT payload kon niet worden gelezen: {exc}"
        finally:
            done.set()
            client.disconnect()

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"3d-print-manager-{printer.id}")
        client.username_pw_set("bblp", access_code)
        client.tls_set(cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(printer.host, int(printer.mqtt_port or 8883), keepalive=30)
        client.loop_start()
        done.wait(timeout_seconds)
        client.loop_stop()
        client.disconnect()
    except Exception as exc:  # noqa: BLE001
        printer.last_status = "mqtt_fout"
        printer.status_message = f"MQTT-status ophalen mislukt: {exc}"
        db.commit()
        db.refresh(printer)
        return public_bambu_printer_dict(printer)

    if error.get("message"):
        printer.last_status = "mqtt_fout"
        printer.status_message = error["message"]
    elif not received.get("payload"):
        printer.last_status = "mqtt_timeout"
        printer.status_message = f"Geen MQTT-status ontvangen op topic {topic} binnen {int(timeout_seconds)} seconden."
    else:
        apply_bambu_status_payload(printer, received["payload"])

    db.commit()
    db.refresh(printer)
    return public_bambu_printer_dict(printer)


def apply_bambu_status_payload(printer: BambuPrinter, payload: object) -> None:
    data = payload if isinstance(payload, dict) else {}
    print_data = data.get("print") if isinstance(data.get("print"), dict) else data

    printer.last_status = "status_opgehaald"
    printer.status_message = "MQTT-status ontvangen."
    printer.last_seen_at = datetime.now(timezone.utc)
    printer.printer_state = _string_value(print_data.get("gcode_state") or print_data.get("mc_print_stage") or print_data.get("stg_cur"))
    printer.print_progress = _int_value(print_data.get("mc_percent") or print_data.get("progress"))
    printer.nozzle_temperature = _float_value(print_data.get("nozzle_temper") or print_data.get("nozzle_temperature"))
    printer.bed_temperature = _float_value(print_data.get("bed_temper") or print_data.get("bed_temperature"))
    printer.chamber_temperature = _float_value(print_data.get("chamber_temper") or print_data.get("chamber_temperature"))
    printer.current_task = _string_value(print_data.get("subtask_name") or print_data.get("gcode_file") or print_data.get("file"))


def _string_value(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_value(value: object) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _float_value(value: object) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(str(value))
    except (TypeError, ValueError):
        return None

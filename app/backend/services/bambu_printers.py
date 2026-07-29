import json
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from ftplib import FTP_TLS
from pathlib import Path
from urllib.parse import quote

import paho.mqtt.client as mqtt
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from core.credentials import decrypt_credential
from models import BambuPrinter

PRINT_START_CONFIRMATION = "START PRINT"
BUSY_STATES = {"RUNNING", "PRINTING", "PAUSE", "PAUSED", "PREPARE", "SLICING", "BUSY"}
READY_STATES = {"IDLE", "FINISH", "FINISHED", "FAILED", "STOPPED"}
BAMBU_PRINT_UPLOAD_ROOT = Path("uploads/bambu_print_files")
PRODUCT_PRINT_UPLOAD_ROOT = Path("uploads/product_print_files")
ALLOWED_BAMBU_PRINT_SUFFIXES = (".gcode.3mf", "_gcode.3mf")
MAX_BAMBU_PRINT_UPLOAD_BYTES = 500 * 1024 * 1024


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
        if not _mqtt_reason_code_success(reason_code):
            error["message"] = f"MQTT verbinding geweigerd: {reason_code}"
            done.set()
            return
        client.subscribe(topic)
        client.publish(
            f"device/{serial}/request",
            json.dumps(
                {
                    "pushing": {
                        "sequence_id": str(uuid.uuid4()),
                        "command": "pushall",
                        "version": 1,
                        "push_target": 1,
                    }
                }
            ),
            qos=0,
        )

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
        printer.printer_state = None
        db.commit()
        db.refresh(printer)
        return public_bambu_printer_dict(printer)

    if error.get("message"):
        printer.last_status = "mqtt_fout"
        printer.status_message = error["message"]
        printer.printer_state = None
    elif not received.get("payload"):
        printer.last_status = "mqtt_timeout"
        printer.status_message = f"Geen MQTT-status ontvangen op topic {topic} binnen {int(timeout_seconds)} seconden."
        printer.printer_state = None
    else:
        apply_bambu_status_payload(printer, received["payload"])

    db.commit()
    db.refresh(printer)
    return public_bambu_printer_dict(printer)


def preflight_bambu_print_start(db: Session, printer: BambuPrinter, file_path: str, *, refresh_status: bool = True) -> dict:
    if refresh_status and printer.active and printer.serial_number and printer.access_code_encrypted:
        refresh_bambu_mqtt_status(db, printer, timeout_seconds=8.0)

    checks = _bambu_print_preflight_checks(printer, file_path)
    ok = all(check["ok"] for check in checks if check["level"] == "error")
    return {
        "ok": ok,
        "printer": public_bambu_printer_dict(printer),
        "file_path": file_path,
        "confirmation_required": PRINT_START_CONFIRMATION,
        "checks": checks,
        "message": "Preflight akkoord. Printer is vrij en de print kan worden gestart." if ok else "Preflight blokkeert printstart. Los de rode controles eerst op.",
    }


def save_bambu_print_upload(file: UploadFile) -> dict:
    original_name = Path(file.filename or "print.gcode.3mf").name
    lower_name = original_name.lower()
    if not lower_name.endswith(ALLOWED_BAMBU_PRINT_SUFFIXES):
        raise HTTPException(
            status_code=400,
            detail="Upload een door Bambu Studio voorbereid .gcode.3mf bestand. Een gewone STL/3MF zonder slicing kan de printer niet direct starten.",
        )

    BAMBU_PRINT_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_bambu_filename(original_name)
    target_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}-{safe_name}"
    target_path = BAMBU_PRINT_UPLOAD_ROOT / target_name
    size = 0

    with target_path.open("wb") as handle:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_BAMBU_PRINT_UPLOAD_BYTES:
                target_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Printbestand is te groot. Maximum is 500 MB.")
            handle.write(chunk)

    printer_file_path = f"file:///sdcard/{quote(target_name)}"
    return {
        "ok": True,
        "local_upload_path": f"/uploads/bambu_print_files/{target_name}",
        "file_path": printer_file_path,
        "filename": target_name,
        "original_filename": original_name,
        "size_bytes": size,
        "message": "Printbestand opgeslagen in de app. Bij printstart uploadt de app dit bestand eerst naar de printer.",
    }


def start_bambu_sdcard_print(db: Session, printer: BambuPrinter, payload) -> dict:
    preflight = preflight_bambu_print_start(db, printer, payload.file_path)
    if not preflight["ok"]:
        raise HTTPException(status_code=400, detail=preflight)
    if (payload.confirmation_text or "").strip().upper() != PRINT_START_CONFIRMATION:
        raise HTTPException(
            status_code=400,
            detail=f"Bevestiging ontbreekt. Typ exact '{PRINT_START_CONFIRMATION}' voordat de app een print mag starten.",
        )

    if payload.local_upload_path:
        uploaded_file_path = _upload_local_file_to_bambu_printer(printer, payload.local_upload_path)
        payload.file_path = uploaded_file_path

    access_code = decrypt_credential(printer.access_code_encrypted or "")
    serial = (printer.serial_number or "").strip()
    request_id = str(uuid.uuid4())
    command = {
        "print": {
            "sequence_id": request_id,
            "command": "project_file",
            "url": payload.file_path.strip(),
            "param": payload.plate.strip() or "Metadata/plate_1.gcode",
            "subtask_id": "0",
            "use_ams": bool(payload.use_ams),
            "timelapse": bool(payload.timelapse),
            "flow_cali": bool(payload.flow_cali),
            "bed_leveling": bool(payload.bed_leveling),
            "layer_inspect": bool(payload.layer_inspect),
            "vibration_cali": bool(payload.vibration_cali),
        }
    }

    _publish_bambu_mqtt_command(printer, access_code, serial, command)
    printer.last_status = "printstart_verzonden"
    printer.status_message = f"Printstart verzonden voor {payload.file_path.strip()}. Controleer printerstatus of Bambu Studio voor bevestiging."
    printer.current_task = payload.file_path.strip().replace("file:///sdcard/", "")
    printer.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(printer)
    return {
        "ok": True,
        "request_id": request_id,
        "message": printer.status_message,
        "printer": public_bambu_printer_dict(printer),
        "mqtt_topic": f"device/{serial}/request",
    }


class _ImplicitFTP_TLS(FTP_TLS):
    def connect(self, host="", port=0, timeout=-999, source_address=None):
        if port == 0:
            port = 990
        super().connect(host, port, timeout, source_address)
        self.sock = self.context.wrap_socket(self.sock, server_hostname=self.host)
        self.file = self.sock.makefile("r", encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome


def _upload_local_file_to_bambu_printer(printer: BambuPrinter, local_upload_path: str) -> str:
    access_code = decrypt_credential(printer.access_code_encrypted or "")
    if not access_code:
        raise HTTPException(status_code=400, detail="Access code ontbreekt. Uploaden naar de printer kan niet zonder LAN access code.")

    relative = local_upload_path.removeprefix("/uploads/")
    source_path = (Path("uploads") / relative).resolve()
    allowed_roots = {BAMBU_PRINT_UPLOAD_ROOT.resolve(), PRODUCT_PRINT_UPLOAD_ROOT.resolve()}
    if not source_path.is_file() or not any(root in source_path.parents for root in allowed_roots):
        raise HTTPException(status_code=400, detail="Geupload printbestand kon niet worden gevonden in de app.")

    remote_filename = _bambu_remote_print_filename(source_path)
    remote_path = _upload_local_file_to_bambu_printer_with_curl(printer, access_code, source_path, remote_filename)
    if remote_path:
        return f"ftp:///{quote(remote_path, safe='/')}"

    try:
        ftp = _ImplicitFTP_TLS(timeout=30)
        ftp.context.check_hostname = False
        ftp.context.verify_mode = ssl.CERT_NONE
        ftp.connect(printer.host, 990)
        ftp.login("bblp", access_code)
        ftp.prot_p()
        with source_path.open("rb") as handle:
            ftp.storbinary(f"STOR {remote_filename}", handle)
        ftp.quit()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Upload naar printer via FTPS mislukt: {exc}") from exc

    return f"ftp:///{quote(remote_filename)}"


def _upload_local_file_to_bambu_printer_with_curl(printer: BambuPrinter, access_code: str, source_path: Path, filename: str) -> str | None:
    try:
        subprocess.run(["curl", "--version"], check=True, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None

    file_size = source_path.stat().st_size
    max_time = min(max(300, int(file_size / 75_000)), 1800)
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as temp_dir:
        upload_source = Path(temp_dir) / filename
        shutil.copyfile(source_path, upload_source)
        for remote_dir, remote_path in (("", filename), ("models/", f"models/{filename}")):
            target_url = f"ftps://{printer.host}:990/{remote_dir}"
            command = [
                "curl",
                "--fail",
                "--silent",
                "--show-error",
                "--ftp-pasv",
                "--insecure",
                "--ssl-reqd",
                "--connect-timeout",
                "20",
                "--max-time",
                str(max_time),
                "--user",
                f"bblp:{access_code}",
                "--upload-file",
                str(upload_source),
                target_url,
            ]
            try:
                subprocess.run(command, check=True, capture_output=True, text=True, timeout=max_time + 30)
                return remote_path
            except subprocess.CalledProcessError as exc:
                detail = (exc.stderr or exc.stdout or "").strip() or f"curl exit code {exc.returncode}"
                failures.append(f"{remote_path}: {detail}")
            except subprocess.TimeoutExpired as exc:
                raise HTTPException(status_code=504, detail="Upload naar printer via FTPS duurde te lang en is afgebroken.") from exc

    raise HTTPException(status_code=502, detail=f"Upload naar printer via FTPS mislukt: {' | '.join(failures)}")


def _bambu_remote_print_filename(source_path: Path) -> str:
    token = uuid.uuid5(uuid.NAMESPACE_URL, source_path.name).hex[:12]
    return f"pm-{token}.gcode.3mf"


def _publish_bambu_mqtt_command(printer: BambuPrinter, access_code: str, serial: str, command: dict, timeout_seconds: float = 5.0) -> None:
    error: dict[str, str] = {}
    connected = threading.Event()
    published = threading.Event()

    def on_connect(client, _userdata, _flags, reason_code, _properties=None):
        if not _mqtt_reason_code_success(reason_code):
            error["message"] = f"MQTT verbinding geweigerd: {reason_code}"
            connected.set()
            return
        connected.set()
        result = client.publish(f"device/{serial}/request", json.dumps(command), qos=0)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            error["message"] = f"MQTT publish mislukt: {result.rc}"

    def on_publish(client, _userdata, _mid, _reason_code=None, _properties=None):
        published.set()
        client.disconnect()

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"3d-print-manager-start-{printer.id}")
        client.username_pw_set("bblp", access_code)
        client.tls_set(cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)
        client.on_connect = on_connect
        client.on_publish = on_publish
        client.connect(printer.host, int(printer.mqtt_port or 8883), keepalive=30)
        client.loop_start()
        connected.wait(timeout_seconds)
        published.wait(timeout_seconds)
        client.loop_stop()
        client.disconnect()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"MQTT printstart mislukt: {exc}") from exc

    if error.get("message"):
        raise HTTPException(status_code=502, detail=error["message"])
    if not connected.is_set() or not published.is_set():
        raise HTTPException(status_code=504, detail="MQTT printstart timeout. Controleer LAN mode, Developer Mode, access code en printerstatus.")


def _mqtt_reason_code_success(reason_code: object) -> bool:
    if hasattr(reason_code, "is_failure"):
        return not bool(reason_code.is_failure)
    try:
        return int(reason_code) == 0
    except (TypeError, ValueError):
        return str(reason_code).strip().lower() in {"0", "success", "normal disconnection"}


def _bambu_print_preflight_checks(printer: BambuPrinter, file_path: str) -> list[dict]:
    checks: list[dict] = []

    def add(name: str, ok: bool, message: str, level: str = "error") -> None:
        checks.append({"name": name, "ok": ok, "message": message, "level": level})

    normalized_path = (file_path or "").strip()
    state = (printer.printer_state or "").strip().upper()

    add("Printer actief", bool(printer.active), "Printer staat actief in de app." if printer.active else "Printer staat inactief in de app.")
    add("Host ingevuld", bool((printer.host or "").strip()), "Host/IP is ingevuld." if (printer.host or "").strip() else "Vul het lokale IP-adres of hostname van de printer in.")
    add("Serienummer ingevuld", bool((printer.serial_number or "").strip()), "Serienummer is ingevuld." if (printer.serial_number or "").strip() else "Vul het Bambu serienummer in voor MQTT-topic device/{serial}/request.")
    add("Access code opgeslagen", bool(printer.access_code_encrypted), "LAN access code is opgeslagen." if printer.access_code_encrypted else "Sla de LAN access code op voordat je opdrachten kunt sturen.")
    add("MQTT-poort", int(printer.mqtt_port or 0) > 0, f"MQTT-poort {printer.mqtt_port} wordt gebruikt." if int(printer.mqtt_port or 0) > 0 else "MQTT-poort ontbreekt.")
    add(
        "SD-bestandspad",
        normalized_path.startswith("file:///sdcard/") and normalized_path.lower().endswith(".3mf"),
        "Bestandspad wijst naar een voorbereid 3MF-project op de printer/SD." if normalized_path.startswith("file:///sdcard/") and normalized_path.lower().endswith(".3mf") else "Vul het volledige bestandspad in, bijvoorbeeld file:///sdcard/bestand.gcode.3mf. Alleen file:///sdcard/ is nog geen bestand.",
    )
    if not state:
        add("Printerstatus", False, "Status is onbekend. De app kon niet bevestigen dat de printer vrij is, dus printstart wordt geblokkeerd.")
    elif state in BUSY_STATES:
        add("Printer niet bezig", False, f"Printer lijkt bezig of gepauzeerd ({state}). Start geen nieuwe print via de site.")
    elif state in READY_STATES:
        add("Printer niet bezig", True, f"Printerstatus is {state}. De printer lijkt vrij.")
    else:
        add("Printerstatus herkend", False, f"Printerstatus is {state}. De app herkent deze status nog niet betrouwbaar als vrij, dus printstart wordt geblokkeerd.")

    return checks


def _safe_bambu_filename(filename: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in "._-" else "-" for char in filename.strip())
    return cleaned.strip(".-") or "print.gcode.3mf"


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

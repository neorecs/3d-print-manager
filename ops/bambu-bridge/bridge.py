"""3D Print Manager - Bambu bridge agent.

Runs on a small computer (NAS, Raspberry Pi, mini-pc) in the network where the
Bambu printers are. It keeps a local MQTT connection to each printer (LAN mode +
Developer Mode) and syncs with the app over outgoing HTTPS. Nothing has to be
opened in this network.

Settings (environment):
  BRIDGE_APP_URL   https://jouw-domein (the app, reachable from here)
  BRIDGE_TOKEN     the pmb_... token shown once when the bridge was created
  BRIDGE_POLL_SECONDS (optional, default from the app, normally 10)

Printer settings (IP, serial, access code) come from the app, so they are managed
in one place. They are kept in memory only.
"""

import json
import logging
import os
import shutil
import signal
import ssl
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from ftplib import FTP_TLS
from pathlib import Path
from urllib.parse import quote

import paho.mqtt.client as mqtt

VERSION = "1.0.0"
READY_STATES = {"IDLE", "FINISH", "FINISHED", "FAILED", "STOPPED"}
logger = logging.getLogger("bambu-bridge")


def deep_merge(target: dict, update: dict) -> dict:
    """Bambu sends small deltas after the first full report; keep a complete picture."""
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_merge(target[key], value)
        else:
            target[key] = value
    return target


class PrinterLink:
    """One MQTT connection to one printer, reconnecting by itself."""

    def __init__(self, config: dict):
        self.config = config
        self.state: dict = {}
        self.error: str | None = None
        self.connected = threading.Event()
        self.lock = threading.Lock()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"pm-bridge-{config['id']}-{uuid.uuid4().hex[:6]}")
        self.client.username_pw_set("bblp", config["access_code"])
        self.client.tls_set(cert_reqs=ssl.CERT_NONE)
        self.client.tls_insecure_set(True)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.reconnect_delay_set(min_delay=2, max_delay=60)

    @property
    def serial(self) -> str:
        return self.config["serial_number"]

    def start(self) -> None:
        self.client.connect_async(self.config["host"], int(self.config["mqtt_port"]), keepalive=30)
        self.client.loop_start()

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(self, client, _userdata, _flags, reason_code, _properties=None):
        if getattr(reason_code, "is_failure", False):
            self.error = f"MQTT geweigerd door printer: {reason_code}. Klopt de access code?"
            return
        self.error = None
        client.subscribe(f"device/{self.serial}/report")
        self.connected.set()
        self.publish({"pushing": {"sequence_id": "0", "command": "pushall", "version": 1, "push_target": 1}})

    def _on_disconnect(self, _client, _userdata, _flags, reason_code, _properties=None):
        self.connected.clear()
        if reason_code != 0:
            self.error = f"Verbinding met printer verbroken ({reason_code}); opnieuw verbinden..."

    def _on_message(self, _client, _userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except ValueError:
            return
        with self.lock:
            deep_merge(self.state, payload)

    def publish(self, command: dict) -> None:
        info = self.client.publish(f"device/{self.serial}/request", json.dumps(command), qos=1)
        info.wait_for_publish(timeout=5)
        if not info.is_published():
            raise RuntimeError("Commando kon niet naar de printer worden gestuurd.")

    def report(self) -> dict:
        if self.error and not self.connected.is_set():
            return {"printer_id": self.config["id"], "error": self.error}
        with self.lock:
            snapshot = json.loads(json.dumps(self.state)) if self.state else None
        return {"printer_id": self.config["id"], "payload": snapshot} if snapshot else {"printer_id": self.config["id"]}

    def gcode_state(self) -> str:
        with self.lock:
            return str((self.state.get("print") or {}).get("gcode_state") or "").upper()


class Bridge:
    def __init__(self, app_url: str, token: str):
        self.app_url = app_url.rstrip("/")
        self.token = token
        self.links: dict[int, PrinterLink] = {}
        self.results: list[dict] = []
        self.poll_seconds = int(os.getenv("BRIDGE_POLL_SECONDS", "0")) or 10
        self.running = True

    # ----- talking to the app -----
    def _request(self, method: str, path: str, body: dict | None = None, timeout: int = 30):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            f"{self.app_url}/api{path}",
            data=data,
            method=method,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json", "User-Agent": f"pm-bambu-bridge/{VERSION}"},
        )
        return urllib.request.urlopen(request, timeout=timeout)

    def sync(self) -> dict:
        body = {"agent_version": VERSION, "reports": [link.report() for link in self.links.values()], "results": self.results}
        with self._request("POST", "/bridge-agent/sync", body) as response:
            answer = json.loads(response.read().decode("utf-8"))
        self.results = []
        return answer

    def download(self, file_url: str, target: Path) -> None:
        with self._request("GET", file_url, timeout=600) as response, target.open("wb") as handle:
            shutil.copyfileobj(response, handle)

    # ----- printers -----
    def apply_printers(self, configs: list[dict]) -> None:
        wanted = {config["id"]: config for config in configs}
        for printer_id in list(self.links):
            if printer_id not in wanted or self.links[printer_id].config != wanted[printer_id]:
                self.links.pop(printer_id).stop()
        for printer_id, config in wanted.items():
            if printer_id in self.links:
                continue
            if not (config.get("host") and config.get("serial_number") and config.get("access_code")):
                logger.warning("Printer %s mist host, serienummer of access code in de app", config.get("name"))
                continue
            link = PrinterLink(config)
            link.start()
            self.links[printer_id] = link
            logger.info("Verbinden met %s (%s)", config["name"], config["host"])

    def run_command(self, command: dict) -> None:
        link = self.links.get(command["printer_id"])
        try:
            if link is None:
                raise RuntimeError("Printer is niet verbonden met de bridge.")
            kind = command["kind"]
            if kind == "pushall":
                link.publish({"pushing": {"sequence_id": str(command["id"]), "command": "pushall", "version": 1, "push_target": 1}})
                message = "Volledige status opgevraagd."
            elif kind in {"pause", "resume", "stop"}:
                link.publish({"print": {"sequence_id": str(command["id"]), "command": kind, "param": ""}})
                message = {"pause": "Pauze verstuurd.", "resume": "Hervatten verstuurd.", "stop": "Stoppen verstuurd."}[kind]
            elif kind == "print":
                message = self.start_print(link, command)
            else:
                raise RuntimeError(f"Onbekend commando {kind}")
            self.results.append({"command_id": command["id"], "ok": True, "message": message})
        except Exception as exc:  # noqa: BLE001 - every failure goes back to the app
            logger.warning("Commando %s mislukt: %s", command.get("id"), exc)
            self.results.append({"command_id": command["id"], "ok": False, "message": str(exc)[:900]})

    def start_print(self, link: PrinterLink, command: dict) -> str:
        state = link.gcode_state()
        if state not in READY_STATES:
            raise RuntimeError(f"Printer is niet vrij (status {state or 'onbekend'}); print niet gestart.")
        payload = command["payload"]
        filename = payload["remote_filename"]
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory) / filename
            self.download(command["file_url"], local)
            upload_to_printer(link.config["host"], link.config["access_code"], local, filename)
        link.publish({"print": {
            "sequence_id": str(command["id"]),
            "command": "project_file",
            "url": f"file:///sdcard/cache/{quote(filename)}",
            "param": payload.get("plate") or "Metadata/plate_1.gcode",
            "subtask_id": "0",
            "use_ams": bool(payload.get("use_ams")),
            "timelapse": bool(payload.get("timelapse")),
            "flow_cali": bool(payload.get("flow_cali")),
            "bed_leveling": bool(payload.get("bed_leveling", True)),
            "layer_inspect": bool(payload.get("layer_inspect", True)),
            "vibration_cali": bool(payload.get("vibration_cali")),
        }})
        return f"Bestand geüpload en printstart verzonden ({filename})."

    def loop(self) -> None:
        logger.info("Bambu bridge %s gestart, app: %s", VERSION, self.app_url)
        backoff = self.poll_seconds
        while self.running:
            try:
                answer = self.sync()
                self.apply_printers(answer.get("printers") or [])
                for command in answer.get("commands") or []:
                    self.run_command(command)
                if not os.getenv("BRIDGE_POLL_SECONDS"):
                    self.poll_seconds = max(int(answer.get("poll_seconds") or 10), 3)
                backoff = self.poll_seconds
                # Report command results right away instead of waiting a full round.
                time.sleep(1 if self.results else self.poll_seconds)
            except urllib.error.HTTPError as exc:
                if exc.code == 401:
                    logger.error("De app weigert de bridge-token. Maak een nieuwe bridge aan en zet BRIDGE_TOKEN opnieuw.")
                else:
                    logger.warning("App gaf fout %s", exc.code)
                backoff = min(backoff * 2, 300)
                time.sleep(backoff)
            except (urllib.error.URLError, OSError, ValueError) as exc:
                logger.warning("App niet bereikbaar: %s", exc)
                backoff = min(backoff * 2, 300)
                time.sleep(backoff)
        for link in self.links.values():
            link.stop()


class _ImplicitFTP_TLS(FTP_TLS):
    def connect(self, host="", port=0, timeout=-999, source_address=None):
        super().connect(host, port or 990, timeout, source_address)
        self.sock = self.context.wrap_socket(self.sock, server_hostname=self.host)
        self.file = self.sock.makefile("r", encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome


def upload_to_printer(host: str, access_code: str, source: Path, filename: str) -> None:
    """FTPS (implicit TLS, port 990) to the printer's cache folder; curl first, it copes best with Bambu's FTPS."""
    if shutil.which("curl"):
        max_time = str(min(max(300, int(source.stat().st_size / 75_000)), 1800))
        result = subprocess.run(
            ["curl", "--fail", "--silent", "--show-error", "--ftp-pasv", "--insecure", "--ssl-reqd",
             "--connect-timeout", "20", "--max-time", max_time, "--user", f"bblp:{access_code}",
             "-T", str(source), f"ftps://{host}:990/cache/{filename}"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return
        logger.warning("curl-upload mislukt (%s), probeer Python FTPS", result.stderr.strip()[:200])
    ftp = _ImplicitFTP_TLS(timeout=30)
    ftp.context.check_hostname = False
    ftp.context.verify_mode = ssl.CERT_NONE
    ftp.connect(host, 990)
    ftp.login("bblp", access_code)
    ftp.prot_p()
    ftp.cwd("cache")
    with source.open("rb") as handle:
        ftp.storbinary(f"STOR {filename}", handle)
    ftp.quit()


def main() -> None:
    logging.basicConfig(level=os.getenv("BRIDGE_LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    app_url, token = os.getenv("BRIDGE_APP_URL", ""), os.getenv("BRIDGE_TOKEN", "")
    if not app_url.startswith("https://") and not os.getenv("BRIDGE_ALLOW_HTTP"):
        raise SystemExit("BRIDGE_APP_URL moet met https:// beginnen (de access codes gaan over deze verbinding).")
    if not token.startswith("pmb_"):
        raise SystemExit("BRIDGE_TOKEN ontbreekt of is ongeldig (begint met pmb_).")
    bridge = Bridge(app_url, token)

    def stop(*_args):
        bridge.running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    bridge.loop()


if __name__ == "__main__":
    main()

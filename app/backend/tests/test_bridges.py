import asyncio
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet
from sqlalchemy import func, select

from support import *

from api.routes.bambu import _check_connection
from api.routes.bridges import bridge_agent_sync
from core.credentials import encrypt_credential
from models import BambuPrinter, BridgeCommand, PrinterBridge
from schemas.common import BambuPrintStartRequest
from services import bridge_service
from services.bambu_printers import refresh_bambu_mqtt_status, start_bambu_remote_print
from services.bridge_service import authenticate_bridge, bridge_online, command_file, create_bridge, handle_sync, queue_command

AGENT_PATH = Path(__file__).resolve().parents[3] / "ops" / "bambu-bridge" / "bridge.py"


def load_agent():
    spec = importlib.util.spec_from_file_location("bambu_bridge_agent", AGENT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["bambu_bridge_agent"] = module
    spec.loader.exec_module(module)
    return module


class FakeRequest:
    def __init__(self, token: str, body: dict):
        self.headers = {"authorization": f"Bearer {token}"}
        self._body = body
        self.client = None

    async def json(self):
        return self._body


class BridgeServiceTests(BackendTestCase):
    def setUp(self) -> None:
        super().setUp()
        os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())
        self.bridge, self.token = create_bridge(self.db, "Werkplaats")
        self.printer = BambuPrinter(
            name="P1S ouders", host="192.168.1.50", serial_number="01P00A000000001",
            access_code_encrypted=encrypt_credential("12345678"), connection_mode="bridge", bridge_id=self.bridge.id,
        )
        self.db.add(self.printer)
        self.db.commit()

    def test_token_is_stored_as_hash_and_checked(self) -> None:
        self.assertNotIn(self.token, self.bridge.token_hash)
        self.assertTrue(self.token.startswith("pmb_"))
        self.assertEqual(authenticate_bridge(self.db, f"Bearer {self.token}").id, self.bridge.id)
        for header in (None, "Bearer pmb_wrong", "Bearer something"):
            with self.assertRaises(HTTPException):
                authenticate_bridge(self.db, header)
        self.bridge.revoked = True
        self.db.commit()
        with self.assertRaises(HTTPException):
            authenticate_bridge(self.db, f"Bearer {self.token}")

    def test_sync_returns_printer_config_and_applies_reports(self) -> None:
        answer = handle_sync(self.db, self.bridge, {
            "agent_version": "1.0.0",
            "reports": [{"printer_id": self.printer.id, "payload": {"print": {"gcode_state": "RUNNING", "mc_percent": 42, "nozzle_temper": 219.5}}}],
        })
        self.assertEqual(answer["printers"][0]["access_code"], "12345678")
        self.assertEqual(answer["printers"][0]["serial_number"], "01P00A000000001")
        self.db.refresh(self.printer)
        self.assertEqual(self.printer.printer_state, "RUNNING")
        self.assertEqual(self.printer.print_progress, 42)
        self.assertTrue(bridge_online(self.db.get(PrinterBridge, self.bridge.id)))

    def test_other_bridges_printers_are_not_exposed_or_updated(self) -> None:
        other, _ = create_bridge(self.db, "Ander")
        answer = handle_sync(self.db, other, {"reports": [{"printer_id": self.printer.id, "payload": {"print": {"gcode_state": "FAILED"}}}]})
        self.assertEqual(answer["printers"], [])
        self.db.refresh(self.printer)
        self.assertNotEqual(self.printer.printer_state, "FAILED")

    def test_commands_are_handed_out_once_and_results_recorded(self) -> None:
        command = queue_command(self.db, self.printer, "pause")
        first = handle_sync(self.db, self.bridge, {})
        self.assertEqual([item["id"] for item in first["commands"]], [command.id])
        self.assertEqual(handle_sync(self.db, self.bridge, {})["commands"], [])
        handle_sync(self.db, self.bridge, {"results": [{"command_id": command.id, "ok": True, "message": "Pauze verstuurd."}]})
        self.db.refresh(command)
        self.assertEqual(command.status, "geslaagd")

    def test_unanswered_print_is_never_retried_but_other_commands_are(self) -> None:
        pause = queue_command(self.db, self.printer, "pause")
        start = queue_command(self.db, self.printer, "print", {"local_upload_path": "/uploads/product_print_files/a.gcode.3mf"})
        handle_sync(self.db, self.bridge, {})
        long_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
        pause.picked_at = long_ago
        start.picked_at = long_ago
        self.db.commit()
        answer = handle_sync(self.db, self.bridge, {})
        self.assertEqual([item["id"] for item in answer["commands"]], [pause.id])
        self.db.refresh(start)
        self.assertEqual(start.status, "mislukt")

    def test_pushall_is_not_queued_twice(self) -> None:
        self.assertEqual(queue_command(self.db, self.printer, "pushall").id, queue_command(self.db, self.printer, "pushall").id)

    def test_refresh_status_for_bridge_printer_queues_instead_of_mqtt(self) -> None:
        with patch("services.bambu_printers.mqtt.Client", side_effect=AssertionError("no direct MQTT")):
            result = refresh_bambu_mqtt_status(self.db, self.printer)
        self.assertIn("offline", result["bridge_note"])
        self.assertEqual(self.db.scalar(select(func.count()).select_from(BridgeCommand)), 1)

    def test_print_start_is_queued_and_file_only_served_to_own_bridge(self) -> None:
        handle_sync(self.db, self.bridge, {"reports": [{"printer_id": self.printer.id, "payload": {"print": {"gcode_state": "IDLE"}}}]})
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "uploads" / "product_print_files").mkdir(parents=True)
            (root / "uploads" / "product_print_files" / "a.gcode.3mf").write_bytes(b"3mf")
            cwd = os.getcwd()
            os.chdir(root)
            try:
                payload = BambuPrintStartRequest(local_upload_path="/uploads/product_print_files/a.gcode.3mf", confirmation_text="START PRINT")
                with patch("services.bambu_printers._upload_local_file_to_bambu_printer", side_effect=AssertionError("no direct upload")):
                    result = start_bambu_remote_print(self.db, self.printer, payload)
                self.assertTrue(result["ok"])
                answer = handle_sync(self.db, self.bridge, {})
                command = next(item for item in answer["commands"] if item["kind"] == "print")
                self.assertTrue(command["payload"]["remote_filename"].endswith(".gcode.3mf"))
                self.assertEqual(command_file(self.db, self.bridge, command["id"]).read_bytes(), b"3mf")
                other, _ = create_bridge(self.db, "Ander")
                with self.assertRaises(HTTPException):
                    command_file(self.db, other, command["id"])
            finally:
                os.chdir(cwd)

    def test_bridge_mode_requires_an_active_bridge(self) -> None:
        with self.assertRaises(HTTPException):
            _check_connection(self.db, {"connection_mode": "bridge", "bridge_id": None})
        data = {"connection_mode": "LAN", "bridge_id": self.bridge.id}
        _check_connection(self.db, data)
        self.assertEqual(data, {"connection_mode": "lan", "bridge_id": None})

    def test_sync_route_rejects_bad_token(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            asyncio.run(bridge_agent_sync(FakeRequest("pmb_nope", {}), self.db))
        self.assertEqual(caught.exception.status_code, 401)
        self.assertIn("printers", asyncio.run(bridge_agent_sync(FakeRequest(self.token, {}), self.db)))


class BridgeAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = load_agent()

    def test_deep_merge_keeps_full_state_from_deltas(self) -> None:
        state = {"print": {"gcode_state": "IDLE", "nozzle_temper": 25, "ams": {"tray": 1}}}
        self.agent.deep_merge(state, {"print": {"nozzle_temper": 210}})
        self.assertEqual(state["print"], {"gcode_state": "IDLE", "nozzle_temper": 210, "ams": {"tray": 1}})

    def test_print_refused_when_printer_busy(self) -> None:
        bridge = self.agent.Bridge("https://app.example", "pmb_x")
        link = MagicMock()
        link.gcode_state.return_value = "RUNNING"
        bridge.links = {7: link}
        bridge.download = MagicMock()
        bridge.run_command({"id": 1, "printer_id": 7, "kind": "print", "payload": {"remote_filename": "pm-a.gcode.3mf"}, "file_url": "/bridge-agent/files/1"})
        self.assertFalse(bridge.results[0]["ok"])
        self.assertIn("niet vrij", bridge.results[0]["message"])
        bridge.download.assert_not_called()
        link.publish.assert_not_called()

    def test_print_uploads_then_starts(self) -> None:
        bridge = self.agent.Bridge("https://app.example", "pmb_x")
        link = MagicMock()
        link.gcode_state.return_value = "IDLE"
        link.config = {"host": "192.168.1.50", "access_code": "12345678"}
        bridge.links = {7: link}
        bridge.download = MagicMock(side_effect=lambda url, target: target.write_bytes(b"3mf"))
        with patch.object(self.agent, "upload_to_printer") as upload:
            bridge.run_command({"id": 2, "printer_id": 7, "kind": "print", "payload": {"remote_filename": "pm-a.gcode.3mf", "plate": "Metadata/plate_1.gcode"}, "file_url": "/bridge-agent/files/2"})
        self.assertTrue(bridge.results[0]["ok"], bridge.results)
        upload.assert_called_once()
        sent = link.publish.call_args[0][0]["print"]
        self.assertEqual(sent["command"], "project_file")
        self.assertEqual(sent["url"], "file:///sdcard/cache/pm-a.gcode.3mf")

    def test_unknown_printer_reports_failure(self) -> None:
        bridge = self.agent.Bridge("https://app.example", "pmb_x")
        bridge.run_command({"id": 3, "printer_id": 99, "kind": "pause", "payload": {}})
        self.assertEqual(bridge.results, [{"command_id": 3, "ok": False, "message": "Printer is niet verbonden met de bridge."}])

    def test_agent_refuses_plain_http(self) -> None:
        with patch.dict(os.environ, {"BRIDGE_APP_URL": "http://app.example", "BRIDGE_TOKEN": "pmb_x"}, clear=False):
            os.environ.pop("BRIDGE_ALLOW_HTTP", None)
            with self.assertRaises(SystemExit):
                self.agent.main()

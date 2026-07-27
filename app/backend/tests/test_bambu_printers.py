from support import BackendTestCase

from models import BambuPrinter
from services.bambu_printers import _mqtt_reason_code_success, preflight_bambu_print_start


class BambuPrinterPreflightTests(BackendTestCase):
    def make_printer(self, state: str | None) -> BambuPrinter:
        printer = BambuPrinter(
            name="P2S test",
            model="P2S",
            serial_number="123456789012345",
            host="10.0.0.10",
            mqtt_port=8883,
            access_code_encrypted="stored",
            active=True,
            printer_state=state,
        )
        self.db.add(printer)
        self.db.commit()
        self.db.refresh(printer)
        return printer

    def test_preflight_blocks_unknown_printer_state(self):
        result = preflight_bambu_print_start(
            self.db,
            self.make_printer(None),
            "file:///sdcard/test.gcode.3mf",
            refresh_status=False,
        )

        self.assertFalse(result["ok"])
        self.assertTrue(any(check["name"] == "Printerstatus" and not check["ok"] for check in result["checks"]))

    def test_preflight_blocks_busy_printer_state(self):
        result = preflight_bambu_print_start(
            self.db,
            self.make_printer("RUNNING"),
            "file:///sdcard/test.gcode.3mf",
            refresh_status=False,
        )

        self.assertFalse(result["ok"])
        self.assertTrue(any(check["name"] == "Printer niet bezig" and not check["ok"] for check in result["checks"]))

    def test_preflight_allows_idle_printer_state(self):
        result = preflight_bambu_print_start(
            self.db,
            self.make_printer("IDLE"),
            "file:///sdcard/test.gcode.3mf",
            refresh_status=False,
        )

        self.assertTrue(result["ok"])

    def test_mqtt_reason_code_accepts_paho_v2_success_object(self):
        class ReasonCode:
            is_failure = False

            def __str__(self):
                return "Success"

        self.assertTrue(_mqtt_reason_code_success(ReasonCode()))
        self.assertTrue(_mqtt_reason_code_success(0))
        self.assertFalse(_mqtt_reason_code_success(5))

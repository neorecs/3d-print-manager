from support import BackendTestCase

from models import BambuPrinter
from pathlib import Path

from services.bambu_printers import _bambu_remote_print_filename, _mqtt_reason_code_success, preflight_bambu_print_start


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
            "/uploads/product_print_files/1/test.gcode.3mf",
            refresh_status=False,
        )

        self.assertFalse(result["ok"])
        self.assertTrue(any(check["name"] == "Printerstatus" and not check["ok"] for check in result["checks"]))

    def test_preflight_blocks_busy_printer_state(self):
        result = preflight_bambu_print_start(
            self.db,
            self.make_printer("RUNNING"),
            "/uploads/product_print_files/1/test.gcode.3mf",
            refresh_status=False,
        )

        self.assertFalse(result["ok"])
        self.assertTrue(any(check["name"] == "Printer niet bezig" and not check["ok"] for check in result["checks"]))

    def test_preflight_allows_idle_printer_state(self):
        result = preflight_bambu_print_start(
            self.db,
            self.make_printer("IDLE"),
            "/uploads/product_print_files/1/test.gcode.3mf",
            refresh_status=False,
        )

        self.assertTrue(result["ok"])

    def test_preflight_blocks_start_without_remote_upload_source(self):
        result = preflight_bambu_print_start(
            self.db,
            self.make_printer("IDLE"),
            "",
            refresh_status=False,
        )

        self.assertFalse(result["ok"])
        self.assertTrue(any(check["name"] == "Gekoppeld printbestand" and not check["ok"] for check in result["checks"]))

    def test_mqtt_reason_code_accepts_paho_v2_success_object(self):
        class ReasonCode:
            is_failure = False

            def __str__(self):
                return "Success"

        self.assertTrue(_mqtt_reason_code_success(ReasonCode()))
        self.assertTrue(_mqtt_reason_code_success(0))
        self.assertFalse(_mqtt_reason_code_success(5))

    def test_remote_print_filename_is_short_and_bambu_safe(self):
        filename = _bambu_remote_print_filename(Path("1cdd9ac93ce14bd69b49ea6f4b953cf1-world_s_tinest_3d_print_gcode.3mf"))

        self.assertLessEqual(len(filename), 25)
        self.assertTrue(filename.startswith("pm-"))
        self.assertTrue(filename.endswith(".gcode.3mf"))

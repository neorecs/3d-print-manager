import json
import tempfile
import zipfile
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException

from support import *
from models import BambuPrinter, PrintBatch, PrintBatchItem
from services import bambu_studio_service


class BambuStudioWorkflowTests(BackendTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.original_upload_root = bambu_studio_service.UPLOAD_ROOT
        self.original_export_root = bambu_studio_service.EXPORT_ROOT
        self.original_prepared_root = bambu_studio_service.PREPARED_ROOT
        bambu_studio_service.UPLOAD_ROOT = self.root / "uploads"
        bambu_studio_service.EXPORT_ROOT = self.root / "exports"
        bambu_studio_service.PREPARED_ROOT = self.root / "prepared"

    def tearDown(self) -> None:
        bambu_studio_service.UPLOAD_ROOT = self.original_upload_root
        bambu_studio_service.EXPORT_ROOT = self.original_export_root
        bambu_studio_service.PREPARED_ROOT = self.original_prepared_root
        self.temporary_directory.cleanup()
        super().tearDown()

    def make_print_file(self, product: Product, content: bytes = b"test-gcode-3mf") -> Path:
        directory = bambu_studio_service.UPLOAD_ROOT / "product_print_files" / str(product.id)
        directory.mkdir(parents=True, exist_ok=True)
        source = directory / "0123456789abcdef0123456789abcdef-test-product.gcode.3mf"
        source.write_bytes(content)
        product.print_file_path = f"/uploads/product_print_files/{product.id}/{source.name}"
        self.db.commit()
        return source

    def make_valid_print_file(self, product: Product) -> Path:
        source = self.make_print_file(product)
        project = {
            "printer_model": "Bambu Lab P2S",
            "printer_settings_id": "Bambu Lab P2S 0.4 nozzle",
            "filament_colour": ["#00AE42"],
        }
        slice_info = b'''<?xml version="1.0" encoding="UTF-8"?>
<config><plate><metadata key="printer_model_id" value="N7"/>
<filament id="1" type="PLA" color="#00AE42"/></plate></config>'''
        with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", "<Types />")
            archive.writestr("Metadata/project_settings.config", json.dumps(project))
            archive.writestr("Metadata/slice_info.config", slice_info)
            archive.writestr("Metadata/plate_1.json", json.dumps({"filament_colors": ["#00AE42"]}))
            archive.writestr("Metadata/plate_1.gcode", "; test")
        return source

    def test_product_download_uses_readable_filename(self) -> None:
        product, _variant = self.make_product_variant("STUDIO-DOWNLOAD")
        source = self.make_print_file(product)

        response = bambu_studio_service.product_print_file_response(product)

        self.assertEqual(Path(response.path), source)
        self.assertIn("test-product.gcode.3mf", response.headers["content-disposition"])
        self.assertEqual(response.headers["cache-control"], "private, no-store")

    def test_batch_export_contains_lists_guide_and_unique_print_file(self) -> None:
        product, variant = self.make_product_variant("STUDIO-BATCH")
        source = self.make_print_file(product, b"print-ready")
        job = PrintJob(
            product_id=product.id,
            product_variant_id=variant.id,
            color="rood",
            material="PLA",
            quantity_needed=2,
            quantity_planned=3,
            quantity_to_order=2,
            quantity_to_inventory=1,
            status="gepland",
        )
        batch = PrintBatch(batch_name="Rode PLA batch", material="PLA", color="rood", status="gepland")
        self.db.add_all([job, batch])
        self.db.commit()
        self.db.add(PrintBatchItem(print_batch_id=batch.id, print_job_id=job.id, quantity_in_batch=3))
        self.db.commit()

        result = bambu_studio_service.export_print_batch_for_bambu_studio(self.db, batch)

        archive = Path(result["files"]["bambu_studio_zip"])
        self.assertTrue(archive.is_file())
        self.assertEqual(result["print_file_count"], 1)
        self.assertEqual(result["missing_print_files"], [])
        with zipfile.ZipFile(archive) as bundle:
            names = set(bundle.namelist())
            self.assertIn("productielijst.csv", names)
            self.assertIn("orderoverzicht.csv", names)
            self.assertIn("LEESMIJ-BAMBU-STUDIO.md", names)
            print_names = [name for name in names if name.startswith("printbestanden/")]
            self.assertEqual(len(print_names), 1)
            self.assertEqual(bundle.read(print_names[0]), source.read_bytes())
            self.assertIn("Print plate", bundle.read("LEESMIJ-BAMBU-STUDIO.md").decode("utf-8"))

    def test_missing_print_file_is_reported_without_breaking_manifest_export(self) -> None:
        product, variant = self.make_product_variant("STUDIO-MISSING")
        product.print_file_path = "/uploads/product_print_files/999/missing.gcode.3mf"
        job = PrintJob(
            product_id=product.id,
            product_variant_id=variant.id,
            quantity_needed=1,
            quantity_planned=1,
            status="gepland",
        )
        batch = PrintBatch(batch_name="Onvolledige batch", status="gepland")
        self.db.add_all([job, batch])
        self.db.commit()
        self.db.add(PrintBatchItem(print_batch_id=batch.id, print_job_id=job.id, quantity_in_batch=1))
        self.db.commit()

        result = bambu_studio_service.export_print_batch_for_bambu_studio(self.db, batch)

        self.assertEqual(result["print_file_count"], 0)
        self.assertEqual(result["missing_print_files"], [product.name])
        self.assertTrue(Path(result["files"]["bambu_studio_zip"]).is_file())

    def test_download_rejects_paths_outside_product_print_storage(self) -> None:
        product, _variant = self.make_product_variant("STUDIO-PATH")
        product.print_file_path = "/uploads/accounting_documents/secret.pdf"

        with self.assertRaises(HTTPException) as raised:
            bambu_studio_service.product_print_file_response(product)

        self.assertEqual(raised.exception.status_code, 404)

    def test_preparation_matches_variant_to_printer_ams_and_rewrites_color(self) -> None:
        product, variant = self.make_product_variant("STUDIO-AMS")
        self.make_valid_print_file(product)
        printer = BambuPrinter(
            name="P2S Productie",
            model="P2S",
            host="10.0.0.20",
            ams_slots_json=json.dumps(
                [
                    {"ams_id": 0, "tray_id": 0, "slot_number": 1, "label": "AMS 1 - sleuf 1", "material": "PLA", "color_hex": "#991C1C"},
                    {"ams_id": 0, "tray_id": 1, "slot_number": 2, "label": "AMS 1 - sleuf 2", "material": "PETG", "color_hex": "#FF0000"},
                ]
            ),
        )
        self.db.add(printer)
        self.db.commit()
        self.db.refresh(printer)

        preparation = bambu_studio_service.product_print_preparation(self.db, product, variant, printer)
        self.assertEqual(preparation["recommended_slot"]["tray_id"], 0)

        response = bambu_studio_service.prepared_product_print_file_response(
            self.db, product, variant, printer, 0, 0, BackgroundTasks()
        )
        with zipfile.ZipFile(Path(response.path)) as archive:
            project = json.loads(archive.read("Metadata/project_settings.config"))
            self.assertEqual(project["filament_colour"][0], "#991C1C")
            slice_info = archive.read("Metadata/slice_info.config").decode("utf-8")
            self.assertIn('color="#991C1C"', slice_info)

    def test_preparation_rejects_material_that_differs_from_sliced_file(self) -> None:
        product, variant = self.make_product_variant("STUDIO-WRONG-MATERIAL")
        self.make_valid_print_file(product)
        variant.material = "PETG"
        printer = BambuPrinter(name="P2S", model="P2S", host="10.0.0.20", ams_slots_json="[]")
        self.db.add(printer)
        self.db.commit()

        with self.assertRaises(HTTPException) as raised:
            bambu_studio_service.product_print_preparation(self.db, product, variant, printer)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("geslicet voor PLA", raised.exception.detail)

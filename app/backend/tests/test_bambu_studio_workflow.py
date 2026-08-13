import tempfile
import zipfile
from pathlib import Path

from fastapi import HTTPException

from support import *
from models import PrintBatch, PrintBatchItem
from services import bambu_studio_service


class BambuStudioWorkflowTests(BackendTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.original_upload_root = bambu_studio_service.UPLOAD_ROOT
        self.original_export_root = bambu_studio_service.EXPORT_ROOT
        bambu_studio_service.UPLOAD_ROOT = self.root / "uploads"
        bambu_studio_service.EXPORT_ROOT = self.root / "exports"

    def tearDown(self) -> None:
        bambu_studio_service.UPLOAD_ROOT = self.original_upload_root
        bambu_studio_service.EXPORT_ROOT = self.original_export_root
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

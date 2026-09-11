import io
import tempfile
from pathlib import Path
from unittest.mock import patch

from support import *
from fastapi import UploadFile
from services.product_creation import save_product_with_variant
from services.upload_service import upload_product_print_file
from schemas.common import ProductWithVariantCreate, ProductVariantCreate
from services.order_guards import require_reprocessable_order
from core.internal_auth import _is_signed_file_bridge


class ReliabilityTests(BackendTestCase):
    def test_failed_variant_rolls_back_product_and_retry_succeeds(self):
        self.make_product_variant("TAKEN")
        payload = ProductWithVariantCreate(name="New", first_variant=ProductVariantCreate(
            product_id=0, variant_name="Red", sku="TAKEN"))
        with self.assertRaises(HTTPException) as caught:
            save_product_with_variant(self.db, payload)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(len(self.db.scalars(select(Product)).all()), 1)
        payload.first_variant.sku = "AVAILABLE"
        result = save_product_with_variant(self.db, payload)
        self.assertEqual(len(self.db.scalars(select(Product)).all()), 2)
        variant = self.db.scalar(select(ProductVariant).where(ProductVariant.sku == "AVAILABLE"))
        self.assertEqual(variant.product_id, result["id"])

    def test_file_commit_failure_preserves_previous_reference(self):
        product, _ = self.make_product_variant()
        previous = product.print_file_path
        with tempfile.TemporaryDirectory() as directory:
            with patch("services.upload_service.PRODUCT_PRINT_FILE_ROOT", Path(directory)), \
                    patch("services.upload_service.delete_uploaded_product_print_file") as delete, \
                    patch.object(self.db, "commit", side_effect=RuntimeError("database unavailable")):
                with self.assertRaises(RuntimeError):
                    upload_product_print_file(self.db, product.id, UploadFile(filename="model.stl", file=io.BytesIO(b"solid test")))
                delete.assert_not_called()
            self.assertEqual(product.print_file_path, previous)
            self.assertFalse(any(Path(directory).rglob("*.stl")))

    def make_order(self, status="nieuw"):
        platform = self.make_platform()
        product, variant = self.make_product_variant()
        order = Order(internal_order_number="SAFE-1", external_order_id="SAFE-1", platform_id=platform.id, status=status)
        self.db.add(order)
        self.db.flush()
        line = OrderItem(order_id=order.id, product_id=product.id, product_variant_id=variant.id,
                         sku=variant.sku, quantity_ordered=4, quantity_to_print=4)
        self.db.add(line)
        self.db.commit()
        return order, line

    def test_closed_order_cannot_be_reprocessed(self):
        order, _ = self.make_order("verzonden")
        with self.assertRaises(HTTPException) as caught:
            process_order_inventory(order.id, self.db)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(order.status, "verzonden")
        self.assertEqual(self.db.scalars(select(InventoryMovement)).all(), [])

    def test_started_print_prevents_order_recalculation(self):
        order, line = self.make_order("ingepland")
        self.db.add(PrintJob(order_item_id=line.id, product_id=line.product_id,
                            product_variant_id=line.product_variant_id, status="bezig"))
        self.db.commit()
        with self.assertRaises(HTTPException):
            require_reprocessable_order(self.db, order.id)
        self.assertEqual(order.status, "ingepland")

    def test_correction_cannot_remove_reserved_stock(self):
        product, variant = self.make_product_variant()
        job = PrintJob(product_id=product.id, product_variant_id=variant.id, quantity_needed=0,
                       quantity_planned=5, status="nieuw")
        self.db.add(job)
        self.db.commit()
        complete_print_job(job.id, PrintJobComplete(quantity_succeeded=5, quantity_to_order=0), self.db)
        inventory = self.db.scalar(select(ProductInventory))
        inventory.quantity_reserved = 4
        self.db.commit()
        before_count = len(self.db.scalars(select(InventoryMovement)).all())
        with self.assertRaises(HTTPException) as caught:
            complete_print_job(job.id, PrintJobComplete(quantity_succeeded=2, quantity_to_order=0), self.db)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(inventory.quantity_on_hand, 5)
        self.assertEqual(job.quantity_succeeded, 5)
        self.assertEqual(len(self.db.scalars(select(InventoryMovement)).all()), before_count)

    def test_valid_correction_movement_matches_stock_delta(self):
        product, variant = self.make_product_variant()
        job = PrintJob(product_id=product.id, product_variant_id=variant.id, quantity_needed=0,
                       quantity_planned=5, status="nieuw")
        self.db.add(job)
        self.db.commit()
        complete_print_job(job.id, PrintJobComplete(quantity_succeeded=5, quantity_to_order=0), self.db)
        complete_print_job(job.id, PrintJobComplete(quantity_succeeded=2, quantity_to_order=0), self.db)
        self.assertEqual(self.db.scalar(select(ProductInventory)).quantity_on_hand, 2)
        movements = self.db.scalars(select(InventoryMovement).order_by(InventoryMovement.id)).all()
        self.assertEqual(movements[-1].quantity, -3)

    def test_partial_print_does_not_complete_order(self):
        order, line = self.make_order("ingepland")
        job = PrintJob(order_item_id=line.id, product_id=line.product_id, product_variant_id=line.product_variant_id,
                       quantity_needed=4, quantity_planned=4, status="gepland")
        self.db.add(job)
        self.db.flush()
        line.print_job_id = job.id
        self.db.commit()
        complete_print_job(job.id, PrintJobComplete(quantity_succeeded=1, quantity_failed=3), self.db)
        self.assertNotEqual(order.status, "geprint")

    def test_normal_download_is_not_a_session_exempt_bridge(self):
        self.assertFalse(_is_signed_file_bridge("/products/1/print-file/download"))
        self.assertTrue(_is_signed_file_bridge("/products/1/print-file/source-download"))
        self.assertFalse(_is_signed_file_bridge("/products/invalid/print-file/source-download"))

    def test_reduced_print_result_reopens_order_shortage(self):
        order, line = self.make_order("ingepland")
        job = PrintJob(order_item_id=line.id, product_id=line.product_id, product_variant_id=line.product_variant_id,
                       quantity_needed=4, quantity_planned=4, status="gepland")
        self.db.add(job)
        self.db.commit()
        complete_print_job(job.id, PrintJobComplete(quantity_succeeded=4), self.db)
        self.assertEqual(order.status, "geprint")
        complete_print_job(job.id, PrintJobComplete(quantity_succeeded=1, quantity_failed=3), self.db)
        self.assertEqual(order.status, "deels_te_printen")

    def test_bridge_requires_internal_auth_and_normal_download_requires_session(self):
        import asyncio
        from types import SimpleNamespace
        from starlette.requests import Request
        from starlette.responses import Response
        from core.internal_auth import enforce_backend_access

        async def run(path, token=None, method="GET"):
            headers = [(b"x-backend-internal-token", token.encode())] if token else []
            request = Request({"type": "http", "path": path, "method": method, "headers": headers})
            async def downstream(request):
                return Response(status_code=204)
            return await enforce_backend_access(request, downstream)

        settings = SimpleNamespace(backend_internal_token="test-only", auth_secret="test-secret")
        with patch("core.internal_auth.get_settings", return_value=settings):
            self.assertEqual(asyncio.run(run("/products/1/print-file/source-download")).status_code, 401)
            self.assertEqual(asyncio.run(run("/products/1/print-file/source-download", "test-only")).status_code, 204)
            self.assertEqual(asyncio.run(run("/products/1/print-file/download", "test-only")).status_code, 401)
            self.assertEqual(asyncio.run(run("/products/1/print-file/source-download", "test-only", "POST")).status_code, 401)

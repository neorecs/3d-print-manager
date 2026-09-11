from unittest.mock import patch

from support import *
from models import AccountingSale, PrintBatch, PrintBatchItem
from services.order_processing import process_order
from inventory.service import process_order_inventory as reserve_order


class OrderProcessingTests(BackendTestCase):
    def make_order(self):
        platform = self.make_platform()
        product, variant = self.make_product_variant()
        order = Order(internal_order_number="ATOMIC-1", external_order_id="ATOMIC-1", platform_id=platform.id, total_amount=100, status="nieuw")
        inventory = ProductInventory(product_id=product.id, product_variant_id=variant.id,
                                     quantity_on_hand=6, quantity_reserved=0)
        self.db.add_all([order, inventory])
        self.db.flush()
        line = OrderItem(order_id=order.id, sku=variant.sku, quantity_ordered=10)
        self.db.add(line)
        self.db.commit()
        return order, line, inventory

    def test_repeat_has_one_job_one_sale_and_no_extra_movements(self):
        order, line, stock = self.make_order()
        for _ in range(3):
            result = process_order(self.db, order.id)
            self.assertEqual(result["order"]["status"], "ingepland")
        self.assertEqual(stock.quantity_reserved, 6)
        self.assertEqual(line.quantity_to_print, 4)
        self.assertEqual(len(self.db.scalars(select(PrintJob)).all()), 1)
        self.assertEqual(len(self.db.scalars(select(AccountingSale)).all()), 1)
        self.assertEqual(len(self.db.scalars(select(InventoryMovement)).all()), 1)

    def test_resume_legacy_reservation(self):
        order, line, stock = self.make_order()
        reserve_order(self.db, order)
        process_order(self.db, order.id)
        self.assertEqual(stock.quantity_reserved, 6)
        self.assertEqual(len(self.db.scalars(select(InventoryMovement)).all()), 1)
        self.assertIsNotNone(line.print_job_id)

    def test_accounting_failure_rolls_back_everything_and_retry_works(self):
        order, line, stock = self.make_order()
        with patch("services.order_processing.create_accounting_sale_from_order", side_effect=RuntimeError("failure")):
            with self.assertRaises(RuntimeError):
                process_order(self.db, order.id)
        self.assertEqual(stock.quantity_reserved, 0)
        self.assertEqual(order.status, "nieuw")
        self.assertIsNone(line.product_variant_id)
        self.assertEqual(self.db.scalars(select(PrintJob)).all(), [])
        self.assertEqual(self.db.scalars(select(InventoryMovement)).all(), [])
        process_order(self.db, order.id)
        self.assertEqual(stock.quantity_reserved, 6)

    def test_commit_failure_rolls_back_all_tables(self):
        order, line, stock = self.make_order()
        with patch.object(self.db, "commit", side_effect=RuntimeError("failure")):
            with self.assertRaises(RuntimeError):
                process_order(self.db, order.id)
        self.assertEqual(stock.quantity_reserved, 0)
        self.assertEqual(self.db.scalars(select(AccountingSale)).all(), [])
        self.assertEqual(self.db.scalars(select(PrintJob)).all(), [])

    def test_unknown_sku_prevents_partial_order_processing(self):
        order, line, stock = self.make_order()
        self.db.add(OrderItem(order_id=order.id, sku="UNKNOWN", quantity_ordered=1))
        self.db.commit()
        with self.assertRaises(HTTPException) as caught:
            process_order(self.db, order.id)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(stock.quantity_reserved, 0)
        self.assertEqual(self.db.scalars(select(AccountingSale)).all(), [])

    def test_restock_removes_obsolete_unstarted_job(self):
        order, line, stock = self.make_order()
        process_order(self.db, order.id)
        stock.quantity_on_hand = 10
        self.db.commit()
        process_order(self.db, order.id)
        self.assertEqual(line.quantity_to_print, 0)
        self.assertIsNone(line.print_job_id)
        self.assertEqual(self.db.scalars(select(PrintJob)).all(), [])
        self.assertEqual(order.status, "volledig_uit_voorraad")

    def test_restock_preserves_explicit_extra_stock_production(self):
        order, line, stock = self.make_order()
        process_order(self.db, order.id)
        job = self.db.get(PrintJob, line.print_job_id)
        job.quantity_planned = 7
        stock.quantity_on_hand = 10
        self.db.commit()
        process_order(self.db, order.id)
        self.assertIsNone(job.order_item_id)
        self.assertIsNone(line.print_job_id)
        self.assertEqual(job.quantity_planned, 3)
        self.assertEqual(job.quantity_to_inventory, 3)
        process_order(self.db, order.id)
        self.assertEqual(len(self.db.scalars(select(PrintJob)).all()), 1)

    def test_changed_shortage_of_batched_job_rolls_back(self):
        order, line, stock = self.make_order()
        process_order(self.db, order.id)
        batch = PrintBatch(batch_name="Protected")
        self.db.add(batch)
        self.db.flush()
        self.db.add(PrintBatchItem(print_batch_id=batch.id, print_job_id=line.print_job_id, quantity_in_batch=4))
        stock.quantity_on_hand = 10
        self.db.commit()
        with self.assertRaises(HTTPException):
            process_order(self.db, order.id)
        self.assertEqual(stock.quantity_reserved, 6)
        self.assertEqual(line.quantity_to_print, 4)

    def test_started_job_and_closed_order_are_unchanged(self):
        order, line, stock = self.make_order()
        process_order(self.db, order.id)
        job = self.db.get(PrintJob, line.print_job_id)
        job.status = "bezig"
        self.db.commit()
        with self.assertRaises(HTTPException):
            process_order(self.db, order.id)
        self.assertEqual(stock.quantity_reserved, 6)
        job.status = "nieuw"
        order.status = "verzonden"
        self.db.commit()
        with self.assertRaises(HTTPException):
            process_order(self.db, order.id)
        self.assertEqual(order.status, "verzonden")

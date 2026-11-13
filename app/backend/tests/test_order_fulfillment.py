from support import *

from api.routes.orders import update_order
from domain.statuses import ORDER_CANCELLED, ORDER_PACKED, ORDER_SHIPPED, PRINT_JOB_CANCELLED, PRINT_JOB_PRINTED
from schemas.common import OrderCreate
from services.order_fulfillment import cancel_order, pack_order, ship_order
from services.order_import_service import upsert_imported_order
from services.order_processing import process_order


class OrderFulfillmentTests(BackendTestCase):
    def make_order(self, ordered: int, on_hand: int):
        platform = self.make_platform()
        product, variant = self.make_product_variant()
        order = Order(internal_order_number="SHIP-1", external_order_id="SHIP-1", platform_id=platform.id, total_amount=50, status="nieuw")
        inventory = ProductInventory(product_id=product.id, product_variant_id=variant.id, quantity_on_hand=on_hand, quantity_reserved=0)
        self.db.add_all([order, inventory])
        self.db.flush()
        line = OrderItem(order_id=order.id, sku=variant.sku, quantity_ordered=ordered)
        self.db.add(line)
        self.db.commit()
        return platform, order, line, inventory

    def movements(self, order):
        return [
            (movement.movement_type, movement.quantity)
            for movement in self.db.scalars(select(InventoryMovement).where(InventoryMovement.order_id == order.id).order_by(InventoryMovement.id)).all()
        ]

    def test_shipping_books_reserved_stock_out(self) -> None:
        _, order, _, inventory = self.make_order(ordered=2, on_hand=6)
        process_order(self.db, order.id)
        self.assertEqual(inventory.quantity_reserved, 2)

        pack_order(self.db, order.id)
        self.assertEqual(order.status, ORDER_PACKED)
        result = ship_order(self.db, order.id, performed_by="admin@example.com")

        self.assertEqual(result["status"], "shipped")
        self.assertEqual(order.status, ORDER_SHIPPED)
        self.assertEqual(inventory.quantity_on_hand, 4)
        self.assertEqual(inventory.quantity_reserved, 0)
        self.assertEqual(self.movements(order), [("gereserveerd_voor_order", 2), ("verzonden", -2)])
        shipped = self.db.scalar(select(InventoryMovement).where(InventoryMovement.movement_type == "verzonden"))
        self.assertEqual(shipped.performed_by, "admin@example.com")

    def test_shipping_twice_books_stock_out_once(self) -> None:
        _, order, _, inventory = self.make_order(ordered=2, on_hand=6)
        process_order(self.db, order.id)
        ship_order(self.db, order.id)
        second = ship_order(self.db, order.id)

        self.assertEqual(second["status"], "already_shipped")
        self.assertEqual(inventory.quantity_on_hand, 4)
        self.assertEqual(self.movements(order).count(("verzonden", -2)), 1)

    def test_shipping_is_blocked_until_print_work_is_done(self) -> None:
        _, order, line, inventory = self.make_order(ordered=10, on_hand=6)
        process_order(self.db, order.id)

        with self.assertRaises(HTTPException) as blocked:
            ship_order(self.db, order.id)
        self.assertEqual(blocked.exception.status_code, 409)
        self.assertNotEqual(order.status, ORDER_SHIPPED)
        self.assertEqual(inventory.quantity_on_hand, 6)
        self.assertEqual(inventory.quantity_reserved, 6)

        job = self.db.get(PrintJob, line.print_job_id)
        job.status = PRINT_JOB_PRINTED
        job.quantity_succeeded = 4
        job.quantity_to_order = 4
        self.db.commit()

        ship_order(self.db, order.id)
        self.assertEqual(order.status, ORDER_SHIPPED)
        self.assertEqual(inventory.quantity_on_hand, 0)
        self.assertEqual(inventory.quantity_reserved, 0)

    def test_unprocessed_order_cannot_be_shipped_manually(self) -> None:
        _, order, _, _ = self.make_order(ordered=1, on_hand=6)
        with self.assertRaises(HTTPException) as blocked:
            ship_order(self.db, order.id)
        self.assertEqual(blocked.exception.status_code, 409)

    def test_manual_cancel_releases_reservation_and_open_print_work(self) -> None:
        _, order, line, inventory = self.make_order(ordered=10, on_hand=6)
        process_order(self.db, order.id)
        job_id = line.print_job_id

        result = cancel_order(self.db, order.id, performed_by="admin@example.com")

        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(order.status, ORDER_CANCELLED)
        self.assertEqual(inventory.quantity_on_hand, 6)
        self.assertEqual(inventory.quantity_reserved, 0)
        self.assertEqual(self.db.get(PrintJob, job_id).status, PRINT_JOB_CANCELLED)
        self.assertIn(("reservering_vrijgegeven", 6), self.movements(order))

    def test_shipped_order_cannot_be_cancelled(self) -> None:
        _, order, _, _ = self.make_order(ordered=1, on_hand=6)
        process_order(self.db, order.id)
        ship_order(self.db, order.id)
        with self.assertRaises(HTTPException) as blocked:
            cancel_order(self.db, order.id)
        self.assertEqual(blocked.exception.status_code, 409)

    def test_platform_shipped_status_books_stock_out_with_warning(self) -> None:
        platform, _, _, _ = self.make_order(ordered=1, on_hand=0)
        product, variant = self.make_product_variant("IMPORT-SKU")
        inventory = ProductInventory(product_id=product.id, product_variant_id=variant.id, quantity_on_hand=5, quantity_reserved=0)
        self.db.add(inventory)
        self.db.commit()
        payload = {
            "external_order_id": "receipt-9", "order_number": "receipt-9", "external_status": "paid", "payment_status": "betaald",
            "items": [{"external_order_item_id": "tx-9", "sku": variant.sku, "quantity_ordered": 2, "unit_sale_price": 10}],
        }
        imported = upsert_imported_order(self.db, platform, payload)
        self.db.flush()
        process_order(self.db, imported["order"]["id"])

        shipped = upsert_imported_order(self.db, platform, {**payload, "external_status": "completed"})
        self.db.commit()

        order = self.db.get(Order, imported["order"]["id"])
        self.assertEqual(order.status, ORDER_SHIPPED)
        self.assertEqual(inventory.quantity_on_hand, 3)
        self.assertEqual(inventory.quantity_reserved, 0)
        self.assertEqual(shipped["warnings"], [])

        repeated = upsert_imported_order(self.db, platform, {**payload, "external_status": "completed"})
        self.db.commit()
        self.assertEqual(inventory.quantity_on_hand, 3)
        self.assertEqual(repeated["warnings"], [])

    def test_order_edit_cannot_change_status(self) -> None:
        platform, order, _, _ = self.make_order(ordered=1, on_hand=6)
        payload = OrderCreate(
            internal_order_number=order.internal_order_number,
            platform_id=platform.id,
            external_order_id=order.external_order_id,
            customer_name="Nieuwe naam",
            status=ORDER_SHIPPED,
        )
        updated = update_order(order.id, payload, self.db)

        self.assertEqual(updated["customer_name"], "Nieuwe naam")
        self.assertEqual(updated["status"], "nieuw")

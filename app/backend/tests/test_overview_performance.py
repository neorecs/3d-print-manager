import time
from datetime import datetime, timezone

from sqlalchemy import event

from models import Order, OrderItem, Platform, PrintJob, Product, ProductInventory, ProductPlatformPublication, ProductVariant
from services.overview_service import catalog_overview, dashboard_overview, orders_overview
from tests.support import BackendTestCase


class OverviewPerformanceTests(BackendTestCase):
    PRODUCT_COUNT = 1000
    ORDER_COUNT = 1200

    def setUp(self) -> None:
        super().setUp()
        self._seed_realistic_volume()

    def _seed_realistic_volume(self) -> None:
        self.db.add(Platform(id=1, name="Testkanaal", type="shopify", active=True))
        self.db.bulk_save_objects([
            Product(id=index, name=f"Product {index}", internal_title=f"Product {index}", status="concept", active=index % 10 != 0)
            for index in range(1, self.PRODUCT_COUNT + 1)
        ])
        self.db.bulk_save_objects([
            ProductVariant(id=index, product_id=index, variant_name="Standaard", sku=f"SKU-{index}", color="Rood", material="PLA", default_sale_price=15, cost_price=3, active=True)
            for index in range(1, self.PRODUCT_COUNT + 1)
        ])
        self.db.bulk_save_objects([
            ProductInventory(id=index, product_id=index, product_variant_id=index, quantity_on_hand=5, quantity_reserved=1, minimum_stock_level=4)
            for index in range(1, self.PRODUCT_COUNT + 1)
        ])
        self.db.bulk_save_objects([
            ProductPlatformPublication(id=index, product_id=index, platform_id=1, publication_status="gepubliceerd")
            for index in range(1, self.PRODUCT_COUNT + 1)
        ])
        now = datetime.now(timezone.utc)
        self.db.bulk_save_objects([
            Order(id=index, internal_order_number=f"ORDER-{index}", platform_id=1, external_order_id=f"EXT-{index}", order_date=now, total_amount=20, status="nieuw", payment_status="betaald")
            for index in range(1, self.ORDER_COUNT + 1)
        ])
        self.db.bulk_save_objects([
            OrderItem(id=index, order_id=index, product_id=((index - 1) % self.PRODUCT_COUNT) + 1, product_variant_id=((index - 1) % self.PRODUCT_COUNT) + 1, sku=f"SKU-{((index - 1) % self.PRODUCT_COUNT) + 1}", quantity_ordered=1, quantity_from_inventory=0, quantity_to_print=1, inventory_status="niet_op_voorraad")
            for index in range(1, self.ORDER_COUNT + 1)
        ])
        self.db.bulk_save_objects([
            PrintJob(id=index, order_item_id=index, product_id=((index - 1) % self.PRODUCT_COUNT) + 1, product_variant_id=((index - 1) % self.PRODUCT_COUNT) + 1, quantity_needed=1, quantity_planned=1, status="nieuw")
            for index in range(1, self.ORDER_COUNT + 1)
        ])
        self.db.commit()

    def _measure(self, callback):
        statements = 0

        def count_statement(*_args):
            nonlocal statements
            statements += 1

        event.listen(self.engine, "before_cursor_execute", count_statement)
        started = time.perf_counter()
        try:
            result = callback()
        finally:
            elapsed = time.perf_counter() - started
            event.remove(self.engine, "before_cursor_execute", count_statement)
        return result, statements, elapsed

    def test_catalog_page_is_bounded_under_realistic_volume(self) -> None:
        result, statements, elapsed = self._measure(lambda: catalog_overview(self.db, 3, 20, "actief"))
        self.assertEqual(len(result["rows"]), 20)
        self.assertEqual(result["total"], 900)
        self.assertEqual(result["page"], 3)
        self.assertLessEqual(statements, 9)
        self.assertLess(elapsed, 2.0)

    def test_order_page_is_bounded_under_realistic_volume(self) -> None:
        result, statements, elapsed = self._measure(lambda: orders_overview(self.db, 4, 25, "nieuw"))
        self.assertEqual(len(result["orders"]), 25)
        self.assertEqual(len(result["order_items"]), 25)
        self.assertEqual(result["total"], self.ORDER_COUNT)
        self.assertLessEqual(statements, 7)
        self.assertLess(elapsed, 2.0)

    def test_dashboard_payload_remains_bounded(self) -> None:
        result, statements, elapsed = self._measure(lambda: dashboard_overview(self.db))
        self.assertLessEqual(len(result["top_products"]), 5)
        self.assertLessEqual(len(result["low_inventory"]), 5)
        self.assertLessEqual(len(result["open_print_jobs"]), 5)
        self.assertEqual(result["metrics"]["orders_total"], self.ORDER_COUNT)
        self.assertLessEqual(statements, 10)
        self.assertLess(elapsed, 2.0)

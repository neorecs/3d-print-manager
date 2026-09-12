from support import *

from domain.statuses import ACCOUNTING_CANCELLED, ORDER_CANCELLED, PRINT_JOB_CANCELLED
from models import AccountingSale
from services.order_import_service import upsert_imported_order


class OrderImportTestCase(BackendTestCase):
    def test_cancelled_reimport_releases_once_and_cancels_open_work(self) -> None:
        platform = self.make_platform("etsy")
        product, variant = self.make_product_variant("CANCEL-SKU")
        inventory = ProductInventory(product_id=product.id, product_variant_id=variant.id, quantity_on_hand=5, quantity_reserved=2)
        order = Order(internal_order_number="ETSY-1-100", platform_id=platform.id, external_order_id="100", status="ingepland", payment_status="betaald")
        self.db.add_all([inventory, order])
        self.db.flush()
        item = OrderItem(order_id=order.id, product_id=product.id, product_variant_id=variant.id, external_order_item_id="line-1", sku=variant.sku, quantity_ordered=2, quantity_from_inventory=2, inventory_status="volledig_op_voorraad")
        self.db.add(item)
        self.db.flush()
        job = PrintJob(order_item_id=item.id, product_id=product.id, product_variant_id=variant.id, quantity_needed=1, quantity_planned=1, status="nieuw")
        sale = AccountingSale(order_id=order.id, platform_id=platform.id, invoice_number="ETSY-1-100", net_amount=10, vat_rate=21, vat_amount=2.1, gross_amount=12.1, status="concept")
        self.db.add_all([job, sale])
        self.db.commit()
        payload = {
            "external_order_id": "100", "order_number": "100", "external_status": "canceled", "payment_status": "geannuleerd",
            "items": [{"external_order_item_id": "line-1", "sku": variant.sku, "quantity_ordered": 2, "unit_sale_price": 6.05}],
        }

        first = upsert_imported_order(self.db, platform, payload)
        self.db.flush()
        second = upsert_imported_order(self.db, platform, payload)
        self.db.commit()

        self.assertEqual(first["action"], "updated")
        self.assertEqual(second["action"], "updated")
        self.assertEqual(order.status, ORDER_CANCELLED)
        self.assertEqual(inventory.quantity_reserved, 0)
        self.assertEqual(item.quantity_from_inventory, 0)
        self.assertEqual(job.status, PRINT_JOB_CANCELLED)
        self.assertEqual(sale.status, ACCOUNTING_CANCELLED)
        movements = self.db.scalars(select(InventoryMovement).where(InventoryMovement.order_id == order.id)).all()
        self.assertEqual([(movement.movement_type, movement.quantity) for movement in movements], [("reservering_vrijgegeven", 2)])

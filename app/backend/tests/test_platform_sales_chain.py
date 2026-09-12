from unittest.mock import patch

from support import *

from domain.statuses import ACCOUNTING_CANCELLED, ORDER_CANCELLED
from models import AccountingSale
from publishing.service import publish_publication, sync_publication
from services.order_import_service import upsert_imported_order
from services.order_processing import process_order


class PlatformSalesChainTestCase(BackendTestCase):
    def test_etsy_draft_change_order_processing_and_cancelled_reimport(self) -> None:
        platform = self.make_platform("etsy")
        product, variant = self.make_product_variant("CHAIN-SKU")
        inventory = ProductInventory(product_id=product.id, product_variant_id=variant.id, quantity_on_hand=5, quantity_reserved=0)
        media = ProductMedia(product_id=product.id, file_path="/uploads/product_media/1/photo.jpg", media_type="image", alt_text="Productfoto", is_primary=True)
        publication = ProductPlatformPublication(
            product_id=product.id,
            platform_id=platform.id,
            publication_status="klaar_voor_publicatie",
            platform_title="Eerste titel",
            platform_description="Eerste omschrijving",
            platform_category="Decoratie",
            platform_tags="3d print,cadeau",
            platform_shipping_profile_id="321",
        )
        self.db.add_all([inventory, media, publication])
        self.db.commit()
        connector = EtsyConnector(
            {"api_key": "key", "shared_secret": "secret", "access_token": "token", "shop_id": "123", "taxonomy_id": "456", "readiness_state_id": "789"},
            live_mode=True,
        )
        connector._request_form = lambda method, path, payload: {"listing_id": 42}
        connector._request_json = lambda method, path, payload=None: {"products": [{"product_id": 99, "sku": "CHAIN-SKU"}]}
        connector._upload_listing_images = lambda listing_id, items: {"success": True, "uploaded": len(items), "raw_response": {}}

        with patch("publishing.service.get_platform_connector", return_value=connector):
            published = publish_publication(self.db, publication)
            publication.platform_title = "Gewijzigde titel"
            synced = sync_publication(self.db, publication)

        paid_payload = {
            "external_order_id": "receipt-1", "order_number": "receipt-1", "external_status": "paid", "payment_status": "betaald",
            "total_amount": 12.95, "currency": "EUR",
            "items": [{"external_order_item_id": "transaction-1", "sku": variant.sku, "quantity_ordered": 1, "unit_sale_price": 12.95}],
        }
        imported = upsert_imported_order(self.db, platform, paid_payload)
        self.db.flush()
        processed = process_order(self.db, imported["order"]["id"])
        cancelled_payload = {**paid_payload, "external_status": "canceled", "payment_status": "geannuleerd"}
        upsert_imported_order(self.db, platform, cancelled_payload)
        repeated = upsert_imported_order(self.db, platform, cancelled_payload)
        self.db.commit()

        order = self.db.get(Order, imported["order"]["id"])
        sale = self.db.scalar(select(AccountingSale).where(AccountingSale.order_id == order.id))
        movements = self.db.scalars(select(InventoryMovement).where(InventoryMovement.order_id == order.id).order_by(InventoryMovement.id)).all()
        self.assertEqual(published["external_listing_id"], "42")
        self.assertEqual(synced["publication_status"], "gepubliceerd")
        self.assertEqual(processed["accounting_sale"]["created"], True)
        self.assertEqual(order.status, ORDER_CANCELLED)
        self.assertEqual(order.payment_status, "geannuleerd")
        self.assertEqual(inventory.quantity_reserved, 0)
        self.assertEqual(sale.status, ACCOUNTING_CANCELLED)
        self.assertEqual(repeated["warnings"], [])
        self.assertEqual([movement.movement_type for movement in movements], ["gereserveerd_voor_order", "reservering_vrijgegeven"])

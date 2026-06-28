import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("CONNECTORS_LIVE_MODE", "false")

from api.routes import (  # noqa: E402
    complete_print_job,
    convert_stock_recommendation,
    generate_stock_recommendations,
    process_order_inventory,
    publish_product_publication,
    suggest_print_batches,
    update_stock_recommendation,
    validate_publication_record,
)
from core.credentials import decrypt_credential, encrypt_credential, is_encrypted_credential  # noqa: E402
from connectors.shopify.connector import ShopifyConnector  # noqa: E402
from connectors.etsy.connector import EtsyConnector  # noqa: E402
from database import Base  # noqa: E402
from services.ai_product_assistant import generate_product_translation  # noqa: E402
from models import (  # noqa: E402
    InventoryMovement,
    Order,
    OrderItem,
    Platform,
    PrintJob,
    Product,
    ProductInventory,
    ProductMedia,
    ProductPlatformPublication,
    ProductVariantPlatformLink,
    ProductVariant,
    StockRecommendation,
)
from schemas.common import PrintJobComplete, StockRecommendationGenerate, StockRecommendationUpdate  # noqa: E402


class BusinessRuleTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.db = self.Session()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def make_platform(self, platform_type: str = "etsy") -> Platform:
        platform = Platform(name=platform_type.title(), type=platform_type, active=True)
        self.db.add(platform)
        self.db.commit()
        self.db.refresh(platform)
        return platform

    def make_product_variant(self, sku: str = "TEST-SKU") -> tuple[Product, ProductVariant]:
        product = Product(
            name="Test product",
            internal_title="Test product",
            short_description="Korte omschrijving",
            long_description="Lange omschrijving",
            sales_description="Verkooptekst",
            seo_title="SEO titel",
            seo_description="SEO omschrijving",
            product_type="decoratie",
            internal_category="test",
            status="klaar_voor_publicatie",
            active=True,
        )
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        variant = ProductVariant(
            product_id=product.id,
            variant_name="Rood PLA",
            sku=sku,
            color="rood",
            material="PLA",
            print_file_path="prints/test.3mf",
            estimated_print_time_minutes=45,
            estimated_filament_grams=32,
            default_sale_price=12.95,
            cost_price=2.50,
            active=True,
        )
        self.db.add(variant)
        self.db.commit()
        self.db.refresh(variant)
        return product, variant

    def test_order_inventory_reserves_available_stock_and_prints_only_shortage(self) -> None:
        platform = self.make_platform()
        product, variant = self.make_product_variant("INV-RESERVE")
        inventory = ProductInventory(
            product_id=product.id,
            product_variant_id=variant.id,
            color=variant.color,
            material=variant.material,
            quantity_on_hand=6,
            quantity_reserved=0,
        )
        order = Order(
            internal_order_number="T-ORDER-1",
            platform_id=platform.id,
            external_order_id="EXT-1",
            order_date=datetime.now(timezone.utc),
            total_amount=129.50,
            currency="EUR",
        )
        self.db.add_all([inventory, order])
        self.db.commit()
        order_item = OrderItem(
            order_id=order.id,
            sku=variant.sku,
            quantity_ordered=10,
            unit_sale_price=12.95,
        )
        self.db.add(order_item)
        self.db.commit()

        result = process_order_inventory(order.id, self.db)

        self.db.refresh(order_item)
        self.db.refresh(inventory)
        self.assertEqual(result["order"]["status"], "deels_te_printen")
        self.assertEqual(order_item.quantity_from_inventory, 6)
        self.assertEqual(order_item.quantity_to_print, 4)
        self.assertEqual(order_item.inventory_status, "deels_op_voorraad")
        self.assertEqual(inventory.quantity_reserved, 6)
        movement = self.db.scalar(select(InventoryMovement))
        self.assertEqual(movement.movement_type, "gereserveerd_voor_order")
        self.assertEqual(movement.quantity, 6)
        self.assertEqual(movement.quantity_on_hand_before, 6)
        self.assertEqual(movement.quantity_on_hand_after, 6)
        self.assertEqual(movement.quantity_reserved_before, 0)
        self.assertEqual(movement.quantity_reserved_after, 6)
        self.assertEqual(movement.free_stock_before, 6)
        self.assertEqual(movement.free_stock_after, 0)
        self.assertEqual(movement.source, "order_inventory_check")

    def test_print_result_sends_extra_successes_to_inventory_and_failed_to_movements(self) -> None:
        product, variant = self.make_product_variant("PRINT-RESULT")
        print_job = PrintJob(
            product_id=product.id,
            product_variant_id=variant.id,
            color=variant.color,
            material=variant.material,
            quantity_needed=4,
            quantity_planned=12,
            status="nieuw",
        )
        self.db.add(print_job)
        self.db.commit()

        result = complete_print_job(
            print_job.id,
            PrintJobComplete(quantity_succeeded=11, quantity_failed=1, quantity_to_order=4),
            self.db,
        )

        inventory = self.db.scalar(select(ProductInventory).where(ProductInventory.product_variant_id == variant.id))
        movements = self.db.scalars(select(InventoryMovement).order_by(InventoryMovement.id)).all()
        self.assertEqual(result["quantity_to_inventory"], 7)
        self.assertEqual(result["status"], "deels_mislukt")
        self.assertEqual(inventory.quantity_on_hand, 7)
        self.assertEqual(
            [(item.movement_type, item.quantity) for item in movements],
            [("print_gereed", 7), ("afgekeurd", 1)],
        )
        self.assertEqual(movements[0].source, "print_result")
        self.assertEqual(movements[0].quantity_on_hand_before, 0)
        self.assertEqual(movements[0].quantity_on_hand_after, 7)
        self.assertEqual(movements[0].free_stock_after, 7)

    def test_publication_validation_and_mock_publish(self) -> None:
        platform = self.make_platform("etsy")
        product, _variant = self.make_product_variant("PUB-MOCK")
        self.db.add(
            ProductMedia(
                product_id=product.id,
                file_path="media/test.jpg",
                media_type="image",
                alt_text="Test foto",
                sort_order=1,
                is_primary=True,
            )
        )
        publication = ProductPlatformPublication(
            product_id=product.id,
            platform_id=platform.id,
            publication_status="klaar_voor_publicatie",
            platform_title="Test titel",
            platform_description="Beschrijving",
            platform_category="Decoratie",
            platform_tags="een,twee,drie",
            platform_price_override=12.95,
            platform_shipping_profile_id="ship-test",
        )
        self.db.add(publication)
        self.db.commit()

        validation = validate_publication_record(self.db, publication)
        published = publish_product_publication(publication.id, self.db)

        self.assertTrue(validation["ready"])
        self.assertEqual(published["publication_status"], "gepubliceerd")
        self.assertTrue(published["external_product_id"].startswith("mock-etsy-product-"))
        self.assertIsNotNone(published["last_synced_at"])

    def test_stock_recommendation_uses_sales_safety_stock_and_free_stock(self) -> None:
        platform = self.make_platform()
        product, variant = self.make_product_variant("STOCK-ADVICE")
        inventory = ProductInventory(
            product_id=product.id,
            product_variant_id=variant.id,
            color=variant.color,
            material=variant.material,
            quantity_on_hand=3,
            quantity_reserved=0,
        )
        order = Order(
            internal_order_number="T-ORDER-2",
            platform_id=platform.id,
            external_order_id="EXT-2",
            order_date=datetime.now(timezone.utc),
            total_amount=129.50,
            currency="EUR",
        )
        self.db.add_all([inventory, order])
        self.db.commit()
        self.db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_variant_id=variant.id,
                sku=variant.sku,
                quantity_ordered=10,
                unit_sale_price=12.95,
            )
        )
        self.db.commit()

        result = generate_stock_recommendations(
            StockRecommendationGenerate(period_days=7, safety_stock=2, weeks_ahead=1),
            self.db,
        )

        recommendation = self.db.scalar(select(StockRecommendation))
        self.assertEqual(result["generated_count"], 1)
        self.assertEqual(recommendation.current_free_stock, 3)
        self.assertEqual(recommendation.expected_sales, 10)
        self.assertEqual(recommendation.recommended_stock_level, 12)
        self.assertEqual(recommendation.recommended_print_quantity, 9)
        self.assertIn("Gemiddelde weekverkoop", recommendation.reason)

    def test_adjusted_stock_recommendation_converts_adjusted_quantity_to_print_job(self) -> None:
        product, variant = self.make_product_variant("STOCK-ADJUST")
        recommendation = StockRecommendation(
            product_id=product.id,
            product_variant_id=variant.id,
            current_free_stock=3,
            expected_sales=10,
            safety_stock=2,
            recommended_stock_level=12,
            recommended_print_quantity=9,
            reason="Initieel advies.",
            status="nieuw",
        )
        self.db.add(recommendation)
        self.db.commit()
        self.db.refresh(recommendation)

        updated = update_stock_recommendation(
            recommendation.id,
            StockRecommendationUpdate(
                safety_stock=4,
                recommended_print_quantity=6,
                reason="Handmatig lager gezet.",
            ),
            self.db,
        )
        print_job = convert_stock_recommendation(recommendation.id, self.db)

        self.assertEqual(updated["status"], "aangepast")
        self.assertEqual(updated["recommended_print_quantity"], 6)
        self.assertEqual(print_job["quantity_needed"], 6)
        self.assertEqual(print_job["quantity_to_inventory"], 6)

    def test_batch_suggestions_group_open_jobs_by_material_and_color(self) -> None:
        product, variant = self.make_product_variant("BATCH-ADVICE")
        other_product, other_variant = self.make_product_variant("BATCH-OTHER")
        self.db.add_all(
            [
                PrintJob(
                    product_id=product.id,
                    product_variant_id=variant.id,
                    color="rood",
                    material="PLA",
                    quantity_needed=4,
                    quantity_planned=6,
                    quantity_to_order=4,
                    quantity_to_inventory=2,
                    estimated_print_time_minutes=180,
                    estimated_filament_grams=120,
                    status="nieuw",
                ),
                PrintJob(
                    product_id=other_product.id,
                    product_variant_id=other_variant.id,
                    color="rood",
                    material="PLA",
                    quantity_needed=2,
                    quantity_planned=2,
                    quantity_to_order=2,
                    quantity_to_inventory=0,
                    estimated_print_time_minutes=60,
                    estimated_filament_grams=40,
                    status="gepland",
                ),
                PrintJob(
                    product_id=product.id,
                    product_variant_id=variant.id,
                    color="zwart",
                    material="PETG",
                    quantity_needed=1,
                    quantity_planned=1,
                    estimated_print_time_minutes=30,
                    estimated_filament_grams=20,
                    status="verwerkt",
                ),
            ]
        )
        self.db.commit()

        suggestions = suggest_print_batches(self.db)

        self.assertEqual(len(suggestions), 1)
        suggestion = suggestions[0]
        self.assertEqual(suggestion["material"], "PLA")
        self.assertEqual(suggestion["color"], "rood")
        self.assertEqual(suggestion["job_count"], 2)
        self.assertEqual(suggestion["quantity_planned"], 8)
        self.assertEqual(suggestion["quantity_to_order"], 6)
        self.assertEqual(suggestion["quantity_to_inventory"], 2)
        self.assertEqual(suggestion["estimated_total_print_time_minutes"], 240)
        self.assertEqual(suggestion["estimated_total_filament_grams"], 160)
        self.assertIn("hetzelfde materiaal", suggestion["reason"])

    def test_credentials_are_encrypted_and_decrypted(self) -> None:
        secret = "super-secret-token"
        encrypted = encrypt_credential(secret)

        self.assertTrue(is_encrypted_credential(encrypted))
        self.assertNotIn(secret, encrypted)
        self.assertEqual(decrypt_credential(encrypted), secret)

    def test_shopify_live_publish_builds_graphql_product_create(self) -> None:
        calls = []
        connector = ShopifyConnector(
            {"access_token": "token", "shop_domain": "example-shop.myshopify.com"},
            live_mode=True,
        )

        def fake_graphql(query: str, variables: dict) -> dict:
            calls.append((query, variables))
            if "productVariantsBulkCreate" in query:
                return {
                    "data": {
                        "productVariantsBulkCreate": {
                            "productVariants": [
                                {
                                    "id": "gid://shopify/ProductVariant/456",
                                    "sku": "SHOPIFY-SKU",
                                    "inventoryItem": {"id": "gid://shopify/InventoryItem/789"},
                                }
                            ],
                            "userErrors": [],
                        }
                    }
                }
            return {
                "data": {
                    "productCreate": {
                        "product": {"id": "gid://shopify/Product/123", "title": "Shopify title"},
                        "userErrors": [],
                    }
                }
            }

        connector._graphql = fake_graphql
        result = connector.publish_product(
            {
                "product_id": 1,
                "title": "Shopify title",
                "description": "Description",
                "category": "Decoratie",
                "tags": ["tag1", "tag2"],
                "media": [
                    {"file_path": "https://example.com/image.jpg", "alt_text": "Alt"},
                    {"file_path": "/uploads/local-only.png", "alt_text": "Local"},
                ],
                "variants": [{"sku": "SHOPIFY-SKU"}],
            }
        )

        self.assertTrue(result.success)
        self.assertEqual(result.external_product_id, "gid://shopify/Product/123")
        query, variables = calls[0]
        self.assertIn("productCreate", query)
        self.assertEqual(variables["product"]["title"], "Shopify title")
        self.assertEqual(variables["product"]["tags"], ["tag1", "tag2"])
        self.assertEqual(len(variables["media"]), 1)
        self.assertEqual(variables["media"][0]["originalSource"], "https://example.com/image.jpg")
        variant_query, variant_variables = calls[1]
        self.assertIn("productVariantsBulkCreate", variant_query)
        self.assertEqual(variant_variables["productId"], "gid://shopify/Product/123")
        self.assertEqual(variant_variables["variants"][0]["sku"], "SHOPIFY-SKU")
        self.assertEqual(result.external_variant_ids["SHOPIFY-SKU"], "gid://shopify/ProductVariant/456")
        self.assertEqual(result.external_inventory_ids["SHOPIFY-SKU"], "gid://shopify/InventoryItem/789")

    def test_shopify_live_sync_requires_existing_external_product_id(self) -> None:
        connector = ShopifyConnector({"access_token": "token", "shop_domain": "example-shop"}, live_mode=True)

        result = connector.sync_product({"title": "No id", "variants": [{"sku": "SKU"}]})

        self.assertFalse(result.success)
        self.assertIn("external_product_id", result.message)

    def test_shopify_live_sync_builds_graphql_product_update(self) -> None:
        calls = []
        connector = ShopifyConnector({"access_token": "token", "shop_domain": "example-shop"}, live_mode=True)

        def fake_graphql(query: str, variables: dict) -> dict:
            calls.append((query, variables))
            if "productVariantsBulkCreate" in query:
                return {
                    "data": {
                        "productVariantsBulkCreate": {
                            "productVariants": [
                                {"id": "gid://shopify/ProductVariant/456", "sku": "SHOPIFY-SKU", "inventoryItem": {"id": "gid://shopify/InventoryItem/789"}}
                            ],
                            "userErrors": [],
                        }
                    }
                }
            return {
                "data": {
                    "productUpdate": {
                        "product": {"id": "gid://shopify/Product/123", "title": "Updated"},
                        "userErrors": [],
                    }
                }
            }

        connector._graphql = fake_graphql
        result = connector.sync_product(
            {
                "external_product_id": "gid://shopify/Product/123",
                "title": "Updated",
                "description": "Updated description",
                "variants": [{"sku": "SHOPIFY-SKU"}],
            }
        )

        self.assertTrue(result.success)
        query, variables = calls[0]
        self.assertIn("productUpdate", query)
        self.assertEqual(variables["product"]["id"], "gid://shopify/Product/123")
        self.assertEqual(variables["product"]["title"], "Updated")
        self.assertIn("productVariantsBulkCreate", calls[1][0])

    def test_shopify_import_orders_maps_graphql_payload(self) -> None:
        connector = ShopifyConnector({"access_token": "token", "shop_domain": "example-shop"}, live_mode=True)

        def fake_graphql(query: str, variables: dict) -> dict:
            self.assertIn("orders", query)
            self.assertEqual(variables["first"], 25)
            self.assertIsNone(variables["after"])
            self.assertEqual(variables["query"], "status:any created_at:>=2026-01-01T00:00:00+00:00")
            return {
                "data": {
                    "orders": {
                        "pageInfo": {"hasNextPage": False, "endCursor": "cursor-1"},
                        "edges": [
                            {
                                "node": {
                                    "id": "gid://shopify/Order/1",
                                    "name": "#1001",
                                    "email": "customer@example.com",
                                    "createdAt": "2026-06-27T10:00:00Z",
                                    "totalPriceSet": {"shopMoney": {"amount": "19.90", "currencyCode": "EUR"}},
                                    "customer": {"displayName": "Shopify klant", "email": "fallback@example.com"},
                                    "lineItems": {
                                        "edges": [
                                            {
                                                "node": {
                                                    "id": "gid://shopify/LineItem/1",
                                                    "sku": "DUMPLING-ROOD-PLA",
                                                    "quantity": 2,
                                                    "title": "Dumpling",
                                                    "variantTitle": "Rood",
                                                    "originalUnitPriceSet": {"shopMoney": {"amount": "9.95", "currencyCode": "EUR"}},
                                                    "variant": {"id": "gid://shopify/ProductVariant/1", "sku": "VARIANT-SKU"},
                                                }
                                            }
                                        ]
                                    },
                                }
                            }
                        ]
                    }
                }
            }

        connector._graphql = fake_graphql
        result = connector.import_orders(since="2026-01-01T00:00:00+00:00")

        self.assertTrue(result["success"])
        self.assertEqual(len(result["orders"]), 1)
        order = result["orders"][0]
        self.assertEqual(order["external_order_id"], "gid://shopify/Order/1")
        self.assertEqual(order["order_number"], "#1001")
        self.assertEqual(order["customer_name"], "Shopify klant")
        self.assertEqual(order["total_amount"], 19.9)
        self.assertEqual(order["items"][0]["sku"], "DUMPLING-ROOD-PLA")
        self.assertEqual(order["items"][0]["unit_sale_price"], 9.95)

    def test_shopify_import_orders_paginates_until_limit_or_last_page(self) -> None:
        connector = ShopifyConnector({"access_token": "token", "shop_domain": "example-shop"}, live_mode=True)
        calls = []

        def order_node(order_id: int) -> dict:
            return {
                "id": f"gid://shopify/Order/{order_id}",
                "name": f"#{order_id}",
                "email": "customer@example.com",
                "createdAt": "2026-06-27T10:00:00Z",
                "totalPriceSet": {"shopMoney": {"amount": "19.90", "currencyCode": "EUR"}},
                "customer": {"displayName": "Shopify klant", "email": "fallback@example.com"},
                "lineItems": {"edges": []},
            }

        def fake_graphql(query: str, variables: dict) -> dict:
            calls.append(variables)
            if variables["after"] is None:
                return {
                    "data": {
                        "orders": {
                            "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                            "edges": [{"node": order_node(1)}],
                        }
                    }
                }
            return {
                "data": {
                    "orders": {
                        "pageInfo": {"hasNextPage": False, "endCursor": "cursor-2"},
                        "edges": [{"node": order_node(2)}],
                    }
                }
            }

        connector._graphql = fake_graphql
        result = connector.import_orders(limit=10, page_size=1)

        self.assertTrue(result["success"])
        self.assertEqual(result["page_count"], 2)
        self.assertEqual([call["after"] for call in calls], [None, "cursor-1"])
        self.assertEqual([order["external_order_id"] for order in result["orders"]], ["gid://shopify/Order/1", "gid://shopify/Order/2"])

    def test_shopify_inventory_sync_requires_location_id_in_live_mode(self) -> None:
        connector = ShopifyConnector({"access_token": "token", "shop_domain": "example-shop"}, live_mode=True)

        result = connector.sync_inventory([{"external_inventory_id": "gid://shopify/InventoryItem/1", "quantity": 4}])

        self.assertFalse(result["success"])
        self.assertIn("location_id", result["message"])

    def test_shopify_inventory_sync_builds_inventory_set_quantities(self) -> None:
        connector = ShopifyConnector({"access_token": "token", "shop_domain": "example-shop", "location_id": "gid://shopify/Location/1"}, live_mode=True)
        calls = []

        def fake_graphql(query: str, variables: dict) -> dict:
            calls.append((query, variables))
            return {"data": {"inventorySetQuantities": {"inventoryAdjustmentGroup": {"createdAt": "2026-06-28T00:00:00Z"}, "userErrors": []}}}

        connector._graphql = fake_graphql
        result = connector.sync_inventory([{"external_inventory_id": "gid://shopify/InventoryItem/1", "quantity": 4}])

        self.assertTrue(result["success"])
        query, variables = calls[0]
        self.assertIn("inventorySetQuantities", query)
        self.assertEqual(variables["input"]["quantities"][0]["inventoryItemId"], "gid://shopify/InventoryItem/1")
        self.assertEqual(variables["input"]["quantities"][0]["locationId"], "gid://shopify/Location/1")
        self.assertEqual(variables["input"]["quantities"][0]["quantity"], 4)

    def test_etsy_mock_import_orders_returns_receipt_payload(self) -> None:
        connector = EtsyConnector({}, live_mode=False)

        result = connector.import_orders()

        self.assertTrue(result["success"])
        self.assertEqual(result["orders"][0]["external_order_id"], "mock-etsy-receipt-1001")
        self.assertEqual(result["orders"][0]["items"][0]["sku"], "DUMPLING-ROOD-PLA")

    def test_mock_product_translation_generates_without_openai_call(self) -> None:
        class Settings:
            ai_openai_enabled = False
            openai_api_key = None

        result = generate_product_translation(
            {
                "name": "Dumpling Rood",
                "title": "Dumpling Rood",
                "short_description": "Kleine decoratie voor op bureau.",
                "tags": ["decoratie", "bureau"],
            },
            "de",
            Settings(),
        )

        self.assertEqual(result["source"], "mock_translation")
        self.assertTrue(result["title"].startswith("[DE concept]"))


if __name__ == "__main__":
    unittest.main()

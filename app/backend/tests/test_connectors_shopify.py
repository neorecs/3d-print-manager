from support import *


class ShopifyConnectorTestCase(BackendTestCase):
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

    def test_shopify_live_publish_missing_credentials_returns_connector_error(self) -> None:
        connector = ShopifyConnector({}, live_mode=True)

        result = connector.publish_product({"product_id": 1, "title": "Geen credentials"})

        self.assertFalse(result.success)
        self.assertIn("access_token", result.message)
        self.assertIn("shop_domain", result.message)

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

    def test_shopify_live_import_missing_credentials_returns_clean_error(self) -> None:
        connector = ShopifyConnector({}, live_mode=True)

        result = connector.import_orders()

        self.assertFalse(result["success"])
        self.assertEqual(result["orders"], [])
        self.assertIn("access_token", result["message"])

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

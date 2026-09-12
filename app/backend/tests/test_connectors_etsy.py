from support import *


class EtsyConnectorTestCase(BackendTestCase):
    def test_etsy_mock_import_orders_returns_receipt_payload(self) -> None:
        connector = EtsyConnector({}, live_mode=False)

        result = connector.import_orders()

        self.assertTrue(result["success"])
        self.assertEqual(result["orders"][0]["external_order_id"], "mock-etsy-receipt-1001")
        self.assertEqual(result["orders"][0]["items"][0]["sku"], "DUMPLING-ROOD-PLA")

    def test_etsy_live_publish_missing_credentials_returns_connector_error(self) -> None:
        connector = EtsyConnector({}, live_mode=True)

        result = connector.publish_product({"product_id": 1, "title": "Geen credentials", "variants": [{"sku": "SKU", "default_sale_price": 12.95}]})

        self.assertFalse(result.success)
        self.assertIn("api_key", result.message)
        self.assertIn("shared_secret", result.message)
        self.assertIn("access_token", result.message)
        self.assertIn("shop_id", result.message)
        self.assertIn("taxonomy_id", result.message)

    def test_etsy_money_value_uses_amount_and_divisor(self) -> None:
        connector = EtsyConnector({}, live_mode=False)

        amount = connector._money_value({"amount": 2495, "divisor": 100})

        self.assertEqual(amount, 24.95)

    def test_etsy_live_publish_syncs_listing_inventory_and_media(self) -> None:
        connector = EtsyConnector(
            {
                "api_key": "key",
                "shared_secret": "secret",
                "access_token": "token",
                "shop_id": "123",
                "taxonomy_id": "456",
                "readiness_state_id": "789",
            },
            live_mode=True,
        )
        form_calls = []
        json_calls = []
        connector._request_form = lambda method, path, payload: form_calls.append((method, path, payload)) or {"listing_id": 42}
        connector._request_json = lambda method, path, payload=None: json_calls.append((method, path, payload)) or {"products": [{"product_id": 99, "sku": "ETSY-SKU"}]}
        connector._upload_listing_images = lambda listing_id, media: {"success": True, "uploaded": len(media), "raw_response": {}}

        result = connector.publish_product({
            "product_id": 1,
            "title": "Etsy product",
            "description": "Omschrijving",
            "tags": ["3d print", "cadeau"],
            "shipping_profile_id": "321",
            "media": [{"file_path": "/uploads/product_media/1/photo.jpg"}],
            "variants": [{"sku": "ETSY-SKU", "default_sale_price": 12.95, "quantity_available": 7}],
        })

        self.assertTrue(result.success)
        self.assertEqual(result.external_listing_id, "42")
        self.assertEqual(result.external_variant_ids, {"ETSY-SKU": "99"})
        self.assertEqual(form_calls[0][0], "POST")
        self.assertEqual(form_calls[0][2]["quantity"], 7)
        self.assertEqual(form_calls[0][2]["shipping_profile_id"], 321)
        self.assertEqual(json_calls[0][1], "/listings/42/inventory")
        self.assertEqual(json_calls[0][2]["products"][0]["offerings"][0]["quantity"], 7)

    def test_etsy_multiple_variants_require_taxonomy_property(self) -> None:
        connector = EtsyConnector(
            {"api_key": "key", "shared_secret": "secret", "access_token": "token", "shop_id": "1", "taxonomy_id": "2", "readiness_state_id": "3"},
            live_mode=True,
        )

        result = connector.publish_product({
            "shipping_profile_id": "4",
            "variants": [
                {"sku": "ONE", "default_sale_price": 10},
                {"sku": "TWO", "default_sale_price": 11},
            ],
        })

        self.assertFalse(result.success)
        self.assertIn("variation_property_id", result.message)

    def test_etsy_receipt_maps_paid_and_cancelled_status(self) -> None:
        connector = EtsyConnector({}, live_mode=False)

        paid = connector._receipt_to_order({"receipt_id": 1, "status": "paid", "grandtotal": {"amount": 1000, "divisor": 100}})
        cancelled = connector._receipt_to_order({"receipt_id": 2, "status": "canceled", "was_paid": False})

        self.assertEqual(paid["payment_status"], "betaald")
        self.assertEqual(cancelled["external_status"], "canceled")
        self.assertEqual(cancelled["payment_status"], "geannuleerd")

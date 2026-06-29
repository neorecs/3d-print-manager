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
        self.assertIn("access_token", result.message)
        self.assertIn("shop_id", result.message)
        self.assertIn("taxonomy_id", result.message)

    def test_etsy_money_value_uses_amount_and_divisor(self) -> None:
        connector = EtsyConnector({}, live_mode=False)

        amount = connector._money_value({"amount": 2495, "divisor": 100})

        self.assertEqual(amount, 24.95)

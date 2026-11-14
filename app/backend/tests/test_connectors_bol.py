import io
import json
from unittest.mock import patch
from urllib.error import HTTPError

from support import *

from connectors.bol import connector as bol_module
from connectors.bol.connector import BolConnector
from services.order_import_service import upsert_imported_order

CREDENTIALS = {"client_id": "client", "client_secret": "secret"}


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode() if self.payload is not None else b""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def router(routes: dict, calls: list):
    def fake_urlopen(request, timeout):
        key = f"{request.get_method()} {request.full_url}"
        calls.append((key, request.headers, request.data))
        for prefix, response in routes.items():
            if key.startswith(prefix):
                if isinstance(response, Exception):
                    raise response
                return FakeResponse(response)
        raise AssertionError(f"unexpected call {key}")
    return fake_urlopen


ORDER_DETAIL = {
    "orderId": "A2K8290LP8",
    "orderPlacedDateTime": "2026-11-13T21:04:00+01:00",
    "orderItems": [
        {"orderItemId": "6107434013", "quantity": 2, "quantityCancelled": 0, "unitPrice": 19.45, "totalPrice": 38.9,
         "offer": {"offerId": "o-1", "reference": None}, "product": {"ean": "8712345678906"}},
    ],
}


class BolConnectorTests(BackendTestCase):
    def setUp(self) -> None:
        super().setUp()
        bol_module._token_cache.clear()

    def test_token_is_reused_until_shortly_before_expiry(self) -> None:
        connector = BolConnector(CREDENTIALS, live_mode=True)
        connector.clock = lambda: 1000.0
        calls = []
        routes = {"POST https://login.bol.com/token": {"access_token": "t-1", "expires_in": 299}, "GET https://api.bol.com/retailer/orders": {"orders": []}}
        with patch("connectors.bol.connector.urlopen", side_effect=router(routes, calls)):
            connector.import_orders()
            connector.import_orders()
        token_calls = [call for call in calls if call[0].startswith("POST https://login.bol.com/token")]
        self.assertEqual(len(token_calls), 1)
        self.assertEqual(token_calls[0][1]["Authorization"], "Basic Y2xpZW50OnNlY3JldA==")

    def test_orders_are_mapped_with_ean_and_versioned_accept_header(self) -> None:
        connector = BolConnector(CREDENTIALS, live_mode=True)
        calls = []
        routes = {
            "POST https://login.bol.com/token": {"access_token": "t-1", "expires_in": 299},
            "GET https://api.bol.com/retailer/orders?": {"orders": [{"orderId": "A2K8290LP8"}]},
            "GET https://api.bol.com/retailer/orders/A2K8290LP8": ORDER_DETAIL,
        }
        with patch("connectors.bol.connector.urlopen", side_effect=router(routes, calls)):
            result = connector.import_orders()

        self.assertTrue(result["success"])
        order = result["orders"][0]
        self.assertEqual(order["external_order_id"], "A2K8290LP8")
        self.assertEqual(order["total_amount"], 38.9)
        self.assertEqual(order["items"][0]["ean"], "8712345678906")
        self.assertEqual(order["items"][0]["quantity_ordered"], 2)
        list_call = next(call for call in calls if "/retailer/orders?" in call[0])
        self.assertEqual(list_call[1]["Accept"], "application/vnd.retailer.v10+json")
        self.assertIn("fulfilment-method=FBR", list_call[0])

    def test_fully_cancelled_order_is_marked_cancelled(self) -> None:
        detail = {**ORDER_DETAIL, "orderItems": [{**ORDER_DETAIL["orderItems"][0], "quantityCancelled": 2}]}
        order = BolConnector._order_from_detail(detail)
        self.assertEqual(order["external_status"], "cancelled")

    def test_imported_bol_item_is_linked_to_variant_by_ean(self) -> None:
        platform = self.make_platform("bol")
        _, variant = self.make_product_variant("BOL-SKU")
        variant.ean = "8712345678906"
        self.db.commit()
        imported = upsert_imported_order(self.db, platform, BolConnector._order_from_detail(ORDER_DETAIL))
        item = self.db.scalar(select(OrderItem).where(OrderItem.order_id == imported["order"]["id"]))
        self.assertEqual(item.sku, "BOL-SKU")
        self.assertEqual(item.product_variant_id, variant.id)

    def test_publish_creates_one_offer_per_variant_with_ean(self) -> None:
        connector = BolConnector(CREDENTIALS, live_mode=True)
        requests = []
        connector._request = lambda method, path, media_type, payload=None: requests.append((method, path, media_type, payload)) or {"offerId": "offer-1"}

        result = connector.publish_product({"title": "Planterpot", "variants": [
            {"sku": "A", "ean": "8712345678906", "default_sale_price": 12.95, "quantity_available": 4},
        ]})

        self.assertTrue(result.success)
        self.assertEqual(result.external_variant_ids, {"A": "offer-1"})
        self.assertEqual(result.external_inventory_ids, {"A": "offer-1"})
        method, path, media_type, body = requests[0]
        self.assertEqual((method, path, media_type), ("POST", "/offers", "application/vnd.retailer.v11+json"))
        self.assertEqual(body["reference"], "A")
        self.assertEqual(body["pricing"]["bundlePrices"], [{"quantity": 1, "unitPrice": 12.95}])
        self.assertEqual(body["stock"], {"amount": 4, "managedByRetailer": True})

    def test_publish_without_ean_fails_for_that_variant(self) -> None:
        connector = BolConnector(CREDENTIALS, live_mode=True)
        connector._request = lambda *args, **kwargs: {"offerId": "x"}
        result = connector.publish_product({"title": "P", "variants": [{"sku": "A", "default_sale_price": 1}]})
        self.assertFalse(result.success)
        self.assertIn("EAN ontbreekt", result.message)

    def test_stock_sync_patches_each_offer(self) -> None:
        connector = BolConnector(CREDENTIALS, live_mode=True)
        requests = []
        connector._request = lambda method, path, media_type, payload=None: requests.append((method, path, payload)) or {}
        result = connector.sync_inventory([{"external_inventory_id": "offer-1", "quantity": 3}, {"external_inventory_id": None, "quantity": 9}])
        self.assertEqual(result["synced"], 1)
        self.assertEqual(requests, [("PATCH", "/offers/offer-1", {"stock": {"amount": 3}})])

    def test_rate_limit_is_retried(self) -> None:
        connector = BolConnector(CREDENTIALS, live_mode=True)
        connector.sleep = lambda seconds: None
        responses = [FakeResponse({"access_token": "t", "expires_in": 299}), HTTPError("https://api.bol.com", 429, "slow", {"Retry-After": "1"}, io.BytesIO(b"")), FakeResponse({"orders": []})]

        def fake_urlopen(request, timeout):
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        with patch("connectors.bol.connector.urlopen", side_effect=fake_urlopen):
            result = connector.import_orders()
        self.assertTrue(result["success"])

    def test_mock_mode_makes_no_calls(self) -> None:
        with patch("connectors.bol.connector.urlopen", side_effect=AssertionError("no network in mock mode")):
            result = BolConnector({}, live_mode=False).import_orders()
        self.assertTrue(result["success"])

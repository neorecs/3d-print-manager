import io
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.error import HTTPError

from support import *

from models import PlatformImportLog
from services.order_import_runner import FIRST_IMPORT_WINDOW, IMPORT_OVERLAP, default_since, import_platform_orders


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class OrderImportRunnerTests(BackendTestCase):
    def test_first_import_starts_thirty_days_back(self) -> None:
        platform = self.make_platform("etsy")
        now = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(default_since(self.db, platform, now=now), now - FIRST_IMPORT_WINDOW)

    def test_next_import_continues_from_last_successful_import(self) -> None:
        platform = self.make_platform("etsy")
        last = datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc)
        self.db.add_all([
            PlatformImportLog(platform_id=platform.id, import_type="orders", status="klaar", started_at=last),
            PlatformImportLog(platform_id=platform.id, import_type="orders", status="fout", started_at=last + timedelta(hours=1)),
        ])
        self.db.commit()

        since = default_since(self.db, platform)

        self.assertEqual(since, last - IMPORT_OVERLAP)

    def test_import_passes_remembered_start_date_to_connector(self) -> None:
        platform = self.make_platform("etsy")
        last = datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc)
        self.db.add(PlatformImportLog(platform_id=platform.id, import_type="orders", status="klaar", started_at=last))
        self.db.commit()
        seen = {}

        def fake_import(self_connector, limit=25, since=None, page_size=50):
            seen["since"] = since
            return {"success": True, "message": "ok", "orders": []}

        with patch.object(EtsyConnector, "import_orders", fake_import):
            summary = import_platform_orders(self.db, platform)
        self.db.commit()

        self.assertEqual(seen["since"], (last - IMPORT_OVERLAP).isoformat())
        self.assertEqual(summary["errors"], [])
        logs = self.db.scalars(select(PlatformImportLog).where(PlatformImportLog.status == "klaar")).all()
        self.assertEqual(len(logs), 2)

    def test_import_returns_newly_created_orders(self) -> None:
        platform = self.make_platform("etsy")
        payload = {
            "external_order_id": "r-1", "order_number": "r-1", "external_status": "paid", "payment_status": "betaald",
            "items": [{"external_order_item_id": "t-1", "sku": "ONBEKEND", "quantity_ordered": 1, "unit_sale_price": 10}],
        }
        with patch.object(EtsyConnector, "import_orders", lambda self_connector, **kwargs: {"success": True, "orders": [payload]}):
            first = import_platform_orders(self.db, platform)
            second = import_platform_orders(self.db, platform)

        self.assertEqual(len(first["created"]), 1)
        self.assertEqual(len(second["created"]), 0)
        self.assertEqual(len(second["updated"]), 1)

    def test_failed_import_is_logged_and_does_not_move_start_date(self) -> None:
        platform = self.make_platform("etsy")
        with patch.object(EtsyConnector, "import_orders", lambda self_connector, **kwargs: {"success": False, "message": "Etsy HTTP 500"}):
            summary = import_platform_orders(self.db, platform)
        self.db.commit()

        self.assertEqual(summary["errors"], ["Etsy HTTP 500"])
        now = datetime.now(timezone.utc)
        self.assertLess(default_since(self.db, platform, now=now), now - timedelta(days=29))


class ShopifyRetryTests(BackendTestCase):
    def connector(self) -> ShopifyConnector:
        connector = ShopifyConnector({"access_token": "token", "shop_domain": "shop.myshopify.com"}, live_mode=True)
        connector.sleep = lambda seconds: None
        return connector

    def test_http_429_is_retried(self) -> None:
        responses = [HTTPError("https://shop", 429, "slow down", {"Retry-After": "1"}, io.BytesIO(b"")), FakeResponse({"data": {"ok": True}})]

        def fake_urlopen(request, timeout):
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        with patch("connectors.shopify.connector.urlopen", side_effect=fake_urlopen):
            result = self.connector()._graphql("query { shop { name } }", {})
        self.assertEqual(result, {"data": {"ok": True}})

    def test_graphql_throttled_error_is_retried(self) -> None:
        responses = [
            FakeResponse({"errors": [{"message": "Throttled", "extensions": {"code": "THROTTLED"}}]}),
            FakeResponse({"data": {"ok": True}}),
        ]
        with patch("connectors.shopify.connector.urlopen", side_effect=lambda request, timeout: responses.pop(0)):
            result = self.connector()._graphql("query { shop { name } }", {})
        self.assertEqual(result, {"data": {"ok": True}})

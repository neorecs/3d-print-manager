import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from connectors.base import ConnectorResult, PlatformConnector


ETSY_API_BASE = "https://openapi.etsy.com/v3/application"


class EtsyConnector(PlatformConnector):
    platform_type = "etsy"
    required_credentials = ["api_key", "access_token", "shop_id"]

    def publish_product(self, payload: dict) -> ConnectorResult:
        if not self.live_mode:
            return self._mock_result("publish", payload)
        missing = [key for key in ["taxonomy_id"] if not self.credentials.get(key)]
        if missing:
            return ConnectorResult(False, f"Etsy live-publicatie mist verplichte Etsy-velden: {', '.join(missing)}.")
        variants = payload.get("variants") or []
        first_variant = variants[0] if variants else {}
        price = payload.get("price") or first_variant.get("default_sale_price")
        if price is None:
            return ConnectorResult(False, "Etsy live-publicatie vereist een verkoopprijs.")
        response = self._request(
            "POST",
            f"/shops/{self.credentials['shop_id']}/listings",
            {
                "quantity": 1,
                "title": payload.get("title"),
                "description": payload.get("description"),
                "price": str(price),
                "who_made": "i_did",
                "when_made": "made_to_order",
                "taxonomy_id": int(self.credentials["taxonomy_id"]),
                "type": "physical",
            },
        )
        errors = response.get("errors") or []
        if errors:
            return ConnectorResult(False, self._format_errors(errors), raw_response=response)
        listing_id = str(response.get("listing_id") or response.get("listing", {}).get("listing_id") or "")
        if not listing_id:
            return ConnectorResult(False, "Etsy gaf geen listing-ID terug.", raw_response=response)
        return ConnectorResult(
            True,
            "Etsy conceptlisting aangemaakt.",
            external_product_id=listing_id,
            external_listing_id=listing_id,
            raw_response=response,
        )

    def sync_product(self, payload: dict) -> ConnectorResult:
        if not self.live_mode:
            return self._mock_result("sync", payload)
        listing_id = payload.get("external_listing_id") or payload.get("external_product_id")
        if not listing_id:
            return ConnectorResult(False, "Etsy sync vereist een bestaande external_listing_id.")
        response = self._request(
            "PUT",
            f"/shops/{self.credentials['shop_id']}/listings/{listing_id}",
            {
                "title": payload.get("title"),
                "description": payload.get("description"),
            },
        )
        errors = response.get("errors") or []
        if errors:
            return ConnectorResult(False, self._format_errors(errors), raw_response=response)
        return ConnectorResult(True, "Etsy listing gesynchroniseerd.", external_product_id=str(listing_id), external_listing_id=str(listing_id), raw_response=response)

    def import_orders(self, limit: int = 25, since: str | None = None, page_size: int = 50) -> dict:
        if not self.live_mode:
            return {
                "success": True,
                "message": "Etsy orderimport uitgevoerd in mockmodus.",
                "orders": [
                    {
                        "external_order_id": "mock-etsy-receipt-1001",
                        "order_number": "MOCK-ETSY-1001",
                        "customer_name": "Mock Etsy klant",
                        "customer_email": "mock-etsy@example.com",
                        "order_date": "2026-06-25T10:00:00+00:00",
                        "total_amount": 24.95,
                        "currency": "EUR",
                        "items": [
                            {
                                "external_order_item_id": "mock-etsy-transaction-1",
                                "sku": "DUMPLING-ROOD-PLA",
                                "quantity_ordered": 1,
                                "unit_sale_price": 24.95,
                            }
                        ],
                    }
                ],
                "page_count": 1,
            }
        params = {"limit": max(1, min(limit, 100))}
        response = self._request("GET", f"/shops/{self.credentials['shop_id']}/receipts?{urlencode(params)}")
        errors = response.get("errors") or []
        if errors:
            return {"success": False, "message": self._format_errors(errors), "orders": [], "raw_response": response}
        receipts = response.get("results") or []
        return {
            "success": True,
            "message": f"{len(receipts)} Etsy order(s) opgehaald.",
            "orders": [self._receipt_to_order(receipt) for receipt in receipts],
            "page_count": 1,
            "raw_response": response,
        }

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        data = None if payload is None else json.dumps({key: value for key, value in payload.items() if value not in (None, "", [])}).encode("utf-8")
        request = Request(
            f"{ETSY_API_BASE}{path}",
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.credentials["api_key"],
                "Authorization": f"Bearer {self.credentials['access_token']}",
            },
            method=method,
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return {"errors": [{"message": f"Etsy HTTP {exc.code}: {body}"}]}
        except URLError as exc:
            return {"errors": [{"message": f"Etsy verbinding mislukt: {exc.reason}"}]}

    def _receipt_to_order(self, receipt: dict) -> dict:
        transactions = receipt.get("transactions") or []
        order_date = self._timestamp_to_iso(receipt.get("created_timestamp"))
        return {
            "external_order_id": str(receipt.get("receipt_id")),
            "order_number": str(receipt.get("receipt_id")),
            "customer_name": receipt.get("name") or receipt.get("buyer_user_id"),
            "customer_email": receipt.get("buyer_email"),
            "order_date": order_date,
            "total_amount": self._money_value(receipt.get("grandtotal")),
            "currency": (receipt.get("grandtotal") or {}).get("currency_code") or "EUR",
            "items": [self._transaction_to_item(item) for item in transactions],
        }

    def _transaction_to_item(self, transaction: dict) -> dict:
        return {
            "external_order_item_id": str(transaction.get("transaction_id")),
            "sku": transaction.get("sku"),
            "quantity_ordered": int(transaction.get("quantity") or 0),
            "unit_sale_price": self._money_value(transaction.get("price")),
            "title": transaction.get("title"),
        }

    def _money_value(self, value: dict | None) -> float | None:
        if not value:
            return None

    def _timestamp_to_iso(self, value) -> str | None:
        if not value:
            return None
        try:
            return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            return str(value)
        amount = value.get("amount")
        divisor = value.get("divisor") or 100
        try:
            return round(float(amount) / float(divisor), 2)
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    def _format_errors(self, errors: list[dict]) -> str:
        return "; ".join(error.get("message", str(error)) for error in errors)

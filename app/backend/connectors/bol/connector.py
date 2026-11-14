"""bol Retailer API: orders (v10), offers and stock (Offers v11).

Authentication is OAuth2 client credentials against login.bol.com; a token is
valid for about five minutes and is reused until shortly before it expires
(bol asks not to request a token per call). Every offer is tied to an EAN, so
each variant needs an EAN before it can be offered.

Not yet verified against live bol credentials: run one controlled test per
step (orders, offer, stock) before turning on live mode.
"""

import base64
import json
import logging
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from connectors.base import ConnectorResult, PlatformConnector
from connectors.retry import MAX_ATTEMPTS, RETRYABLE_STATUS_CODES, retry_delay

BOL_TOKEN_URL = "https://login.bol.com/token"
BOL_API_BASE = "https://api.bol.com/retailer"
ORDERS_MEDIA_TYPE = "application/vnd.retailer.v10+json"
OFFERS_MEDIA_TYPE = "application/vnd.retailer.v11+json"
TOKEN_MARGIN_SECONDS = 30
logger = logging.getLogger(__name__)

_token_cache: dict[str, tuple[str, float]] = {}


class BolConnector(PlatformConnector):
    platform_type = "bol"
    required_credentials = ["client_id", "client_secret"]
    sleep = staticmethod(time.sleep)
    clock = staticmethod(time.time)

    # ----- authentication -------------------------------------------------
    def _token(self) -> str:
        client_id = self.credentials["client_id"]
        cached = _token_cache.get(client_id)
        if cached and cached[1] - TOKEN_MARGIN_SECONDS > self.clock():
            return cached[0]
        basic = base64.b64encode(f"{client_id}:{self.credentials['client_secret']}".encode()).decode()
        request = Request(
            BOL_TOKEN_URL,
            data=urlencode({"grant_type": "client_credentials"}).encode(),
            headers={"Authorization": f"Basic {basic}", "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        token = data["access_token"]
        _token_cache[client_id] = (token, self.clock() + int(data.get("expires_in") or 299))
        return token

    def _request(self, method: str, path: str, media_type: str, payload: dict | None = None) -> dict:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        for attempt in range(MAX_ATTEMPTS):
            try:
                token = self._token()
            except (HTTPError, URLError, OSError, KeyError, json.JSONDecodeError) as exc:
                return {"errors": [{"message": f"bol login mislukt: {exc}"}]}
            headers = {"Authorization": f"Bearer {token}", "Accept": media_type}
            if body is not None:
                headers["Content-Type"] = media_type
            request = Request(f"{BOL_API_BASE}{path}", data=body, headers=headers, method=method)
            try:
                with urlopen(request, timeout=30) as response:
                    raw = response.read().decode("utf-8")
                    return json.loads(raw) if raw else {}
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                logger.warning("bol HTTP error: %s", exc.code)
                if exc.code == 401:
                    _token_cache.pop(self.credentials["client_id"], None)
                if (exc.code in RETRYABLE_STATUS_CODES or exc.code == 401) and attempt < MAX_ATTEMPTS - 1:
                    self.sleep(retry_delay(exc.headers.get("Retry-After") if exc.headers else None, attempt))
                    continue
                return {"errors": [{"message": f"bol HTTP {exc.code}: {detail[:500]}"}]}
            except URLError as exc:
                if attempt < MAX_ATTEMPTS - 1:
                    self.sleep(retry_delay(None, attempt))
                    continue
                return {"errors": [{"message": f"bol verbinding mislukt: {exc.reason}"}]}
            except (json.JSONDecodeError, OSError) as exc:
                return {"errors": [{"message": f"bol request mislukt: {exc}"}]}
        return {"errors": [{"message": "bol request mislukt na herhaalde pogingen."}]}

    @staticmethod
    def _error_text(response: dict) -> str | None:
        errors = response.get("errors")
        if errors:
            return "; ".join(error.get("message", str(error)) for error in errors)
        return None

    # ----- orders ---------------------------------------------------------
    def import_orders(self, limit: int = 25, since: str | None = None, page_size: int = 50) -> dict:
        if not self.live_mode:
            return {
                "success": True,
                "message": "bol orderimport uitgevoerd in mockmodus.",
                "orders": [{
                    "external_order_id": "mock-bol-1001", "order_number": "MOCK-BOL-1001", "order_date": "2026-06-25T10:00:00+00:00",
                    "total_amount": 19.95, "currency": "EUR", "external_status": "open", "payment_status": "betaald",
                    "items": [{"external_order_item_id": "mock-bol-item-1", "sku": "DUMPLING-ROOD-PLA", "ean": None, "quantity_ordered": 1, "unit_sale_price": 19.95}],
                }],
            }
        missing = self.missing_required_credentials()
        if missing:
            return {"success": False, "message": self.live_credentials_error("orderimport", missing), "orders": []}

        summaries = []
        for page in range(1, 4):
            response = self._request("GET", f"/orders?{urlencode({'fulfilment-method': 'FBR', 'status': 'OPEN', 'page': page})}", ORDERS_MEDIA_TYPE)
            error = self._error_text(response)
            if error:
                return {"success": False, "message": error, "orders": []}
            page_orders = response.get("orders") or []
            summaries.extend(page_orders)
            if len(page_orders) < 50:
                break

        orders = []
        for summary in summaries[: max(1, limit)]:
            detail = self._request("GET", f"/orders/{summary['orderId']}", ORDERS_MEDIA_TYPE)
            error = self._error_text(detail)
            if error:
                return {"success": False, "message": error, "orders": orders}
            orders.append(self._order_from_detail(detail))
        message = f"{len(orders)} bol order(s) opgehaald."
        if len(summaries) > len(orders):
            message += " Importlimiet bereikt; er zijn mogelijk nog meer orders."
        return {"success": True, "message": message, "orders": orders, "has_next_page": len(summaries) > len(orders)}

    @staticmethod
    def _order_from_detail(detail: dict) -> dict:
        items = []
        total = 0.0
        all_cancelled = True
        for item in detail.get("orderItems") or []:
            quantity = int(item.get("quantity") or 0)
            cancelled = int(item.get("quantityCancelled") or 0)
            unit_price = item.get("unitPrice")
            if quantity - cancelled > 0:
                all_cancelled = False
            total += float(item.get("totalPrice") if item.get("totalPrice") is not None else (unit_price or 0) * quantity)
            items.append({
                "external_order_item_id": str(item.get("orderItemId")),
                "sku": (item.get("offer") or {}).get("reference") or None,
                "ean": (item.get("product") or {}).get("ean") or item.get("ean"),
                "quantity_ordered": max(quantity - cancelled, 0),
                "unit_sale_price": unit_price,
            })
        return {
            "external_order_id": str(detail.get("orderId")),
            "order_number": str(detail.get("orderId")),
            "order_date": detail.get("orderPlacedDateTime"),
            "total_amount": round(total, 2),
            "currency": "EUR",
            "external_status": "cancelled" if items and all_cancelled else "open",
            "payment_status": "betaald",
            "customer_name": None,
            "items": items,
        }

    # ----- offers and stock ----------------------------------------------
    def publish_product(self, payload: dict) -> ConnectorResult:
        if not self.live_mode:
            return self._mock_result("publish", payload)
        missing = self.missing_required_credentials()
        if missing:
            return ConnectorResult(False, self.live_credentials_error("publicatie", missing))
        variant_ids: dict[str, str] = {}
        errors = []
        for variant in payload.get("variants") or []:
            if not variant.get("ean"):
                errors.append(f"{variant.get('sku')}: EAN ontbreekt")
                continue
            price = variant.get("price") if variant.get("price") is not None else variant.get("default_sale_price")
            body = {
                "ean": variant["ean"],
                "reference": variant.get("sku"),
                "onHoldByRetailer": False,
                "unknownProductTitle": (payload.get("title") or "")[:500],
                "condition": {"name": "NEW"},
                "pricing": {"bundlePrices": [{"quantity": 1, "unitPrice": float(price or 0)}]},
                "stock": {"amount": int(variant.get("quantity_available") or 0), "managedByRetailer": True},
                "fulfilment": {"method": "FBR", "deliveryCode": self.credentials.get("delivery_code") or "3-5d"},
            }
            response = self._request("POST", "/offers", OFFERS_MEDIA_TYPE, body)
            error = self._error_text(response)
            if error or not response.get("offerId"):
                errors.append(f"{variant.get('sku')}: {error or 'geen offerId ontvangen'}")
                continue
            variant_ids[str(variant.get("sku"))] = str(response["offerId"])
        if errors:
            return ConnectorResult(False, "bol aanbod niet volledig aangemaakt: " + "; ".join(errors),
                                   external_variant_ids=variant_ids, external_inventory_ids=dict(variant_ids))
        return ConnectorResult(True, f"{len(variant_ids)} bol aanbieding(en) aangemaakt.",
                               external_product_id=next(iter(variant_ids.values()), None),
                               external_variant_ids=variant_ids, external_inventory_ids=dict(variant_ids))

    def sync_product(self, payload: dict) -> ConnectorResult:
        if not self.live_mode:
            return self._mock_result("sync", payload)
        return ConnectorResult(False, "bol: prijs en titel wijzig je voorlopig in het bol verkoopdashboard; voorraad wordt wel gesynchroniseerd.")

    def sync_inventory(self, quantities: list[dict]) -> dict:
        prepared = [item for item in quantities if item.get("external_inventory_id")]
        if not self.live_mode:
            return {"success": True, "message": f"bol voorraad-sync uitgevoerd in mockmodus voor {len(prepared)} aanbieding(en).", "synced": len(prepared), "errors": []}
        missing = self.missing_required_credentials()
        if missing:
            return {"success": False, "message": self.live_credentials_error("voorraad-sync", missing), "synced": 0, "errors": missing}
        synced, errors = 0, []
        for item in prepared:
            response = self._request("PATCH", f"/offers/{item['external_inventory_id']}", OFFERS_MEDIA_TYPE,
                                     {"stock": {"amount": max(int(item.get("quantity") or 0), 0)}})
            error = self._error_text(response)
            if error:
                errors.append(f"{item.get('sku') or item['external_inventory_id']}: {error}")
            else:
                synced += 1
        return {"success": not errors, "message": f"{synced} bol aanbieding(en) bijgewerkt.", "synced": synced, "errors": errors}

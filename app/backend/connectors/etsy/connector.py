import json
import logging
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from connectors.base import ConnectorResult, PlatformConnector


ETSY_API_BASE = "https://openapi.etsy.com/v3/application"
PRODUCT_MEDIA_ROOT = Path("uploads/product_media")
logger = logging.getLogger(__name__)


class EtsyConnector(PlatformConnector):
    platform_type = "etsy"
    required_credentials = ["api_key", "shared_secret", "access_token", "shop_id", "taxonomy_id", "readiness_state_id"]
    order_import_credentials = ["api_key", "shared_secret", "access_token", "shop_id"]

    def publish_product(self, payload: dict) -> ConnectorResult:
        if not self.live_mode:
            return self._mock_result("publish", payload)
        missing = self.missing_required_credentials()
        if missing:
            return ConnectorResult(False, self.live_credentials_error("live-publicatie", missing))
        if not payload.get("shipping_profile_id"):
            return ConnectorResult(False, "Etsy live-publicatie vereist een verzendprofiel.")

        variants = payload.get("variants") or []
        validation_error = self._variant_configuration_error(variants)
        if validation_error:
            return ConnectorResult(False, validation_error)
        first_variant = variants[0]
        price = payload.get("price") or self._variant_price(first_variant)
        response = self._request_form(
            "POST",
            f"/shops/{self.credentials['shop_id']}/listings",
            {
                "quantity": self._listing_quantity(variants),
                "title": payload.get("title"),
                "description": payload.get("description"),
                "price": str(price),
                "who_made": "i_did",
                "when_made": "made_to_order",
                "taxonomy_id": int(self.credentials["taxonomy_id"]),
                "shipping_profile_id": int(payload["shipping_profile_id"]),
                "readiness_state_id": int(self.credentials["readiness_state_id"]),
                "type": "physical",
                "tags": payload.get("tags") or [],
            },
        )
        errors = response.get("errors") or []
        if errors:
            return ConnectorResult(False, self._format_errors(errors), raw_response=response)
        listing_id = str(response.get("listing_id") or response.get("listing", {}).get("listing_id") or "")
        if not listing_id:
            return ConnectorResult(False, "Etsy gaf geen listing-ID terug.", raw_response=response)
        return self._complete_listing_sync(listing_id, payload, response)

    def sync_product(self, payload: dict) -> ConnectorResult:
        if not self.live_mode:
            return self._mock_result("sync", payload)
        missing = self.missing_required_credentials()
        if missing:
            return ConnectorResult(False, self.live_credentials_error("sync", missing))
        listing_id = payload.get("external_listing_id") or payload.get("external_product_id")
        if not listing_id:
            return ConnectorResult(False, "Etsy sync vereist een bestaande external_listing_id.")
        variants = payload.get("variants") or []
        validation_error = self._variant_configuration_error(variants)
        if validation_error:
            return ConnectorResult(False, validation_error, external_product_id=str(listing_id), external_listing_id=str(listing_id))
        response = self._request_form(
            "PATCH",
            f"/shops/{self.credentials['shop_id']}/listings/{listing_id}",
            {
                "title": payload.get("title"),
                "description": payload.get("description"),
                "tags": payload.get("tags") or [],
                "shipping_profile_id": payload.get("shipping_profile_id"),
            },
        )
        errors = response.get("errors") or []
        if errors:
            return ConnectorResult(False, self._format_errors(errors), external_product_id=str(listing_id), external_listing_id=str(listing_id), raw_response=response)
        return self._complete_listing_sync(str(listing_id), payload, response)

    def _complete_listing_sync(self, listing_id: str, payload: dict, listing_response: dict) -> ConnectorResult:
        inventory = self._sync_inventory(listing_id, payload)
        if not inventory["success"]:
            return ConnectorResult(False, inventory["message"], external_product_id=listing_id, external_listing_id=listing_id, raw_response={"listing": listing_response, "inventory": inventory.get("raw_response")})
        images = self._upload_listing_images(listing_id, payload.get("media") or [])
        if not images["success"]:
            return ConnectorResult(False, images["message"], external_product_id=listing_id, external_listing_id=listing_id, external_variant_ids=inventory["external_variant_ids"], raw_response={"listing": listing_response, "inventory": inventory.get("raw_response"), "images": images.get("raw_response")})
        return ConnectorResult(
            True,
            f"Etsy conceptlisting en {len(inventory['external_variant_ids'])} variant(en) gesynchroniseerd; {images['uploaded']} foto('s) verwerkt.",
            external_product_id=listing_id,
            external_listing_id=listing_id,
            external_variant_ids=inventory["external_variant_ids"],
            raw_response={"listing": listing_response, "inventory": inventory.get("raw_response"), "images": images.get("raw_response")},
        )

    def _sync_inventory(self, listing_id: str, payload: dict) -> dict:
        variants = payload.get("variants") or []
        property_id = self.credentials.get("variation_property_id")
        products = []
        for variant in variants:
            property_values = []
            if len(variants) > 1:
                property_values = [{"property_id": int(property_id), "property_name": "Uitvoering", "values": [variant.get("variant_name") or variant.get("sku")]}]
            products.append({
                "sku": variant.get("sku"),
                "offerings": [{
                    "quantity": max(0, int(variant.get("quantity_available") or 0)),
                    "is_enabled": True,
                    "price": float(payload.get("price") or self._variant_price(variant)),
                    "readiness_state_id": int(self.credentials["readiness_state_id"]),
                }],
                "property_values": property_values,
            })
        varied_properties = [int(property_id)] if len(variants) > 1 else []
        response = self._request_json("PUT", f"/listings/{listing_id}/inventory", {
            "products": products,
            "price_on_property": varied_properties,
            "quantity_on_property": varied_properties,
            "sku_on_property": varied_properties,
        })
        errors = response.get("errors") or []
        if errors:
            return {"success": False, "message": f"Etsy voorraadsync mislukt: {self._format_errors(errors)}", "raw_response": response}
        external_ids = {str(product["sku"]): str(product["product_id"]) for product in response.get("products") or [] if product.get("sku") and product.get("product_id")}
        for variant in variants:
            sku = variant.get("sku")
            if sku and sku not in external_ids:
                external_ids[sku] = f"{listing_id}:{sku}"
        return {"success": True, "external_variant_ids": external_ids, "raw_response": response}

    def _upload_listing_images(self, listing_id: str, media: list[dict]) -> dict:
        uploaded, responses = 0, []
        for rank, item in enumerate(media, start=1):
            source = self._resolve_media_path(item.get("file_path"))
            if not source:
                return {"success": False, "message": f"Etsy foto-upload vereist een lokaal productbestand; niet gevonden: {item.get('file_path') or '-'}.", "uploaded": uploaded, "raw_response": {"responses": responses}}
            try:
                body = self._request_multipart(
                    f"/shops/{self.credentials['shop_id']}/listings/{listing_id}/images",
                    source,
                    {"rank": str(rank), "overwrite": "true", "alt_text": item.get("alt_text") or ""},
                )
            except OSError as exc:
                logger.warning("Etsy image upload failed: %s", exc)
                body = {"errors": [{"message": f"Etsy foto-upload mislukt: {exc}"}]}
            responses.append(body)
            errors = body.get("errors") or []
            if errors:
                return {"success": False, "message": self._format_errors(errors), "uploaded": uploaded, "raw_response": {"responses": responses}}
            uploaded += 1
        return {"success": True, "uploaded": uploaded, "raw_response": {"responses": responses}}

    def import_orders(self, limit: int = 25, since: str | None = None, page_size: int = 50) -> dict:
        if not self.live_mode:
            return {
                "success": True,
                "message": "Etsy orderimport uitgevoerd in mockmodus.",
                "orders": [{
                    "external_order_id": "mock-etsy-receipt-1001", "order_number": "MOCK-ETSY-1001",
                    "customer_name": "Mock Etsy klant", "customer_email": "mock-etsy@example.com",
                    "order_date": "2026-06-25T10:00:00+00:00", "total_amount": 24.95, "currency": "EUR",
                    "external_status": "paid", "payment_status": "betaald",
                    "items": [{"external_order_item_id": "mock-etsy-transaction-1", "sku": "DUMPLING-ROOD-PLA", "quantity_ordered": 1, "unit_sale_price": 24.95}],
                }],
                "page_count": 1,
            }
        missing = [key for key in self.order_import_credentials if not self.credentials.get(key)]
        if missing:
            return {"success": False, "message": self.live_credentials_error("orderimport", missing), "orders": [], "page_count": 0}
        safe_limit = max(1, min(limit, 100))
        safe_page_size = max(1, min(page_size, 100, safe_limit))
        orders, raw_pages, offset = [], [], 0
        while len(orders) < safe_limit:
            params = {"limit": min(safe_page_size, safe_limit - len(orders)), "offset": offset, "sort_on": "updated", "sort_order": "asc"}
            if since:
                params["min_last_modified"] = int(datetime.fromisoformat(since.replace("Z", "+00:00")).timestamp())
            response = self._request_json("GET", f"/shops/{self.credentials['shop_id']}/receipts?{urlencode(params)}")
            raw_pages.append(response)
            errors = response.get("errors") or []
            if errors:
                return {"success": False, "message": self._format_errors(errors), "orders": orders, "page_count": len(raw_pages), "raw_response": {"pages": raw_pages}}
            receipts = response.get("results") or []
            orders.extend(self._receipt_to_order(receipt) for receipt in receipts)
            if len(receipts) < params["limit"]:
                break
            offset += len(receipts)
        return {"success": True, "message": f"{len(orders)} Etsy order(s) opgehaald over {len(raw_pages)} pagina(s).", "orders": orders, "page_count": len(raw_pages), "raw_response": {"pages": raw_pages}}

    def _variant_configuration_error(self, variants: list[dict]) -> str | None:
        if not variants:
            return "Etsy vereist minimaal een actieve variant met SKU en prijs."
        if any(not variant.get("sku") or self._variant_price(variant) is None for variant in variants):
            return "Elke Etsy-variant vereist een SKU en verkoopprijs."
        if len(variants) > 1 and not self.credentials.get("variation_property_id"):
            return "Etsy-publicatie met meerdere varianten vereist credential variation_property_id uit de Etsy-taxonomie."
        return None

    def _variant_price(self, variant: dict):
        return variant.get("action_sale_price") or variant.get("default_sale_price")

    def _listing_quantity(self, variants: list[dict]) -> int:
        return max(1, sum(max(0, int(item.get("quantity_available") or 0)) for item in variants))

    def _resolve_media_path(self, file_path: str | None) -> Path | None:
        if not file_path or not file_path.startswith("/uploads/product_media/"):
            return None
        target = (Path("uploads") / file_path.removeprefix("/uploads/")).resolve()
        allowed = PRODUCT_MEDIA_ROOT.resolve()
        if target != allowed and allowed not in target.parents:
            return None
        return target if target.is_file() else None

    def _request_form(self, method: str, path: str, payload: dict | None = None) -> dict:
        data = None if payload is None else urlencode({key: value for key, value in payload.items() if value not in (None, "", [])}, doseq=True).encode("utf-8")
        return self._urlopen_request(method, path, data, "application/x-www-form-urlencoded")

    def _request_json(self, method: str, path: str, payload: dict | None = None) -> dict:
        data = None if payload is None else json.dumps({key: value for key, value in payload.items() if value not in (None, "", [])}).encode("utf-8")
        return self._urlopen_request(method, path, data, "application/json")

    def _urlopen_request(self, method: str, path: str, data: bytes | None, content_type: str) -> dict:
        request = Request(f"{ETSY_API_BASE}{path}", data=data, headers=self._headers(content_type), method=method)
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            logger.warning("Etsy HTTP error: %s", exc.code)
            return {"errors": [{"message": f"Etsy HTTP {exc.code}: {body}"}]}
        except URLError as exc:
            logger.warning("Etsy connection error: %s", exc.reason)
            return {"errors": [{"message": f"Etsy verbinding mislukt: {exc.reason}"}]}
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Etsy request failed: %s", exc)
            return {"errors": [{"message": f"Etsy request mislukt: {exc}"}]}

    def _request_multipart(self, path: str, source: Path, fields: dict[str, str]) -> dict:
        boundary = f"----3d-print-manager-{uuid.uuid4().hex}"
        chunks = []
        for name, value in fields.items():
            chunks.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode(),
            ])
        content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="image"; filename="{source.name}"\r\n'.encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            source.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ])
        return self._urlopen_request("POST", path, b"".join(chunks), f"multipart/form-data; boundary={boundary}")

    def _headers(self, content_type: str | None = "application/json", include_content_type: bool = True) -> dict[str, str]:
        api_key = self.credentials["api_key"]
        shared_secret = self.credentials.get("shared_secret")
        x_api_key = api_key if ":" in api_key or not shared_secret else f"{api_key}:{shared_secret}"
        headers = {"x-api-key": x_api_key, "Authorization": f"Bearer {self.credentials['access_token']}"}
        if include_content_type and content_type:
            headers["Content-Type"] = content_type
        return headers

    def _receipt_to_order(self, receipt: dict) -> dict:
        status = str(receipt.get("status") or "").strip().lower()
        was_paid = bool(receipt.get("was_paid")) or status in {"paid", "completed"}
        return {
            "external_order_id": str(receipt.get("receipt_id")), "order_number": str(receipt.get("receipt_id")),
            "customer_name": receipt.get("name") or receipt.get("buyer_user_id"), "customer_email": receipt.get("buyer_email"),
            "order_date": self._timestamp_to_iso(receipt.get("created_timestamp")), "total_amount": self._money_value(receipt.get("grandtotal")),
            "currency": (receipt.get("grandtotal") or {}).get("currency_code") or "EUR", "external_status": status,
            "payment_status": "betaald" if was_paid else ("geannuleerd" if status == "canceled" else "niet_betaald"),
            "items": [self._transaction_to_item(item) for item in receipt.get("transactions") or []],
        }

    def _transaction_to_item(self, transaction: dict) -> dict:
        return {"external_order_item_id": str(transaction.get("transaction_id")), "sku": transaction.get("sku"), "quantity_ordered": int(transaction.get("quantity") or 0), "unit_sale_price": self._money_value(transaction.get("price")), "title": transaction.get("title")}

    def _money_value(self, value: dict | None) -> float | None:
        if not value:
            return None
        try:
            return round(float(value.get("amount")) / float(value.get("divisor") or 100), 2)
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    def _timestamp_to_iso(self, value) -> str | None:
        if not value:
            return None
        try:
            return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            return str(value)

    def _format_errors(self, errors: list[dict]) -> str:
        return "; ".join(error.get("message", str(error)) for error in errors)

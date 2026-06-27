import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from connectors.base import ConnectorResult, PlatformConnector


SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-04")


class ShopifyConnector(PlatformConnector):
    platform_type = "shopify"
    required_credentials = ["access_token", "shop_domain"]

    def publish_product(self, payload: dict) -> ConnectorResult:
        if not self.live_mode:
            return self._mock_result("publish", payload)
        variables = {
            "product": self._product_input(payload),
            "media": self._media_input(payload),
        }
        response = self._graphql(self._product_create_mutation(), variables)
        top_level_errors = response.get("errors") or []
        if top_level_errors:
            return ConnectorResult(False, self._format_user_errors(top_level_errors), raw_response=response)
        data = response.get("data", {}).get("productCreate", {})
        errors = data.get("userErrors") or []
        if errors:
            return ConnectorResult(False, self._format_user_errors(errors), raw_response=response)
        product = data.get("product") or {}
        product_id = product.get("id")
        if not product_id:
            return ConnectorResult(False, "Shopify gaf geen product-ID terug.", raw_response=response)
        return ConnectorResult(
            True,
            "Shopify product aangemaakt.",
            external_product_id=product_id,
            external_listing_id=product_id,
            raw_response=response,
        )

    def sync_product(self, payload: dict) -> ConnectorResult:
        if not self.live_mode:
            return self._mock_result("sync", payload)
        product_id = payload.get("external_product_id") or payload.get("external_listing_id")
        if not product_id:
            return ConnectorResult(False, "Shopify sync vereist een bestaand external_product_id.")
        product_input = self._product_input(payload)
        product_input["id"] = product_id
        variables = {
            "product": product_input,
            "media": self._media_input(payload),
        }
        response = self._graphql(self._product_update_mutation(), variables)
        top_level_errors = response.get("errors") or []
        if top_level_errors:
            return ConnectorResult(False, self._format_user_errors(top_level_errors), raw_response=response)
        data = response.get("data", {}).get("productUpdate", {})
        errors = data.get("userErrors") or []
        if errors:
            return ConnectorResult(False, self._format_user_errors(errors), raw_response=response)
        product = data.get("product") or {}
        return ConnectorResult(
            True,
            "Shopify product gesynchroniseerd.",
            external_product_id=product.get("id") or product_id,
            external_listing_id=product.get("id") or product_id,
            raw_response=response,
        )

    def import_orders(self, limit: int = 25, since: str | None = None) -> dict:
        if not self.live_mode:
            return {
                "success": True,
                "message": "Shopify orderimport uitgevoerd in mockmodus.",
                "orders": [
                    {
                        "external_order_id": "mock-shopify-order-1001",
                        "order_number": "MOCK-SHOPIFY-1001",
                        "customer_name": "Mock Shopify klant",
                        "customer_email": "mock-shopify@example.com",
                        "order_date": "2026-06-25T10:00:00+00:00",
                        "total_amount": 19.9,
                        "currency": "EUR",
                        "items": [
                            {
                                "external_order_item_id": "mock-shopify-line-1",
                                "sku": "DUMPLING-ROOD-PLA",
                                "quantity_ordered": 2,
                                "unit_sale_price": 9.95,
                            }
                        ],
                    }
                ],
            }

        query = "status:any"
        if since:
            query = f"{query} created_at:>={since}"
        response = self._graphql(self._orders_query(), {"first": max(1, min(limit, 50)), "query": query})
        errors = response.get("errors") or []
        if errors:
            return {"success": False, "message": self._format_user_errors(errors), "orders": [], "raw_response": response}

        edges = response.get("data", {}).get("orders", {}).get("edges") or []
        return {
            "success": True,
            "message": f"{len(edges)} Shopify order(s) opgehaald.",
            "orders": [self._order_from_node(edge.get("node") or {}) for edge in edges],
            "raw_response": response,
        }

    def _graphql(self, query: str, variables: dict) -> dict:
        shop_domain = self._normalized_shop_domain()
        request = Request(
            f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/graphql.json",
            data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": self.credentials["access_token"],
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return {"errors": [{"message": f"Shopify HTTP {exc.code}: {body}"}]}
        except URLError as exc:
            return {"errors": [{"message": f"Shopify verbinding mislukt: {exc.reason}"}]}

        if payload.get("errors"):
            messages = ", ".join(error.get("message", str(error)) for error in payload["errors"])
            return {"data": {}, "errors": [{"message": messages}], "raw": payload}
        return payload

    def _product_input(self, payload: dict) -> dict:
        product_input = {
            "title": payload.get("title"),
            "descriptionHtml": payload.get("description"),
            "productType": payload.get("category"),
            "tags": payload.get("tags") or [],
        }
        return {key: value for key, value in product_input.items() if value not in (None, "", [])}

    def _media_input(self, payload: dict) -> list[dict]:
        media = []
        for item in payload.get("media", []):
            source = item.get("file_path")
            if not source or not source.startswith(("http://", "https://")):
                continue
            media.append(
                {
                    "originalSource": source,
                    "alt": item.get("alt_text") or payload.get("title") or "",
                    "mediaContentType": "IMAGE",
                }
            )
        return media

    def _normalized_shop_domain(self) -> str:
        shop_domain = self.credentials["shop_domain"].replace("https://", "").replace("http://", "").strip("/")
        if "." not in shop_domain:
            shop_domain = f"{shop_domain}.myshopify.com"
        return shop_domain

    def _money_amount(self, value: dict | None) -> float | None:
        amount = ((value or {}).get("shopMoney") or {}).get("amount")
        if amount is None:
            return None
        try:
            return float(amount)
        except (TypeError, ValueError):
            return None

    def _money_currency(self, value: dict | None) -> str:
        return ((value or {}).get("shopMoney") or {}).get("currencyCode") or "EUR"

    def _order_from_node(self, node: dict) -> dict:
        customer = node.get("customer") or {}
        line_edges = node.get("lineItems", {}).get("edges") or []
        return {
            "external_order_id": node.get("id"),
            "order_number": node.get("name") or node.get("id"),
            "customer_name": customer.get("displayName"),
            "customer_email": node.get("email") or customer.get("email"),
            "order_date": node.get("createdAt"),
            "total_amount": self._money_amount(node.get("totalPriceSet")),
            "currency": self._money_currency(node.get("totalPriceSet")),
            "items": [self._order_item_from_node(edge.get("node") or {}) for edge in line_edges],
        }

    def _order_item_from_node(self, node: dict) -> dict:
        variant = node.get("variant") or {}
        return {
            "external_order_item_id": node.get("id"),
            "sku": node.get("sku") or variant.get("sku"),
            "quantity_ordered": int(node.get("quantity") or 0),
            "unit_sale_price": self._money_amount(node.get("originalUnitPriceSet")),
            "title": node.get("title"),
            "variant_title": node.get("variantTitle"),
        }

    def _format_user_errors(self, errors: list[dict]) -> str:
        messages = []
        for error in errors:
            field = ".".join(str(part) for part in error.get("field") or [])
            message = error.get("message", "Onbekende Shopify fout")
            messages.append(f"{field}: {message}" if field else message)
        return "; ".join(messages)

    def _product_create_mutation(self) -> str:
        return """
        mutation ProductCreate($product: ProductCreateInput!, $media: [CreateMediaInput!]) {
          productCreate(product: $product, media: $media) {
            product {
              id
              title
            }
            userErrors {
              field
              message
            }
          }
        }
        """

    def _product_update_mutation(self) -> str:
        return """
        mutation ProductUpdate($product: ProductUpdateInput!, $media: [CreateMediaInput!]) {
          productUpdate(product: $product, media: $media) {
            product {
              id
              title
            }
            userErrors {
              field
              message
            }
          }
        }
        """

    def _orders_query(self) -> str:
        return """
        query Orders($first: Int!, $query: String) {
          orders(first: $first, reverse: true, sortKey: CREATED_AT, query: $query) {
            edges {
              node {
                id
                name
                email
                createdAt
                totalPriceSet {
                  shopMoney {
                    amount
                    currencyCode
                  }
                }
                customer {
                  displayName
                  email
                }
                lineItems(first: 50) {
                  edges {
                    node {
                      id
                      sku
                      title
                      variantTitle
                      quantity
                      originalUnitPriceSet {
                        shopMoney {
                          amount
                          currencyCode
                        }
                      }
                      variant {
                        id
                        sku
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """

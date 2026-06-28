import json
import os
import uuid
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
        variants_result = self._sync_variants(product_id, payload, create_missing=True)
        if not variants_result["success"]:
            return ConnectorResult(False, variants_result["message"], raw_response={"product": response, "variants": variants_result.get("raw_response")})
        return ConnectorResult(
            True,
            self._product_message("Shopify product aangemaakt", variants_result),
            external_product_id=product_id,
            external_listing_id=product_id,
            external_variant_ids=variants_result["external_variant_ids"],
            external_inventory_ids=variants_result["external_inventory_ids"],
            raw_response={"product": response, "variants": variants_result.get("raw_response")},
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
        variants_result = self._sync_variants(product.get("id") or product_id, payload, create_missing=True)
        if not variants_result["success"]:
            return ConnectorResult(False, variants_result["message"], raw_response={"product": response, "variants": variants_result.get("raw_response")})
        return ConnectorResult(
            True,
            self._product_message("Shopify product gesynchroniseerd", variants_result),
            external_product_id=product.get("id") or product_id,
            external_listing_id=product.get("id") or product_id,
            external_variant_ids=variants_result["external_variant_ids"],
            external_inventory_ids=variants_result["external_inventory_ids"],
            raw_response={"product": response, "variants": variants_result.get("raw_response")},
        )

    def import_orders(self, limit: int = 25, since: str | None = None, page_size: int = 50) -> dict:
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
                "page_count": 1,
                "has_next_page": False,
                "end_cursor": None,
            }

        query = "status:any"
        if since:
            query = f"{query} created_at:>={since}"
        orders = []
        raw_pages = []
        after = None
        page_count = 0
        end_cursor = None
        has_next_page = True
        safe_limit = max(1, min(limit, 250))
        safe_page_size = max(1, min(page_size, 50, safe_limit))

        while has_next_page and len(orders) < safe_limit:
            response = self._graphql(
                self._orders_query(),
                {
                    "first": min(safe_page_size, safe_limit - len(orders)),
                    "after": after,
                    "query": query,
                },
            )
            raw_pages.append(response)
            errors = response.get("errors") or []
            if errors:
                return {
                    "success": False,
                    "message": f"Shopify orderimport mislukt op pagina {page_count + 1}: {self._format_user_errors(errors)}",
                    "orders": orders,
                    "page_count": page_count,
                    "has_next_page": bool(after),
                    "end_cursor": after,
                    "raw_response": {"pages": raw_pages},
                }

            data = response.get("data", {}).get("orders", {})
            edges = data.get("edges") or []
            orders.extend(self._order_from_node(edge.get("node") or {}) for edge in edges)
            page_info = data.get("pageInfo") or {}
            has_next_page = bool(page_info.get("hasNextPage")) and bool(edges)
            end_cursor = page_info.get("endCursor")
            after = end_cursor
            page_count += 1

        return {
            "success": True,
            "message": f"{len(orders)} Shopify order(s) opgehaald over {page_count} pagina(s).",
            "orders": orders,
            "page_count": page_count,
            "has_next_page": has_next_page,
            "end_cursor": end_cursor,
            "raw_response": {"pages": raw_pages},
        }

    def sync_inventory(self, quantities: list[dict]) -> dict:
        prepared = [
            {
                "inventoryItemId": item.get("external_inventory_id"),
                "locationId": self.credentials.get("location_id"),
                "quantity": int(item.get("quantity") or 0),
            }
            for item in quantities
            if item.get("external_inventory_id")
        ]
        if not self.live_mode:
            return {
                "success": True,
                "message": f"Shopify voorraad-sync uitgevoerd in mockmodus voor {len(prepared)} variant(en).",
                "synced": len(prepared),
                "errors": [],
                "raw_response": {"mode": "mock", "quantities": prepared},
            }
        if not self.credentials.get("location_id"):
            return {
                "success": False,
                "message": "Shopify voorraad-sync vereist credential location_id.",
                "synced": 0,
                "errors": ["location_id ontbreekt"],
            }
        if not prepared:
            return {
                "success": False,
                "message": "Geen Shopify inventory-item-ID's gevonden om voorraad te synchroniseren.",
                "synced": 0,
                "errors": ["external_inventory_id ontbreekt"],
            }

        variables = {
            "input": {
                "name": "available",
                "reason": "correction",
                "referenceDocumentUri": f"3d-print-manager://shopify-inventory-sync/{uuid.uuid4()}",
                "ignoreCompareQuantity": True,
                "quantities": prepared,
            }
        }
        response = self._graphql(self._inventory_set_quantities_mutation(), variables)
        errors = response.get("errors") or []
        if errors:
            return {
                "success": False,
                "message": self._format_user_errors(errors),
                "synced": 0,
                "errors": [self._format_user_errors(errors)],
                "raw_response": response,
            }
        user_errors = response.get("data", {}).get("inventorySetQuantities", {}).get("userErrors") or []
        if user_errors:
            return {
                "success": False,
                "message": self._format_user_errors(user_errors),
                "synced": 0,
                "errors": [self._format_user_errors(user_errors)],
                "raw_response": response,
            }
        return {
            "success": True,
            "message": f"{len(prepared)} Shopify voorraadregel(s) gesynchroniseerd.",
            "synced": len(prepared),
            "errors": [],
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

    def _sync_variants(self, product_id: str, payload: dict, create_missing: bool = True) -> dict:
        variants = [variant for variant in payload.get("variants", []) if variant.get("sku")]
        if not variants:
            return self._variant_sync_result({}, {}, {"skipped": 0})

        create_inputs = []
        update_inputs = []
        for variant in variants:
            variant_id = variant.get("external_variant_id")
            variant_input = self._variant_input(variant)
            if variant_id:
                variant_input["id"] = variant_id
                update_inputs.append(variant_input)
            elif create_missing:
                create_inputs.append(variant_input)

        external_variant_ids: dict[str, str] = {}
        external_inventory_ids: dict[str, str] = {}
        raw_response = {}

        if update_inputs:
            response = self._graphql(self._product_variants_bulk_update_mutation(), {"productId": product_id, "variants": update_inputs})
            raw_response["update"] = response
            error = self._variant_error(response, "productVariantsBulkUpdate")
            if error:
                return self._variant_sync_error(error, raw_response)
            self._collect_variant_ids(response.get("data", {}).get("productVariantsBulkUpdate", {}).get("productVariants") or [], external_variant_ids, external_inventory_ids)

        if create_inputs:
            response = self._graphql(
                self._product_variants_bulk_create_mutation(),
                {"productId": product_id, "variants": create_inputs},
            )
            raw_response["create"] = response
            error = self._variant_error(response, "productVariantsBulkCreate")
            if error:
                return self._variant_sync_error(error, raw_response)
            self._collect_variant_ids(response.get("data", {}).get("productVariantsBulkCreate", {}).get("productVariants") or [], external_variant_ids, external_inventory_ids)

        return self._variant_sync_result(
            external_variant_ids,
            external_inventory_ids,
            {"created": len(create_inputs), "updated": len(update_inputs), "skipped": len(variants) - len(create_inputs) - len(update_inputs)},
            raw_response,
        )

    def _variant_input(self, variant: dict) -> dict:
        price = variant.get("default_sale_price")
        if price is None:
            price = variant.get("price")
        option_name = variant.get("variant_name") or "Standaard"
        option_values = [{"name": str(option_name), "optionName": "Uitvoering"}]
        variant_input = {
            "sku": variant.get("sku"),
            "price": str(price) if price is not None else None,
            "optionValues": option_values,
        }
        return {key: value for key, value in variant_input.items() if value not in (None, "", [])}

    def _variant_error(self, response: dict, key: str) -> str | None:
        errors = response.get("errors") or []
        if errors:
            return self._format_user_errors(errors)
        user_errors = response.get("data", {}).get(key, {}).get("userErrors") or []
        if user_errors:
            return self._format_user_errors(user_errors)
        return None

    def _variant_sync_error(self, message: str, raw_response: dict) -> dict:
        return {
            "success": False,
            "message": f"Shopify variantsync mislukt: {message}",
            "external_variant_ids": {},
            "external_inventory_ids": {},
            "raw_response": raw_response,
        }

    def _variant_sync_result(self, external_variant_ids: dict[str, str], external_inventory_ids: dict[str, str], counts: dict, raw_response: dict | None = None) -> dict:
        return {
            "success": True,
            "message": f"{counts.get('created', 0)} variant(en) aangemaakt, {counts.get('updated', 0)} bijgewerkt, {counts.get('skipped', 0)} overgeslagen.",
            "external_variant_ids": external_variant_ids,
            "external_inventory_ids": external_inventory_ids,
            "counts": counts,
            "raw_response": raw_response or {},
        }

    def _collect_variant_ids(self, variants: list[dict], external_variant_ids: dict[str, str], external_inventory_ids: dict[str, str]) -> None:
        for variant in variants:
            sku = variant.get("sku")
            variant_id = variant.get("id")
            inventory_id = (variant.get("inventoryItem") or {}).get("id")
            if sku and variant_id:
                external_variant_ids[sku] = variant_id
            if sku and inventory_id:
                external_inventory_ids[sku] = inventory_id

    def _product_message(self, base: str, variants_result: dict) -> str:
        return f"{base}. {variants_result.get('message', '').strip()}".strip()

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

    def _product_variants_bulk_create_mutation(self) -> str:
        return """
        mutation ProductVariantsBulkCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkCreate(productId: $productId, variants: $variants, strategy: REMOVE_STANDALONE_VARIANT) {
            productVariants {
              id
              sku
              inventoryItem {
                id
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """

    def _product_variants_bulk_update_mutation(self) -> str:
        return """
        mutation ProductVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            productVariants {
              id
              sku
              inventoryItem {
                id
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """

    def _inventory_set_quantities_mutation(self) -> str:
        return """
        mutation InventorySetQuantities($input: InventorySetQuantitiesInput!) {
          inventorySetQuantities(input: $input) {
            inventoryAdjustmentGroup {
              createdAt
              reason
            }
            userErrors {
              field
              message
              code
            }
          }
        }
        """

    def _orders_query(self) -> str:
        return """
        query Orders($first: Int!, $after: String, $query: String) {
          orders(first: $first, after: $after, reverse: true, sortKey: CREATED_AT, query: $query) {
            pageInfo {
              hasNextPage
              endCursor
            }
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

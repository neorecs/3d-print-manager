from support import *
from publishing.service import build_publication_payload


class PublishingTestCase(BackendTestCase):
    def test_publication_validation_and_mock_publish(self) -> None:
        platform = self.make_platform("etsy")
        product, _variant = self.make_product_variant("PUB-MOCK")
        self.db.add(
            ProductMedia(
                product_id=product.id,
                file_path="media/test.jpg",
                media_type="image",
                alt_text="Test foto",
                sort_order=1,
                is_primary=True,
            )
        )
        publication = ProductPlatformPublication(
            product_id=product.id,
            platform_id=platform.id,
            publication_status="klaar_voor_publicatie",
            platform_title="Test titel",
            platform_description="Beschrijving",
            platform_category="Decoratie",
            platform_tags="een,twee,drie",
            platform_price_override=12.95,
            platform_shipping_profile_id="ship-test",
        )
        self.db.add(publication)
        self.db.commit()

        validation = validate_publication_record(self.db, publication)
        published = publish_product_publication(publication.id, self.db)

        self.assertTrue(validation["ready"])
        self.assertEqual(published["publication_status"], "gepubliceerd")
        self.assertTrue(published["external_product_id"].startswith("mock-etsy-product-"))
        self.assertIsNotNone(published["last_synced_at"])

    def test_publication_payload_contains_free_stock_and_ignores_inactive_variants(self) -> None:
        platform = self.make_platform("etsy")
        product, variant = self.make_product_variant("PUB-STOCK")
        inactive = ProductVariant(product_id=product.id, variant_name="Oud", sku="PUB-INACTIVE", color="zwart", material="PLA", default_sale_price=9.95, active=False)
        inventory = ProductInventory(product_id=product.id, product_variant_id=variant.id, quantity_on_hand=8, quantity_reserved=3)
        publication = ProductPlatformPublication(product_id=product.id, platform_id=platform.id, platform_title="Titel", platform_description="Tekst", platform_category="Decoratie", platform_shipping_profile_id="123")
        self.db.add_all([inactive, inventory, publication])
        self.db.commit()

        payload = build_publication_payload(self.db, publication)

        self.assertEqual(len(payload["variants"]), 1)
        self.assertEqual(payload["variants"][0]["sku"], "PUB-STOCK")
        self.assertEqual(payload["variants"][0]["quantity_available"], 5)

    def test_publication_validation_requires_active_market_translations(self) -> None:
        platform = self.make_platform("shopify")
        product, _variant = self.make_product_variant("MARKET-TRANSLATION")
        self.db.add_all(
            [
                SalesMarket(country_code="NL", country_name="Nederland", primary_language="nl", active=True),
                SalesMarket(country_code="BE", country_name="Belgie", primary_language="nl", additional_languages="fr", active=True),
                SalesMarket(country_code="DE", country_name="Duitsland", primary_language="de", active=True),
                ProductMedia(product_id=product.id, file_path="media/test.jpg", media_type="image", is_primary=True),
            ]
        )
        publication = ProductPlatformPublication(
            product_id=product.id,
            platform_id=platform.id,
            publication_status="klaar_voor_publicatie",
            platform_title="Test titel",
            platform_description="Beschrijving",
            platform_category="Decoratie",
            platform_tags="test,product",
            platform_price_override=12.95,
        )
        self.db.add(publication)
        self.db.commit()

        missing_translation = validate_publication_record(self.db, publication)
        self.assertFalse(missing_translation["ready"])
        self.assertTrue(any("Duitsland" in error and "'de'" in error for error in missing_translation["errors"]))
        self.assertTrue(any("Belgie" in warning and "'fr'" in warning for warning in missing_translation["warnings"]))

        self.db.add(
            ProductTranslation(
                product_id=product.id,
                language_code="de",
                title="Deutscher Titel",
                short_description="Deutsche Beschreibung",
            )
        )
        self.db.commit()

        with_german_translation = validate_publication_record(self.db, publication)
        self.assertTrue(with_german_translation["ready"])
        self.assertTrue(any(item["country_code"] == "DE" and item["severity"] == "ok" for item in with_german_translation["market_checks"]))

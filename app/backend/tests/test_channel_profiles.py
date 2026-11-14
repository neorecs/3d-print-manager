import io
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from support import *

from api.routes import channels
from api.routes.channels import ManualOrder, ManualOrderItem, MarkPlaced, create_manual_order, listing_package, listing_package_photos, mark_publication_placed
from publishing.channel_profiles import channel_profile, is_assisted, listing_issues


class FakeRequest:
    class state:
        user_email = "admin@example.com"


class ChannelProfileTests(BackendTestCase):
    def make_publication(self, platform_type: str, **fields):
        platform = self.make_platform(platform_type)
        product, variant = self.make_product_variant(f"SKU-{platform_type}")
        self.db.add(ProductMedia(product_id=product.id, file_path=f"/uploads/product_media/{product.id}/a.jpg", media_type="image", sort_order=1, is_primary=True))
        publication = ProductPlatformPublication(
            product_id=product.id, platform_id=platform.id, publication_status="klaar_voor_publicatie",
            platform_title=fields.get("title", "Planterpot Hex M"), platform_description="Mooie pot", platform_category="Wonen",
            platform_tags=fields.get("tags", "pot,plant"), platform_price_override=12.95, platform_shipping_profile_id="1",
        )
        self.db.add(publication)
        self.db.commit()
        return platform, product, variant, publication

    def test_profiles_know_which_channels_need_hulpmodus(self) -> None:
        self.assertFalse(is_assisted("etsy"))
        self.assertFalse(is_assisted("bol"))
        self.assertTrue(is_assisted("vinted"))
        self.assertTrue(is_assisted("marktplaats"))
        self.assertTrue(is_assisted("iets-anders"))

    def test_etsy_limits_keep_their_messages(self) -> None:
        errors = listing_issues(channel_profile("etsy"), "Etsy", "x" * 141, ["a" * 21] + [str(i) for i in range(13)], 1, 1)
        self.assertIn("Etsy: Etsy-titel mag maximaal 140 tekens zijn.", errors)
        self.assertIn("Etsy: Etsy ondersteunt maximaal 13 tags.", errors)
        self.assertTrue(any("Etsy-tags mogen maximaal 20 tekens zijn" in error for error in errors))

    def test_etsy_requires_an_original_photo(self) -> None:
        errors = listing_issues(channel_profile("etsy"), "Etsy", "Titel", [], photo_count=2, original_photo_count=0)
        self.assertTrue(any("onbewerkte foto" in error for error in errors))

    def test_vinted_photo_limit(self) -> None:
        errors = listing_issues(channel_profile("vinted"), "Vinted", "Titel", [], photo_count=21)
        self.assertEqual(errors, ["Vinted: Vinted accepteert maximaal 20 foto's."])

    def test_bol_requires_ean_per_variant(self) -> None:
        _, _, variant, publication = self.make_publication("bol")
        validation = validate_publication_record(self.db, publication)
        self.assertTrue(any("EAN-code" in error for error in validation["errors"]))
        variant.ean = "8712345678906"
        self.db.commit()
        validation = validate_publication_record(self.db, publication)
        self.assertFalse(any("EAN-code" in error for error in validation["errors"]))

    def test_assisted_channel_cannot_be_published_through_api(self) -> None:
        _, _, _, publication = self.make_publication("vinted")
        with self.assertRaises(HTTPException) as blocked:
            publish_product_publication(publication.id, self.db)
        self.assertEqual(blocked.exception.status_code, 409)
        self.assertEqual(publication.publication_status, "klaar_voor_publicatie")

    def test_listing_package_and_mark_placed(self) -> None:
        _, _, _, publication = self.make_publication("marktplaats")

        package = listing_package(publication.id, self.db)
        self.assertEqual(package["title"], "Planterpot Hex M")
        self.assertEqual(package["tags"], ["pot", "plant"])
        self.assertEqual(package["price"], 12.95)
        self.assertEqual(package["profile"]["mode"], "hulpmodus")
        self.assertEqual(len(package["photos"]), 1)

        placed = mark_publication_placed(publication.id, MarkPlaced(external_url="https://www.marktplaats.nl/v/test"), self.db)
        self.assertEqual(placed["publication_status"], "gepubliceerd")
        self.assertTrue(placed["placed_manually"])
        self.assertEqual(placed["external_url"], "https://www.marktplaats.nl/v/test")

    def test_mark_placed_rejects_api_channels_and_bad_links(self) -> None:
        _, _, _, etsy_publication = self.make_publication("etsy")
        with self.assertRaises(HTTPException):
            mark_publication_placed(etsy_publication.id, MarkPlaced(), self.db)
        self.db.rollback()
        _, _, _, publication = self.make_publication("vinted")
        with self.assertRaises(HTTPException):
            mark_publication_placed(publication.id, MarkPlaced(external_url="javascript:alert(1)"), self.db)

    def test_photos_zip_contains_only_files_inside_uploads(self) -> None:
        _, product, _, publication = self.make_publication("vinted")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            media_dir = root / "product_media" / str(product.id)
            media_dir.mkdir(parents=True)
            (media_dir / "a.jpg").write_bytes(b"jpg")
            self.db.add(ProductMedia(product_id=product.id, file_path="/uploads/../../etc/passwd", media_type="image", sort_order=2))
            self.db.commit()
            with patch.object(channels, "UPLOAD_ROOT", root):
                body = listing_package_photos(publication.id, self.db).body
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            self.assertEqual(archive.namelist(), ["01.jpg"])

    def test_manual_order_is_created_and_processed(self) -> None:
        platform = self.make_platform("vinted")
        product, variant = self.make_product_variant("MANUAL-SKU")
        self.db.add(ProductInventory(product_id=product.id, product_variant_id=variant.id, quantity_on_hand=3, quantity_reserved=0))
        self.db.commit()

        result = create_manual_order(ManualOrder(platform_id=platform.id, external_order_id="V-123", items=[ManualOrderItem(product_variant_id=variant.id, quantity=2)]), FakeRequest(), self.db)

        self.assertTrue(result["processed"])
        order = self.db.get(Order, result["order"]["id"])
        self.assertEqual(order.internal_order_number, f"VINTED-{platform.id}-V-123")
        self.assertEqual(float(order.total_amount), 25.9)
        inventory = self.db.scalar(select(ProductInventory))
        self.assertEqual(inventory.quantity_reserved, 2)

        with self.assertRaises(HTTPException) as duplicate:
            create_manual_order(ManualOrder(platform_id=platform.id, external_order_id="V-123", items=[ManualOrderItem(product_variant_id=variant.id, quantity=1)]), FakeRequest(), self.db)
        self.assertEqual(duplicate.exception.status_code, 409)

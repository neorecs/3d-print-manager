import base64
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from sqlalchemy import func

from support import *

from core.config import Settings
from models import AIUsageLog
from services import ai_listing_studio
from services.ai_listing_studio import apply_channel_listing, edit_product_photo, enforce_rules, generate_channel_listings
from services.ai_usage_service import ai_usage_status, reserve_ai_request
from publishing.channel_profiles import channel_profile


def ai_settings(**overrides) -> Settings:
    values = {"ai_openai_enabled": True, "openai_api_key": "test", "ai_daily_request_limit": 5, "ai_daily_image_limit": 1}
    values.update(overrides)
    return Settings(**values)


def openai_json(payload: dict) -> dict:
    return {"output_text": json.dumps(payload), "usage": {"input_tokens": 10, "output_tokens": 20}}


class ListingStudioTests(BackendTestCase):
    def test_enforce_rules_trims_title_and_tags_for_etsy(self) -> None:
        listing = enforce_rules(channel_profile("etsy"), {
            "title": "Planterpot " + "zeshoekig modern design " * 10,
            "description": "Tekst",
            "tags": ["#plantenpot", "plantenpot", "een veel te lange tag voor etsy hier"] + [f"tag{i}" for i in range(20)],
        })
        self.assertLessEqual(len(listing["title"]), 140)
        self.assertFalse(listing["title"].endswith(" "))
        self.assertEqual(listing["tags"][0], "plantenpot")
        self.assertEqual(len(listing["tags"]), 13)
        self.assertTrue(all(len(tag) <= 20 for tag in listing["tags"]))

    def test_without_ai_example_texts_are_returned_without_calls(self) -> None:
        product, _ = self.make_product_variant("STUDIO-1")
        with patch.object(ai_listing_studio, "post_openai_response", side_effect=AssertionError("no AI call")):
            result = generate_channel_listings(self.db, product, ["etsy", "vinted"], Settings(ai_openai_enabled=False))
        self.assertEqual(result["source"], "voorbeeld")
        self.assertEqual([item["channel"] for item in result["listings"]], ["etsy", "vinted"])

    def test_rule_violations_get_one_repair_round(self) -> None:
        product, _ = self.make_product_variant("STUDIO-2")
        too_long = {"listings": [{"channel": "etsy", "title": "x" * 200, "description": "d", "tags": ["a"]}], "photo_notes": ["Voeg een maatfoto toe."]}
        fixed = {"listings": [{"channel": "etsy", "title": "Planterpot zeshoek", "description": "d", "tags": ["plantenpot"]}], "photo_notes": []}
        calls = []

        def fake_post(body, settings):
            calls.append(body)
            return openai_json(too_long if len(calls) == 1 else fixed)

        with patch.object(ai_listing_studio, "post_openai_response", side_effect=fake_post):
            result = generate_channel_listings(self.db, product, ["etsy"], ai_settings())
        self.assertEqual(len(calls), 2)
        self.assertTrue(result["repaired"])
        self.assertEqual(result["listings"][0]["title"], "Planterpot zeshoek")
        self.assertIn("Voeg een maatfoto toe.", result["notes"])
        repair_payload = json.loads(calls[1]["input"][1]["content"][0]["text"])
        self.assertIn("te_herstellen", repair_payload)

    def test_photos_are_sent_originals_first(self) -> None:
        product, _ = self.make_product_variant("STUDIO-3")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "product_media" / str(product.id)
            folder.mkdir(parents=True)
            (folder / "edit.png").write_bytes(b"edited")
            (folder / "real.jpg").write_bytes(b"original")
            self.db.add(ProductMedia(product_id=product.id, file_path=f"/uploads/product_media/{product.id}/edit.png", media_type="image", sort_order=0, ai_edited=True))
            self.db.add(ProductMedia(product_id=product.id, file_path=f"/uploads/product_media/{product.id}/real.jpg", media_type="image", sort_order=1))
            self.db.add(ProductMedia(product_id=product.id, file_path="/uploads/../../etc/passwd", media_type="image", sort_order=2))
            self.db.commit()
            with patch.object(ai_listing_studio, "UPLOAD_ROOT", root):
                inputs = ai_listing_studio.photo_inputs(self.db, product)
        self.assertEqual(len(inputs), 2)
        self.assertTrue(inputs[0]["image_url"].startswith("data:image/jpeg;base64,"))

    def test_apply_writes_publication_and_requires_one(self) -> None:
        product, _ = self.make_product_variant("STUDIO-4")
        platform = self.make_platform("etsy")
        with self.assertRaises(HTTPException):
            apply_channel_listing(self.db, product, "etsy", "Titel", "Tekst", ["a"])
        publication = ProductPlatformPublication(product_id=product.id, platform_id=platform.id, publication_status="concept")
        self.db.add(publication)
        self.db.commit()
        apply_channel_listing(self.db, product, "etsy", "Titel", "Tekst", ["plantenpot", "#cadeau"])
        self.db.refresh(publication)
        self.assertEqual(publication.platform_title, "Titel")
        self.assertEqual(publication.platform_tags, "plantenpot, cadeau")


class PhotoStudioTests(BackendTestCase):
    def test_edit_creates_new_marked_photo_and_keeps_original(self) -> None:
        product, _ = self.make_product_variant("PHOTO-1")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "product_media" / str(product.id)
            folder.mkdir(parents=True)
            (folder / "real.jpg").write_bytes(b"original")
            original = ProductMedia(product_id=product.id, file_path=f"/uploads/product_media/{product.id}/real.jpg", media_type="image", is_primary=True)
            self.db.add(original)
            self.db.commit()
            sent = {}

            def fake_edit(settings, image, filename, mime, prompt):
                sent.update(image=image, mime=mime, prompt=prompt)
                return {"data": [{"b64_json": base64.b64encode(b"new-png").decode()}]}

            with patch.object(ai_listing_studio, "UPLOAD_ROOT", root), patch.object(ai_listing_studio, "post_openai_image_edit", side_effect=fake_edit):
                created = edit_product_photo(self.db, product, original, "witte_achtergrond", None, ai_settings())
                stored = (root / created["file_path"].removeprefix("/uploads/")).read_bytes()

        self.assertEqual(stored, b"new-png")
        self.assertEqual(sent["image"], b"original")
        self.assertIn("exact hetzelfde", sent["prompt"])
        media = self.db.get(ProductMedia, created["id"])
        self.assertTrue(media.ai_edited)
        self.assertEqual(media.source_media_id, original.id)
        self.assertFalse(media.is_primary)
        self.assertTrue(self.db.get(ProductMedia, original.id).is_primary)

    def test_image_limit_is_separate_from_text_limit(self) -> None:
        reserve_ai_request(self.db, "image:edit:1", "img", 1)
        with self.assertRaises(HTTPException) as caught:
            reserve_ai_request(self.db, "image:edit:2", "img", 1)
        self.assertEqual(caught.exception.status_code, 429)
        reserve_ai_request(self.db, "product_draft", "text", 1)
        status = ai_usage_status(self.db, 1, 1)
        self.assertEqual(status["used_today"], 1)
        self.assertEqual(status["image_used_today"], 1)
        self.assertEqual(status["image_remaining_today"], 0)

    def test_edit_refused_when_ai_is_off(self) -> None:
        product, _ = self.make_product_variant("PHOTO-2")
        media = ProductMedia(product_id=product.id, file_path="/uploads/x.jpg", media_type="image")
        self.db.add(media)
        self.db.commit()
        with self.assertRaises(HTTPException) as caught:
            edit_product_photo(self.db, product, media, "witte_achtergrond", None, Settings(ai_openai_enabled=False))
        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(AIUsageLog)), 0)

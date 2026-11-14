import asyncio
import base64
import hashlib
import hmac
import secrets
import time
from unittest.mock import patch

from cryptography.fernet import Fernet

from support import *

from api.routes.webhooks import receive_webhook
from models import PlatformImportLog
from connectors.factory import store_platform_credentials
from services.webhook_service import (
    claim_requested_imports,
    has_requested_imports,
    verify_shopify_signature,
    verify_standard_webhook,
)
import worker


class FakeRequest:
    def __init__(self, body: bytes, headers: dict):
        self._body = body
        self.headers = {key.lower(): value for key, value in headers.items()}

    async def body(self) -> bytes:
        return self._body


def shopify_signature(secret: str, body: bytes) -> str:
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


def etsy_headers(secret: str, body: bytes, timestamp: int | None = None) -> dict:
    webhook_id = "msg_" + secrets.token_hex(6)
    sent_at = str(timestamp if timestamp is not None else int(time.time()))
    key = base64.b64decode(secret.removeprefix("whsec_"))
    signature = base64.b64encode(hmac.new(key, f"{webhook_id}.{sent_at}.".encode() + body, hashlib.sha256).digest()).decode()
    return {"webhook-id": webhook_id, "webhook-timestamp": sent_at, "webhook-signature": f"v1,bogus v1,{signature}"}


def new_etsy_secret() -> str:
    return "whsec_" + base64.b64encode(secrets.token_bytes(24)).decode()


class SignatureTests(unittest.TestCase):
    def test_shopify_signature(self) -> None:
        secret, body = secrets.token_hex(16), b'{"id": 1}'
        self.assertTrue(verify_shopify_signature(secret, body, shopify_signature(secret, body)))
        self.assertFalse(verify_shopify_signature(secret, body + b" ", shopify_signature(secret, body)))
        self.assertFalse(verify_shopify_signature(secret, body, None))

    def test_etsy_signature_accepts_any_matching_entry(self) -> None:
        secret, body = new_etsy_secret(), b'{"event_type": "order.paid"}'
        headers = etsy_headers(secret, body)
        self.assertTrue(verify_standard_webhook(secret, body, headers["webhook-id"], headers["webhook-timestamp"], headers["webhook-signature"]))
        self.assertFalse(verify_standard_webhook(secret, b"{}", headers["webhook-id"], headers["webhook-timestamp"], headers["webhook-signature"]))

    def test_etsy_signature_rejects_old_messages(self) -> None:
        secret, body = new_etsy_secret(), b"{}"
        headers = etsy_headers(secret, body, timestamp=int(time.time()) - 3600)
        self.assertFalse(verify_standard_webhook(secret, body, headers["webhook-id"], headers["webhook-timestamp"], headers["webhook-signature"]))


class WebhookRouteTests(BackendTestCase):
    def setUp(self) -> None:
        super().setUp()
        os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())

    def call(self, platform_type: str, platform_id: int, body: bytes, headers: dict) -> dict:
        return asyncio.run(receive_webhook(platform_type, platform_id, FakeRequest(body, headers), self.db))

    def test_valid_shopify_webhook_queues_one_import(self) -> None:
        platform = self.make_platform("shopify")
        secret = secrets.token_hex(16)
        store_platform_credentials(self.db, platform.id, {"webhook_secret": secret})
        self.db.commit()
        body = b'{"id": 820982911946154508}'
        headers = {"X-Shopify-Hmac-Sha256": shopify_signature(secret, body), "X-Shopify-Topic": "orders/create"}

        self.assertEqual(self.call("shopify", platform.id, body, headers), {"received": True, "queued": True})
        self.assertEqual(self.call("shopify", platform.id, body, headers), {"received": True, "queued": False})
        self.assertTrue(has_requested_imports(self.db))
        self.assertEqual(claim_requested_imports(self.db), [platform.id])
        self.db.commit()
        self.assertFalse(has_requested_imports(self.db))

    def test_valid_etsy_webhook_queues_import(self) -> None:
        platform = self.make_platform("etsy")
        secret = new_etsy_secret()
        store_platform_credentials(self.db, platform.id, {"webhook_secret": secret})
        self.db.commit()
        body = b'{"event_type": "order.paid", "shop_id": 1}'
        self.assertTrue(self.call("etsy", platform.id, body, etsy_headers(secret, body))["queued"])

    def test_bad_signature_is_rejected(self) -> None:
        platform = self.make_platform("shopify")
        store_platform_credentials(self.db, platform.id, {"webhook_secret": secrets.token_hex(16)})
        self.db.commit()
        with self.assertRaises(HTTPException) as caught:
            self.call("shopify", platform.id, b"{}", {"X-Shopify-Hmac-Sha256": "invalid"})
        self.assertEqual(caught.exception.status_code, 401)
        self.assertFalse(has_requested_imports(self.db))

    def test_channel_without_secret_or_wrong_type_is_unknown(self) -> None:
        platform = self.make_platform("shopify")
        for platform_type in ("shopify", "etsy", "bol"):
            with self.assertRaises(HTTPException) as caught:
                self.call(platform_type, platform.id, b"{}", {})
            self.assertEqual(caught.exception.status_code, 404)


class WorkerWakeUpTests(BackendTestCase):
    def test_worker_wakes_early_for_webhook_requests(self) -> None:
        platform = self.make_platform("shopify")
        self.db.add(PlatformImportLog(platform_id=platform.id, import_type="webhook", status="gevraagd"))
        self.db.commit()
        slept = []
        with patch.object(worker, "SessionLocal", self.Session):
            result = worker.wait_for_next_round(300, 15, sleep=slept.append)
        self.assertEqual(result, [platform.id])
        self.assertEqual(slept, [15])

    def test_worker_sleeps_full_interval_without_requests(self) -> None:
        slept = []
        with patch.object(worker, "SessionLocal", self.Session):
            self.assertIsNone(worker.wait_for_next_round(60, 15, sleep=slept.append))
        self.assertEqual(sum(slept), 60)

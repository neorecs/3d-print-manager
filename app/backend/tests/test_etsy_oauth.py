import io
import json
from unittest.mock import patch
from urllib.error import HTTPError

from cryptography.fernet import Fernet

from support import *

from api.routes.platforms import EtsyOAuthCallback, finish_etsy_oauth, start_etsy_oauth
from connectors.etsy import oauth
from connectors.factory import load_platform_credentials, store_platform_credentials
from core.config import get_settings


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def http_error(code: int, headers: dict | None = None) -> HTTPError:
    return HTTPError("https://openapi.etsy.com", code, "error", headers or {}, io.BytesIO(b"{}"))


class FakeRequestState:
    user_email = "admin@example.com"


class FakeRequest:
    state = FakeRequestState()


LIVE_CREDENTIALS = {"api_key": "key", "shared_secret": "secret", "access_token": "old-token", "refresh_token": "refresh-1", "shop_id": "1"}


class EtsyTokenTests(BackendTestCase):
    def setUp(self) -> None:
        os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())
        super().setUp()

    def test_needs_refresh_only_with_refresh_token_and_near_expiry(self) -> None:
        self.assertFalse(oauth.needs_refresh({"access_token": "x"}, now=1000))
        self.assertTrue(oauth.needs_refresh({"refresh_token": "r"}, now=1000))
        self.assertTrue(oauth.needs_refresh({"refresh_token": "r", "access_token_expires_at": "1200"}, now=1000))
        self.assertFalse(oauth.needs_refresh({"refresh_token": "r", "access_token_expires_at": "5000"}, now=1000))

    def test_token_values_store_expiry(self) -> None:
        values = oauth.token_values({"access_token": "a", "refresh_token": "r", "expires_in": 3600}, now=1000)
        self.assertEqual(values, {"access_token": "a", "refresh_token": "r", "access_token_expires_at": "4600"})

    def test_expired_token_is_refreshed_and_saved_before_request(self) -> None:
        connector = EtsyConnector({**LIVE_CREDENTIALS, "access_token_expires_at": "0"}, live_mode=True)
        saved = []
        connector.token_saver = saved.append
        headers_seen = []

        def fake_urlopen(request, timeout):
            headers_seen.append(request.get_header("Authorization"))
            return FakeResponse({"results": []})

        new_tokens = {"access_token": "new-token", "refresh_token": "refresh-2", "access_token_expires_at": "9999999999"}
        with patch.object(oauth, "refresh_tokens", return_value=new_tokens) as refresh, \
                patch("connectors.etsy.connector.urlopen", side_effect=fake_urlopen):
            connector._request_json("GET", "/shops/1/receipts")

        refresh.assert_called_once_with("key", "refresh-1")
        self.assertEqual(saved, [new_tokens])
        self.assertEqual(headers_seen, ["Bearer new-token"])

    def test_unauthorized_response_triggers_one_refresh_and_retry(self) -> None:
        connector = EtsyConnector({**LIVE_CREDENTIALS, "access_token_expires_at": "9999999999"}, live_mode=True)
        connector.token_saver = lambda values: None
        responses = [http_error(401), FakeResponse({"ok": True})]

        def fake_urlopen(request, timeout):
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        new_tokens = {"access_token": "new-token", "refresh_token": "refresh-2", "access_token_expires_at": "9999999999"}
        with patch.object(oauth, "refresh_tokens", return_value=new_tokens), \
                patch("connectors.etsy.connector.urlopen", side_effect=fake_urlopen):
            result = connector._request_json("GET", "/shops/1/receipts")

        self.assertEqual(result, {"ok": True})

    def test_rate_limit_is_retried_after_retry_after(self) -> None:
        connector = EtsyConnector({**LIVE_CREDENTIALS, "access_token_expires_at": "9999999999"}, live_mode=True)
        sleeps = []
        connector.sleep = sleeps.append
        responses = [http_error(429, {"Retry-After": "2"}), FakeResponse({"ok": True})]

        def fake_urlopen(request, timeout):
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        with patch("connectors.etsy.connector.urlopen", side_effect=fake_urlopen):
            result = connector._request_json("GET", "/shops/1/receipts")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(sleeps, [2.0])

    def test_env_access_token_does_not_override_oauth_tokens(self) -> None:
        platform = self.make_platform("etsy")
        store_platform_credentials(self.db, platform.id, {"access_token": "db-token", "refresh_token": "refresh-1"})
        self.db.commit()
        with patch.dict(os.environ, {"ETSY_ACCESS_TOKEN": "env-token"}):
            credentials = load_platform_credentials(self.db, platform)
        self.assertEqual(credentials["access_token"], "db-token")


class EtsyOAuthRouteTests(BackendTestCase):
    def setUp(self) -> None:
        os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())
        super().setUp()
        self.env = patch.dict(os.environ, {"ETSY_REDIRECT_URI": "http://nas.local:38502/api/platform-credentials/etsy/oauth/callback"})
        self.env.start()
        get_settings.cache_clear()
        self.platform = self.make_platform("etsy")
        store_platform_credentials(self.db, self.platform.id, {"api_key": "keystring"})
        self.db.commit()

    def tearDown(self) -> None:
        self.env.stop()
        get_settings.cache_clear()
        super().tearDown()

    def test_start_returns_etsy_url_and_stores_state(self) -> None:
        result = start_etsy_oauth(self.platform.id, FakeRequest(), self.db)

        credentials = load_platform_credentials(self.db, self.platform)
        self.assertIn("https://www.etsy.com/oauth/connect?", result["authorize_url"])
        self.assertIn("code_challenge_method=S256", result["authorize_url"])
        self.assertIn(f"state={credentials['oauth_state']}", result["authorize_url"])
        self.assertTrue(credentials["oauth_code_verifier"])

    def test_callback_stores_tokens_and_clears_temporary_state(self) -> None:
        start_etsy_oauth(self.platform.id, FakeRequest(), self.db)
        state = load_platform_credentials(self.db, self.platform)["oauth_state"]
        tokens = {"access_token": "a", "refresh_token": "r", "access_token_expires_at": "9999999999"}

        with patch.object(oauth, "exchange_code", return_value=tokens) as exchange:
            result = finish_etsy_oauth(EtsyOAuthCallback(code="code-1", state=state), FakeRequest(), self.db)

        self.assertEqual(result, {"status": "connected", "platform_id": self.platform.id})
        self.assertEqual(exchange.call_args.args[2], "code-1")
        credentials = load_platform_credentials(self.db, self.platform)
        self.assertEqual(credentials["access_token"], "a")
        self.assertEqual(credentials["refresh_token"], "r")
        self.assertNotIn("oauth_state", credentials)
        self.assertNotIn("oauth_code_verifier", credentials)

    def test_callback_with_unknown_state_is_rejected(self) -> None:
        start_etsy_oauth(self.platform.id, FakeRequest(), self.db)
        with self.assertRaises(HTTPException) as rejected:
            finish_etsy_oauth(EtsyOAuthCallback(code="code-1", state="verkeerd"), FakeRequest(), self.db)
        self.assertEqual(rejected.exception.status_code, 400)

    def test_expired_callback_is_rejected(self) -> None:
        start_etsy_oauth(self.platform.id, FakeRequest(), self.db)
        state = load_platform_credentials(self.db, self.platform)["oauth_state"]
        store_platform_credentials(self.db, self.platform.id, {"oauth_started_at": "1"})
        self.db.commit()
        with self.assertRaises(HTTPException) as rejected:
            finish_etsy_oauth(EtsyOAuthCallback(code="code-1", state=state), FakeRequest(), self.db)
        self.assertEqual(rejected.exception.status_code, 400)

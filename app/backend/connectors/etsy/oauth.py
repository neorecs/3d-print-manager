"""Etsy OAuth 2.0 with PKCE.

Etsy access tokens are valid for one hour; the refresh token (valid 90 days and
rotated on every refresh) is used to get a new one. Every refresh returns a new
refresh token that must be stored, otherwise the next refresh fails.
"""

import base64
import hashlib
import json
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ETSY_AUTHORIZE_URL = "https://www.etsy.com/oauth/connect"
ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
ETSY_SCOPES = ("listings_r", "listings_w", "transactions_r", "transactions_w", "shops_r")
REFRESH_MARGIN_SECONDS = 300


class EtsyOAuthError(Exception):
    pass


def new_pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


def authorize_url(api_key: str, redirect_uri: str, state: str, code_challenge: str) -> str:
    query = urlencode({
        "response_type": "code",
        "client_id": api_key,
        "redirect_uri": redirect_uri,
        "scope": " ".join(ETSY_SCOPES),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    return f"{ETSY_AUTHORIZE_URL}?{query}"


def _client_id(api_key: str) -> str:
    # Credentials may store "keystring:shared_secret"; OAuth only wants the keystring.
    return api_key.split(":", 1)[0]


def _post_token(payload: dict) -> dict:
    request = Request(
        ETSY_TOKEN_URL,
        data=urlencode(payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise EtsyOAuthError(f"Etsy weigerde de tokenaanvraag (HTTP {exc.code}): {body[:300]}") from exc
    except (URLError, OSError, json.JSONDecodeError) as exc:
        raise EtsyOAuthError(f"Etsy tokenaanvraag mislukt: {exc}") from exc
    if not data.get("access_token") or not data.get("refresh_token"):
        raise EtsyOAuthError("Etsy gaf geen volledige tokens terug.")
    return token_values(data)


def token_values(data: dict, now: float | None = None) -> dict[str, str]:
    """Credential values to store from an Etsy token response."""
    issued = now if now is not None else time.time()
    expires_in = int(data.get("expires_in") or 3600)
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "access_token_expires_at": str(int(issued + expires_in)),
    }


def exchange_code(api_key: str, redirect_uri: str, code: str, code_verifier: str) -> dict[str, str]:
    return _post_token({
        "grant_type": "authorization_code",
        "client_id": _client_id(api_key),
        "redirect_uri": redirect_uri,
        "code": code,
        "code_verifier": code_verifier,
    })


def refresh_tokens(api_key: str, refresh_token: str) -> dict[str, str]:
    return _post_token({
        "grant_type": "refresh_token",
        "client_id": _client_id(api_key),
        "refresh_token": refresh_token,
    })


def needs_refresh(credentials: dict[str, str], now: float | None = None) -> bool:
    if not credentials.get("refresh_token"):
        return False
    expires_at = credentials.get("access_token_expires_at")
    if not expires_at:
        return True
    try:
        return float(expires_at) - (now if now is not None else time.time()) < REFRESH_MARGIN_SECONDS
    except ValueError:
        return True

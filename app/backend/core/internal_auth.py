import base64
import hashlib
import hmac
import json
import time

from fastapi import Request
from fastapi.responses import JSONResponse

from core.config import get_settings
from database import SessionLocal
from models import User


PUBLIC_BACKEND_PATHS = {"/health", "/auth/login", "/auth/bootstrap-admin", "/auth/bootstrap-status"}
ADMIN_ONLY_PREFIXES = (
    "/auth/users",
    "/auth/audit-logs",
    "/platform-credentials",
    "/accounting/fiscal-settings",
    "/credentials/generate-key",
    "/seed",
)


async def enforce_backend_access(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    settings = get_settings()
    expected_internal_token = settings.backend_internal_token or ""
    supplied_internal_token = request.headers.get("x-backend-internal-token", "")
    if not expected_internal_token or not hmac.compare_digest(supplied_internal_token, expected_internal_token):
        return JSONResponse({"detail": "Backendtoegang geweigerd."}, status_code=401)

    if request.url.path in PUBLIC_BACKEND_PATHS or _is_signed_file_bridge(request.url.path):
        return await call_next(request)

    payload = _verify_session_token(request.headers.get("x-session-token"), settings.auth_secret or "")
    if not payload:
        return JSONResponse({"detail": "Geen geldige gebruikerssessie."}, status_code=401)

    with SessionLocal() as db:
        user = db.get(User, payload.get("userId"))
        if (
            not user
            or not user.is_active
            or user.email.lower() != str(payload.get("email", "")).lower()
            or user.session_version != payload.get("sessionVersion")
        ):
            return JSONResponse({"detail": "De gebruikerssessie is verlopen of ingetrokken."}, status_code=401)
        role = user.role
        must_change_password = user.must_change_password
        request.state.user_id = user.id
        request.state.user_email = user.email
        request.state.user_role = role

    if must_change_password and request.url.path not in {"/auth/change-password", "/auth/session/validate"}:
        return JSONResponse({"detail": "Wijzig eerst je tijdelijke wachtwoord."}, status_code=403)
    if role == "viewer" and request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        return JSONResponse({"detail": "Een viewer mag alleen gegevens bekijken."}, status_code=403)
    if role != "admin" and (
        request.url.path.startswith(ADMIN_ONLY_PREFIXES) or "/credentials" in request.url.path
    ):
        return JSONResponse({"detail": "Deze actie is alleen beschikbaar voor een beheerder."}, status_code=403)

    return await call_next(request)


def _verify_session_token(token: str | None, secret: str) -> dict | None:
    if not token or not secret or "." not in token:
        return None
    body, signature = token.split(".", 1)
    expected = _base64url(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_base64url_decode(body))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not payload.get("email") or int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _base64url_decode(value: str) -> str:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()


def _is_signed_file_bridge(path: str) -> bool:
    return path.startswith("/products/") and path.endswith("/print-file/prepared-download")

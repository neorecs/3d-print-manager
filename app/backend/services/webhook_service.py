"""Order webhooks from Etsy and Shopify.

A webhook only says "something changed in this shop". After checking the
signature we leave a request for the worker, which imports that channel within
seconds through the normal order import. The webhook never writes orders itself,
so a forged or replayed call can at most trigger an extra (harmless) import, and
the regular polling remains the safety net when a webhook is missed.
"""

import base64
import hashlib
import hmac
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Platform, PlatformImportLog

WEBHOOK_PLATFORM_TYPES = ("etsy", "shopify")
REQUESTED = "gevraagd"
CLAIMED = "opgepakt"
MAX_TIMESTAMP_SKEW_SECONDS = 300


def verify_shopify_signature(secret: str, body: bytes, signature: str | None) -> bool:
    """Shopify: X-Shopify-Hmac-Sha256 = base64(HMAC-SHA256(app client secret, raw body))."""
    if not secret or not signature:
        return False
    expected = base64.b64encode(hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()).decode("ascii")
    return hmac.compare_digest(expected, signature.strip())


def verify_standard_webhook(
    secret: str,
    body: bytes,
    webhook_id: str | None,
    timestamp: str | None,
    signature_header: str | None,
    now: float | None = None,
) -> bool:
    """Etsy follows the Standard Webhooks scheme: whsec_ secret, id.timestamp.body, v1,<base64> signatures."""
    if not secret or not webhook_id or not timestamp or not signature_header:
        return False
    try:
        sent_at = int(timestamp)
    except ValueError:
        return False
    if abs((now if now is not None else time.time()) - sent_at) > MAX_TIMESTAMP_SKEW_SECONDS:
        return False
    raw_secret = secret[len("whsec_"):] if secret.startswith("whsec_") else secret
    try:
        key = base64.b64decode(raw_secret)
    except (ValueError, TypeError):
        return False
    signed = f"{webhook_id}.{timestamp}.".encode("utf-8") + body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode("ascii")
    for entry in signature_header.split():
        _, _, value = entry.partition(",")
        if value and hmac.compare_digest(expected, value):
            return True
    return False


def request_import(db: Session, platform: Platform, source: str) -> bool:
    """Leave one pending import request per channel; returns False when one was already waiting."""
    pending = db.scalar(
        select(PlatformImportLog.id).where(
            PlatformImportLog.platform_id == platform.id,
            PlatformImportLog.import_type == "webhook",
            PlatformImportLog.status == REQUESTED,
        ).limit(1)
    )
    if pending is not None:
        return False
    db.add(PlatformImportLog(
        platform_id=platform.id,
        import_type="webhook",
        status=REQUESTED,
        started_at=datetime.now(timezone.utc),
        message=f"Webhook ontvangen: {source}"[:500],
    ))
    return True


def has_requested_imports(db: Session) -> bool:
    return db.scalar(
        select(PlatformImportLog.id).where(PlatformImportLog.import_type == "webhook", PlatformImportLog.status == REQUESTED).limit(1)
    ) is not None


def claim_requested_imports(db: Session) -> list[int]:
    """Mark pending webhook requests as picked up and return the channels to import (caller commits)."""
    logs = db.scalars(
        select(PlatformImportLog).where(PlatformImportLog.import_type == "webhook", PlatformImportLog.status == REQUESTED)
    ).all()
    platform_ids = []
    for log in logs:
        log.status = CLAIMED
        log.finished_at = datetime.now(timezone.utc)
        if log.platform_id not in platform_ids:
            platform_ids.append(log.platform_id)
    return platform_ids

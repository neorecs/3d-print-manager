from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from connectors.factory import load_platform_credentials
from database import get_db
from models import Platform
from services.webhook_service import WEBHOOK_PLATFORM_TYPES, request_import, verify_shopify_signature, verify_standard_webhook

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/{platform_type}/{platform_id}")
async def receive_webhook(platform_type: str, platform_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    platform_type = platform_type.lower()
    platform = db.get(Platform, platform_id)
    # Same answer for every unknown or unconfigured channel, so the endpoint reveals nothing.
    if platform_type not in WEBHOOK_PLATFORM_TYPES or platform is None or (platform.type or "").lower() != platform_type or not platform.active:
        raise HTTPException(status_code=404, detail="Onbekende webhook.")
    secret = load_platform_credentials(db, platform).get("webhook_secret", "")
    if not secret:
        raise HTTPException(status_code=404, detail="Onbekende webhook.")

    body = await request.body()
    headers = request.headers
    if platform_type == "shopify":
        valid = verify_shopify_signature(secret, body, headers.get("x-shopify-hmac-sha256"))
        source = headers.get("x-shopify-topic") or "shopify"
    else:
        valid = verify_standard_webhook(secret, body, headers.get("webhook-id"), headers.get("webhook-timestamp"), headers.get("webhook-signature"))
        source = "etsy"
    if not valid:
        raise HTTPException(status_code=401, detail="Ongeldige handtekening.")

    queued = request_import(db, platform, source)
    db.commit()
    return {"received": True, "queued": queued}

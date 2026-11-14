import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.credentials import decrypt_credential, encrypt_credential
from connectors.base import ConnectorResult, PlatformConnector
from connectors.etsy.connector import EtsyConnector
from connectors.shopify.connector import ShopifyConnector
from models import Platform, PlatformCredential


class AssistedConnector(PlatformConnector):
    """Channels in 'hulpmodus': the app prepares the listing, the seller places it by hand."""

    platform_type = "hulpmodus"

    def publish_product(self, payload: dict) -> ConnectorResult:
        return ConnectorResult(False, "Dit kanaal werkt in hulpmodus: open het plaatsingspakket, plaats de advertentie zelf en markeer hem daarna als geplaatst.")

    def sync_product(self, payload: dict) -> ConnectorResult:
        return ConnectorResult(False, "Dit kanaal werkt in hulpmodus: pas de advertentie zelf aan op het kanaal.")


CONNECTOR_BY_TYPE = {
    "etsy": EtsyConnector,
    "shopify": ShopifyConnector,
}


def connector_live_mode() -> bool:
    return os.getenv("CONNECTORS_LIVE_MODE", "false").lower() in {"1", "true", "yes", "on"}


def load_platform_credentials(db: Session, platform: Platform) -> dict[str, str]:
    credentials = {
        credential.key_name.lower(): decrypt_credential(credential.encrypted_value)
        for credential in db.scalars(
            select(PlatformCredential).where(PlatformCredential.platform_id == platform.id)
        ).all()
    }
    prefix = platform.type.upper()
    for key in [
        "API_KEY",
        "SHARED_SECRET",
        "ACCESS_TOKEN",
        "SHOP_ID",
        "SHOP_DOMAIN",
        "LOCATION_ID",
        "TAXONOMY_ID",
        "READINESS_STATE_ID",
        "VARIATION_PROPERTY_ID",
    ]:
        value = os.getenv(f"{prefix}_{key}")
        if key == "ACCESS_TOKEN" and credentials.get("refresh_token"):
            # Tokens from the OAuth flow refresh themselves; a static env token would override them.
            continue
        if value:
            credentials[key.lower()] = value
    return credentials


def store_platform_credentials(db: Session, platform_id: int, values: dict[str, str]) -> None:
    """Create or update encrypted credentials for a platform (caller commits)."""
    for key_name, value in values.items():
        key_name = key_name.strip().lower()
        existing = db.scalar(
            select(PlatformCredential).where(PlatformCredential.platform_id == platform_id, PlatformCredential.key_name == key_name)
        )
        if value in (None, ""):
            if existing:
                db.delete(existing)
            continue
        if existing:
            existing.encrypted_value = encrypt_credential(value)
        else:
            db.add(PlatformCredential(platform_id=platform_id, key_name=key_name, encrypted_value=encrypt_credential(value)))


def _token_saver(db: Session, platform_id: int):
    """Persist refreshed tokens in their own transaction, so a running import is never committed halfway."""
    def save(values: dict[str, str]) -> None:
        with Session(bind=db.get_bind()) as token_db:
            store_platform_credentials(token_db, platform_id, values)
            token_db.commit()
    return save


def get_platform_connector(db: Session, platform: Platform) -> PlatformConnector:
    from publishing.channel_profiles import is_assisted

    platform_type = (platform.type or "").lower()
    default_class = AssistedConnector if is_assisted(platform_type) else PlatformConnector
    connector_class = CONNECTOR_BY_TYPE.get(platform_type, default_class)
    connector = connector_class(load_platform_credentials(db, platform), live_mode=connector_live_mode())
    if hasattr(connector_class, "token_saver"):
        connector.token_saver = _token_saver(db, platform.id)
    return connector

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.credentials import decrypt_credential
from connectors.base import PlatformConnector
from connectors.etsy.connector import EtsyConnector
from connectors.shopify.connector import ShopifyConnector
from models import Platform, PlatformCredential


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
    for key in ["API_KEY", "ACCESS_TOKEN", "SHOP_ID", "SHOP_DOMAIN", "LOCATION_ID", "TAXONOMY_ID"]:
        value = os.getenv(f"{prefix}_{key}")
        if value:
            credentials[key.lower()] = value
    return credentials


def get_platform_connector(db: Session, platform: Platform) -> PlatformConnector:
    connector_class = CONNECTOR_BY_TYPE.get((platform.type or "").lower(), PlatformConnector)
    return connector_class(load_platform_credentials(db, platform), live_mode=connector_live_mode())

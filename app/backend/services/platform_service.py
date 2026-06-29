from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.utils import to_dict
from connectors.factory import get_platform_connector
from core.credentials import is_encrypted_credential
from models import Platform, PlatformCredential, ProductInventory, ProductVariantPlatformLink


def public_credential_dict(credential: PlatformCredential) -> dict:
    data = to_dict(credential)
    data.pop("encrypted_value", None)
    data["has_value"] = bool(credential.encrypted_value)
    data["encrypted"] = is_encrypted_credential(credential.encrypted_value)
    return data


def normalize_language_list(value: str | None) -> str | None:
    languages = []
    for language in (value or "").split(","):
        cleaned = language.strip().lower()
        if cleaned and cleaned not in languages:
            languages.append(cleaned)
    return ", ".join(languages) if languages else None


def connector_status_payload(db: Session, platform: Platform) -> dict:
    connector = get_platform_connector(db, platform)
    status = connector.status()
    return {
        "platform_id": platform.id,
        "platform": platform.name,
        "platform_type": status.platform_type,
        "mode": status.mode,
        "required_credentials": status.required_credentials,
        "configured_credentials": status.configured_credentials,
        "missing_credentials": status.missing_credentials,
        "ready_for_live": status.ready_for_live,
    }


def sync_platform_inventory_payload(db: Session, platform: Platform) -> dict:
    if (platform.type or "").lower() != "shopify":
        raise HTTPException(status_code=400, detail="Voorraad-sync is nu alleen voor Shopify beschikbaar")

    connector = get_platform_connector(db, platform)
    links = {
        link.product_variant_id: link
        for link in db.scalars(
            select(ProductVariantPlatformLink).where(ProductVariantPlatformLink.platform_id == platform.id)
        ).all()
    }
    prepared = []
    missing_variant_ids = []
    for inventory in db.scalars(select(ProductInventory).order_by(ProductInventory.id)).all():
        link = links.get(inventory.product_variant_id)
        if not link or not link.external_inventory_id:
            missing_variant_ids.append(inventory.product_variant_id)
            continue
        prepared.append(
            {
                "product_inventory_id": inventory.id,
                "product_variant_id": inventory.product_variant_id,
                "sku": link.external_sku,
                "external_inventory_id": link.external_inventory_id,
                "quantity": inventory.free_stock,
            }
        )

    result = connector.sync_inventory(prepared)
    result["prepared"] = len(prepared)
    result["missing_inventory_links"] = sorted(set(missing_variant_ids))
    result["mode"] = connector.status().mode
    return result

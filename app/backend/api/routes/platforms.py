from fastapi import APIRouter
from api.routes_shared import *

router = APIRouter()

@router.get("/platforms")
def list_platforms(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(Platform).order_by(Platform.id)).all())


@router.post("/platforms")
def create_platform(payload: PlatformCreate, db: Session = Depends(get_db)):
    item = Platform(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.put("/platforms/{item_id}")
def update_platform(item_id: int, payload: PlatformCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, Platform, item_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/sales-markets")
def list_sales_markets(db: Session = Depends(get_db)):
    rows = db.scalars(select(SalesMarket).order_by(SalesMarket.country_code)).all()
    return list_rows(rows)


@router.post("/sales-markets")
def create_sales_market(payload: SalesMarketCreate, db: Session = Depends(get_db)):
    country_code = payload.country_code.strip().upper()
    if len(country_code) != 2:
        raise HTTPException(status_code=400, detail="Landcode moet uit 2 letters bestaan, bijvoorbeeld NL.")
    existing = db.scalar(select(SalesMarket).where(SalesMarket.country_code == country_code))
    if existing:
        raise HTTPException(status_code=400, detail=f"Doelland {country_code} bestaat al.")
    data = payload.model_dump()
    data["country_code"] = country_code
    data["primary_language"] = data["primary_language"].strip().lower()
    data["additional_languages"] = normalize_language_list(data.get("additional_languages"))
    data["currency"] = data["currency"].strip().upper() or "EUR"
    item = SalesMarket(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.put("/sales-markets/{item_id}")
def update_sales_market(item_id: int, payload: SalesMarketCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, SalesMarket, item_id)
    country_code = payload.country_code.strip().upper()
    if len(country_code) != 2:
        raise HTTPException(status_code=400, detail="Landcode moet uit 2 letters bestaan, bijvoorbeeld NL.")
    duplicate = db.scalar(select(SalesMarket).where(SalesMarket.country_code == country_code, SalesMarket.id != item_id))
    if duplicate:
        raise HTTPException(status_code=400, detail=f"Doelland {country_code} bestaat al.")
    data = payload.model_dump()
    data["country_code"] = country_code
    data["primary_language"] = data["primary_language"].strip().lower()
    data["additional_languages"] = normalize_language_list(data.get("additional_languages"))
    data["currency"] = data["currency"].strip().upper() or "EUR"
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return to_dict(item)


def normalize_language_list(value: str | None) -> str | None:
    languages = []
    for language in (value or "").split(","):
        cleaned = language.strip().lower()
        if cleaned and cleaned not in languages:
            languages.append(cleaned)
    return ", ".join(languages) if languages else None


@router.get("/platforms/{platform_id}/credentials")
def list_platform_credentials(platform_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Platform, platform_id)
    credentials = db.scalars(
        select(PlatformCredential).where(PlatformCredential.platform_id == platform_id).order_by(PlatformCredential.key_name)
    ).all()
    return [public_credential_dict(credential) for credential in credentials]


@router.post("/platforms/{platform_id}/credentials")
def create_platform_credential(
    platform_id: int, payload: PlatformCredentialCreate, db: Session = Depends(get_db)
):
    get_or_404(db, Platform, platform_id)
    key_name = payload.key_name.strip().lower()
    if not key_name:
        raise HTTPException(status_code=400, detail="Credential key_name is verplicht")
    existing = db.scalar(
        select(PlatformCredential).where(
            PlatformCredential.platform_id == platform_id,
            PlatformCredential.key_name == key_name,
        )
    )
    if existing:
        existing.encrypted_value = encrypt_credential(payload.encrypted_value)
        db.commit()
        db.refresh(existing)
        return public_credential_dict(existing)
    item = PlatformCredential(platform_id=platform_id, key_name=key_name, encrypted_value=encrypt_credential(payload.encrypted_value))
    db.add(item)
    db.commit()
    db.refresh(item)
    return public_credential_dict(item)


@router.delete("/platform-credentials/{item_id}")
def delete_platform_credential(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, PlatformCredential, item_id)
    db.delete(item)
    db.commit()
    return {"status": "deleted"}


@router.get("/platforms/{platform_id}/connector-status")
def platform_connector_status(platform_id: int, db: Session = Depends(get_db)):
    platform = get_or_404(db, Platform, platform_id)
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


@router.post("/platforms/{platform_id}/sync-inventory")
def sync_platform_inventory(platform_id: int, db: Session = Depends(get_db)):
    platform = get_or_404(db, Platform, platform_id)
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



"""Channel profiles, the listing package for 'hulpmodus' and manual orders."""

import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.utils import to_dict
from database import get_db
from domain.statuses import ORDER_NEW, PUBLICATION_PUBLISHED
from models import Order, OrderItem, Platform, Product, ProductPlatformPublication, ProductVariant
from publishing.channel_profiles import PROFILES, channel_profile, is_assisted, profile_dict
from publishing.service import get_publication_media_for_payload, split_platform_tags, validate_publication_record
from services.order_processing import process_order

router = APIRouter()
UPLOAD_ROOT = Path("uploads")


class MarkPlaced(BaseModel):
    external_url: str | None = Field(default=None, max_length=500)
    external_listing_id: str | None = Field(default=None, max_length=255)


class ManualOrderItem(BaseModel):
    product_variant_id: int
    quantity: int = Field(gt=0, le=1000)
    unit_price: float | None = Field(default=None, ge=0)


class ManualOrder(BaseModel):
    platform_id: int
    external_order_id: str | None = Field(default=None, max_length=255)
    customer_name: str | None = Field(default=None, max_length=255)
    total_amount: float | None = Field(default=None, ge=0)
    items: list[ManualOrderItem] = Field(min_length=1, max_length=50)
    process: bool = True


def _publication(db: Session, publication_id: int) -> tuple[ProductPlatformPublication, Platform, Product]:
    publication = db.get(ProductPlatformPublication, publication_id)
    if not publication:
        raise HTTPException(status_code=404, detail="Publicatie niet gevonden")
    return publication, db.get(Platform, publication.platform_id), db.get(Product, publication.product_id)


@router.get("/channel-profiles")
def list_channel_profiles() -> list[dict]:
    return [profile_dict(profile) for profile in PROFILES.values()]


@router.get("/product-publications/{publication_id}/listing-package")
def listing_package(publication_id: int, db: Session = Depends(get_db)) -> dict:
    """Everything needed to place this listing by hand, field by field."""
    publication, platform, product = _publication(db, publication_id)
    variants = db.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id, ProductVariant.active.is_(True)).order_by(ProductVariant.id)).all()
    prices = [variant.default_sale_price for variant in variants if variant.default_sale_price is not None]
    price = publication.platform_price_override if publication.platform_price_override is not None else (min(prices) if prices else None)
    media = get_publication_media_for_payload(db, publication)
    profile = channel_profile(platform.type)
    return {
        "publication_id": publication.id,
        "platform": {"id": platform.id, "name": platform.name, "type": platform.type},
        "profile": profile_dict(profile),
        "title": publication.platform_title or product.internal_title or product.name,
        "description": publication.platform_description or product.sales_description or product.long_description or product.short_description or "",
        "tags": split_platform_tags(publication.platform_tags),
        "category": publication.platform_category,
        "price": float(price) if price is not None else None,
        "currency": "EUR",
        "variants": [{"sku": variant.sku, "name": variant.variant_name, "color": variant.color, "material": variant.material,
                      "price": float(variant.default_sale_price) if variant.default_sale_price is not None else None} for variant in variants],
        "photos": [{"id": item.id, "url": item.file_path, "alt_text": item.alt_text, "ai_edited": bool(item.ai_edited)} for item in media[: profile.photos_max or None]],
        "status": publication.publication_status,
        "placed_manually": bool(publication.placed_manually),
        "external_url": publication.external_url,
        "validation": validate_publication_record(db, publication),
    }


@router.get("/product-publications/{publication_id}/listing-package/photos.zip")
def listing_package_photos(publication_id: int, db: Session = Depends(get_db)) -> Response:
    publication, platform, product = _publication(db, publication_id)
    media = get_publication_media_for_payload(db, publication)
    profile = channel_profile(platform.type)
    root = UPLOAD_ROOT.resolve()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
        for index, item in enumerate(media[: profile.photos_max or None], start=1):
            relative = (item.file_path or "").removeprefix("/uploads/")
            target = (root / relative).resolve()
            if root not in target.parents or not target.is_file():
                continue
            archive.write(target, f"{index:02d}{target.suffix.lower()}")
    filename = f"foto-s-{platform.type or 'kanaal'}-{product.id}.zip"
    return Response(buffer.getvalue(), media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/product-publications/{publication_id}/mark-placed")
def mark_publication_placed(publication_id: int, payload: MarkPlaced, db: Session = Depends(get_db)) -> dict:
    publication, platform, _ = _publication(db, publication_id)
    if not is_assisted(platform.type):
        raise HTTPException(status_code=409, detail="Dit kanaal publiceert via de koppeling; handmatig markeren is niet nodig.")
    if payload.external_url and not payload.external_url.startswith(("https://", "http://")):
        raise HTTPException(status_code=400, detail="Gebruik een volledige link die met https:// begint.")
    publication.publication_status = PUBLICATION_PUBLISHED
    publication.placed_manually = True
    publication.external_url = payload.external_url or publication.external_url
    publication.external_listing_id = payload.external_listing_id or publication.external_listing_id
    publication.last_synced_at = datetime.now(timezone.utc).isoformat()
    publication.last_error = None
    db.commit()
    return to_dict(publication)


@router.post("/orders/manual")
def create_manual_order(payload: ManualOrder, request: Request, db: Session = Depends(get_db)) -> dict:
    """Record an order from a channel without order import (hulpmodus), then process it like any other order."""
    platform = db.get(Platform, payload.platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail="Verkoopkanaal niet gevonden")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    external_id = (payload.external_order_id or "").strip() or f"handmatig-{stamp}"
    order = Order(
        internal_order_number=f"{(platform.type or 'kanaal').upper()[:12]}-{platform.id}-{external_id[:60]}",
        platform_id=platform.id,
        external_order_id=external_id,
        customer_name=payload.customer_name,
        order_date=datetime.now(timezone.utc),
        currency="EUR",
        status=ORDER_NEW,
        payment_status="betaald",
    )
    computed_total = 0.0
    db.add(order)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Deze order bestaat al voor dit kanaal.") from exc
    for line in payload.items:
        variant = db.get(ProductVariant, line.product_variant_id)
        if not variant:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Variant {line.product_variant_id} niet gevonden")
        unit_price = line.unit_price if line.unit_price is not None else (float(variant.default_sale_price) if variant.default_sale_price is not None else None)
        computed_total += (unit_price or 0) * line.quantity
        db.add(OrderItem(order_id=order.id, product_id=variant.product_id, product_variant_id=variant.id, sku=variant.sku,
                         quantity_ordered=line.quantity, unit_sale_price=unit_price))
    order.total_amount = payload.total_amount if payload.total_amount is not None else round(computed_total, 2)
    db.commit()
    result = {"order": to_dict(order), "processed": False}
    if payload.process:
        try:
            processed = process_order(db, order.id)
            result.update({"order": processed["order"], "processed": True, "message": processed["message"]})
        except HTTPException as exc:
            result["message"] = f"Order opgeslagen; verwerken lukte niet: {exc.detail}"
    return result

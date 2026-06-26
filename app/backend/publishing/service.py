import re
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.utils import to_dict
from connectors.factory import get_platform_connector
from models import Platform, Product, ProductMedia, ProductPlatformPublication, ProductPublicationMedia, ProductVariant


def get_required(db: Session, model: type, item_id: int):
    item = db.get(model, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return item


def split_platform_tags(tags: str | None) -> list[str]:
    if not tags:
        return []
    return [tag.strip() for tag in re.split(r"[,;\n]", tags) if tag.strip()]


def mark_product_publications_sync_needed(db: Session, product_id: int) -> None:
    query = select(ProductPlatformPublication).where(
        ProductPlatformPublication.product_id == product_id,
        ProductPlatformPublication.publication_status.in_(["gepubliceerd", "klaar_voor_publicatie"]),
    )
    for publication in db.scalars(query).all():
        publication.publication_status = "synchronisatie_nodig"


def publish_publication(db: Session, publication: ProductPlatformPublication) -> dict:
    validation = validate_publication_record(db, publication)
    if not validation["ready"]:
        publication.publication_status = "fout"
        publication.last_error = "; ".join(validation["errors"])
        db.commit()
        raise HTTPException(status_code=400, detail=validation)

    platform = get_required(db, Platform, publication.platform_id)
    connector = get_platform_connector(db, platform)
    result = connector.publish_product(build_publication_payload(db, publication))
    apply_connector_result(db, publication, result)
    return to_dict(publication)


def sync_publication(db: Session, publication: ProductPlatformPublication) -> dict:
    validation = validate_publication_record(db, publication)
    if not validation["ready"]:
        publication.publication_status = "fout"
        publication.last_error = "; ".join(validation["errors"])
        db.commit()
        raise HTTPException(status_code=400, detail=validation)

    platform = get_required(db, Platform, publication.platform_id)
    connector = get_platform_connector(db, platform)
    result = connector.sync_product(build_publication_payload(db, publication))
    apply_connector_result(db, publication, result)
    return to_dict(publication)


def apply_connector_result(db: Session, publication: ProductPlatformPublication, result) -> None:
    if not result.success:
        publication.publication_status = "fout"
        publication.last_error = result.message
        db.commit()
        raise HTTPException(status_code=400, detail=result.message)

    publication.publication_status = "gepubliceerd"
    publication.last_error = None
    publication.external_product_id = result.external_product_id or publication.external_product_id
    publication.external_listing_id = result.external_listing_id or publication.external_listing_id
    publication.last_synced_at = datetime.now(timezone.utc).isoformat()
    db.commit()


def build_publication_payload(db: Session, publication: ProductPlatformPublication) -> dict:
    product = get_required(db, Product, publication.product_id)
    media = get_publication_media_for_payload(db, publication)
    variants = db.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id)).all()
    return {
        "publication_id": publication.id,
        "product_id": product.id,
        "title": publication.platform_title or product.internal_title or product.name,
        "description": publication.platform_description
        or product.sales_description
        or product.long_description
        or product.short_description,
        "category": publication.platform_category or product.internal_category,
        "tags": split_platform_tags(publication.platform_tags),
        "price": publication.platform_price_override,
        "shipping_profile_id": publication.platform_shipping_profile_id,
        "media": [to_dict(item) for item in media],
        "variants": [to_dict(item) for item in variants],
    }


def get_publication_media_for_payload(db: Session, publication: ProductPlatformPublication) -> list[ProductMedia]:
    selected = db.scalars(
        select(ProductPublicationMedia)
        .where(
            ProductPublicationMedia.product_publication_id == publication.id,
            ProductPublicationMedia.active.is_(True),
        )
        .order_by(ProductPublicationMedia.sort_order)
    ).all()
    if selected:
        media_ids = [item.product_media_id for item in selected]
        media_by_id = {
            item.id: item
            for item in db.scalars(
                select(ProductMedia).where(
                    ProductMedia.product_id == publication.product_id,
                    ProductMedia.id.in_(media_ids),
                )
            ).all()
        }
        return [media_by_id[media_id] for media_id in media_ids if media_id in media_by_id]

    return db.scalars(
        select(ProductMedia).where(ProductMedia.product_id == publication.product_id).order_by(ProductMedia.sort_order)
    ).all()


def validate_publication_record(db: Session, publication: ProductPlatformPublication) -> dict:
    product = get_required(db, Product, publication.product_id)
    platform = get_required(db, Platform, publication.platform_id)
    media = get_publication_media_for_payload(db, publication)
    variants = db.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id)).all()

    errors = []
    warnings = []

    if not product.internal_title and not product.name:
        errors.append("Producttitel ontbreekt.")
    if not product.short_description and not product.long_description and not product.sales_description:
        errors.append("Productomschrijving ontbreekt.")
    if not media:
        errors.append("Minimaal een productfoto is verplicht.")
    if not variants:
        errors.append("Minimaal een productvariant is verplicht.")

    for variant in variants:
        if not variant.sku:
            errors.append(f"Variant {variant.id} mist een SKU.")
        if variant.default_sale_price is None:
            errors.append(f"Variant {variant.sku or variant.id} mist een verkoopprijs.")
        if not variant.material:
            errors.append(f"Variant {variant.sku or variant.id} mist materiaal.")
        if not variant.color:
            errors.append(f"Variant {variant.sku or variant.id} mist kleur.")
        if not variant.print_file_path and not variant.estimated_print_time_minutes:
            warnings.append(f"Variant {variant.sku or variant.id} mist printbestand of printtijd.")

    if not publication.platform_title:
        errors.append(f"{platform.name}: platformtitel ontbreekt.")
    if not publication.platform_description:
        errors.append(f"{platform.name}: platformomschrijving ontbreekt.")
    if not publication.platform_category:
        errors.append(f"{platform.name}: platformcategorie ontbreekt.")
    if not publication.platform_tags:
        warnings.append(f"{platform.name}: platformtags ontbreken.")
    if publication.platform_price_override is None and all(v.default_sale_price is None for v in variants):
        errors.append(f"{platform.name}: platformprijs of variantprijs ontbreekt.")

    tags = split_platform_tags(publication.platform_tags)
    platform_type = (platform.type or platform.name or "").lower()
    if platform_type == "etsy":
        if publication.platform_title and len(publication.platform_title) > 140:
            errors.append(f"{platform.name}: Etsy-titel mag maximaal 140 tekens zijn.")
        if len(tags) > 13:
            errors.append(f"{platform.name}: Etsy ondersteunt maximaal 13 tags.")
        long_tags = [tag for tag in tags if len(tag) > 20]
        if long_tags:
            errors.append(f"{platform.name}: Etsy-tags mogen maximaal 20 tekens zijn: {', '.join(long_tags)}.")
        if not publication.platform_shipping_profile_id:
            warnings.append(f"{platform.name}: Etsy verzendprofiel ontbreekt.")
    elif platform_type == "shopify":
        if not product.product_type:
            warnings.append(f"{platform.name}: Shopify producttype ontbreekt.")
        if not product.seo_title or not product.seo_description:
            warnings.append(f"{platform.name}: SEO-titel of SEO-omschrijving ontbreekt.")

    return {
        "publication_id": publication.id,
        "product_id": product.id,
        "platform_id": platform.id,
        "platform": platform.name,
        "ready": not errors,
        "errors": errors,
        "warnings": warnings,
    }

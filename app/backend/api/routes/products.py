from fastapi import APIRouter
from api.routes_shared import *
from services.product_service import generate_product_translations_for_product
from services.upload_service import delete_uploaded_media_file

router = APIRouter()

@router.get("/products")
def list_products(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(Product).order_by(Product.id)).all())


@router.post("/products")
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    item = Product(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/products/{item_id}")
def get_product(item_id: int, db: Session = Depends(get_db)):
    return to_dict(get_or_404(db, Product, item_id))


@router.put("/products/{item_id}")
def update_product(item_id: int, payload: ProductCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, Product, item_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    mark_product_publications_sync_needed(db, item.id)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/product-variants")
def list_product_variants(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(ProductVariant).order_by(ProductVariant.id)).all())


@router.post("/product-variants")
def create_product_variant(payload: ProductVariantCreate, db: Session = Depends(get_db)):
    item = ProductVariant(**payload.model_dump())
    db.add(item)
    mark_product_publications_sync_needed(db, item.product_id)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.put("/product-variants/{item_id}")
def update_product_variant(item_id: int, payload: ProductVariantCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductVariant, item_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    mark_product_publications_sync_needed(db, item.product_id)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/products/{product_id}/media")
def list_product_media(product_id: int, db: Session = Depends(get_db)):
    query = select(ProductMedia).where(ProductMedia.product_id == product_id).order_by(ProductMedia.sort_order)
    return list_rows(db.scalars(query).all())


@router.post("/products/{product_id}/media")
def create_product_media(product_id: int, payload: ProductMediaCreate, db: Session = Depends(get_db)):
    get_or_404(db, Product, product_id)
    if payload.is_primary:
        clear_primary_product_media(db, product_id)
    item = ProductMedia(product_id=product_id, **payload.model_dump())
    db.add(item)
    mark_product_publications_sync_needed(db, product_id)
    db.commit()
    db.refresh(item)
    return to_dict(item)



@router.put("/product-media/{item_id}")
def update_product_media(item_id: int, payload: ProductMediaCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductMedia, item_id)
    if payload.is_primary:
        clear_primary_product_media(db, item.product_id, exclude_media_id=item.id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    mark_product_publications_sync_needed(db, item.product_id)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.delete("/product-media/{item_id}")
def delete_product_media(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductMedia, item_id)
    product_id = item.product_id
    delete_uploaded_media_file(item.file_path)
    db.delete(item)
    mark_product_publications_sync_needed(db, product_id)
    db.commit()
    return {"status": "deleted"}


def clear_primary_product_media(db: Session, product_id: int, exclude_media_id: int | None = None) -> None:
    query = select(ProductMedia).where(ProductMedia.product_id == product_id, ProductMedia.is_primary.is_(True))
    for item in db.scalars(query).all():
        if exclude_media_id is None or item.id != exclude_media_id:
            item.is_primary = False


@router.get("/products/{product_id}/tags")
def list_product_tags(product_id: int, db: Session = Depends(get_db)):
    query = select(ProductTag).where(ProductTag.product_id == product_id).order_by(ProductTag.tag)
    return list_rows(db.scalars(query).all())


@router.post("/products/{product_id}/tags")
def create_product_tag(product_id: int, payload: ProductTagCreate, db: Session = Depends(get_db)):
    item = ProductTag(product_id=product_id, tag=payload.tag.strip())
    if not item.tag:
        raise HTTPException(status_code=400, detail="Tag is verplicht")
    db.add(item)
    mark_product_publications_sync_needed(db, product_id)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.delete("/product-tags/{item_id}")
def delete_product_tag(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductTag, item_id)
    product_id = item.product_id
    db.delete(item)
    mark_product_publications_sync_needed(db, product_id)
    db.commit()
    return {"status": "deleted"}


@router.get("/products/{product_id}/translations")
def list_product_translations(product_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Product, product_id)
    rows = db.scalars(select(ProductTranslation).where(ProductTranslation.product_id == product_id).order_by(ProductTranslation.language_code)).all()
    return list_rows(rows)


@router.post("/products/{product_id}/translations")
def save_product_translation(product_id: int, payload: ProductTranslationCreate, db: Session = Depends(get_db)):
    get_or_404(db, Product, product_id)
    language_code = payload.language_code.strip().lower()
    if not language_code:
        raise HTTPException(status_code=400, detail="language_code is verplicht")
    item = db.scalar(select(ProductTranslation).where(ProductTranslation.product_id == product_id, ProductTranslation.language_code == language_code))
    data = payload.model_dump()
    data["language_code"] = language_code
    if item:
        for key, value in data.items():
            setattr(item, key, value)
    else:
        item = ProductTranslation(product_id=product_id, **data)
        db.add(item)
    mark_product_publications_sync_needed(db, product_id)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.post("/products/{product_id}/translations/generate")
def generate_product_translations(product_id: int, payload: ProductTranslationGenerate | None = None, db: Session = Depends(get_db)):
    payload = payload or ProductTranslationGenerate()
    product = get_or_404(db, Product, product_id)
    return generate_product_translations_for_product(db, product, payload)


@router.get("/products/{product_id}/publications")
def list_product_publications(product_id: int, db: Session = Depends(get_db)):
    query = select(ProductPlatformPublication).where(ProductPlatformPublication.product_id == product_id)
    return list_rows(db.scalars(query).all())


@router.post("/products/{product_id}/publications")
def create_product_publication(
    product_id: int, payload: ProductPlatformPublicationCreate, db: Session = Depends(get_db)
):
    item = ProductPlatformPublication(product_id=product_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.put("/product-publications/{item_id}")
def update_product_publication(
    item_id: int, payload: ProductPlatformPublicationCreate, db: Session = Depends(get_db)
):
    item = get_or_404(db, ProductPlatformPublication, item_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.get("/product-publications/{item_id}/media")
def list_publication_media(item_id: int, db: Session = Depends(get_db)):
    publication = get_or_404(db, ProductPlatformPublication, item_id)
    product_media = db.scalars(
        select(ProductMedia).where(ProductMedia.product_id == publication.product_id).order_by(ProductMedia.sort_order)
    ).all()
    links = {
        link.product_media_id: link
        for link in db.scalars(
            select(ProductPublicationMedia).where(ProductPublicationMedia.product_publication_id == publication.id)
        ).all()
    }
    rows = []
    for media in product_media:
        link = links.get(media.id)
        data = to_dict(media)
        data["selected"] = bool(link and link.active)
        data["publication_media_id"] = link.id if link else None
        data["publication_sort_order"] = link.sort_order if link else media.sort_order
        rows.append(data)
    return rows


@router.put("/product-publications/{item_id}/media")
def update_publication_media(
    item_id: int, payload: ProductPublicationMediaBulkUpdate, db: Session = Depends(get_db)
):
    publication = get_or_404(db, ProductPlatformPublication, item_id)
    allowed_media_ids = {
        item.id for item in db.scalars(select(ProductMedia).where(ProductMedia.product_id == publication.product_id)).all()
    }
    for payload_item in payload.items:
        if payload_item.product_media_id not in allowed_media_ids:
            raise HTTPException(status_code=400, detail="Media-item hoort niet bij dit product")

    existing = db.scalars(
        select(ProductPublicationMedia).where(ProductPublicationMedia.product_publication_id == publication.id)
    ).all()
    for item in existing:
        db.delete(item)
    for payload_item in payload.items:
        db.add(
            ProductPublicationMedia(
                product_publication_id=publication.id,
                product_media_id=payload_item.product_media_id,
                sort_order=payload_item.sort_order,
                active=payload_item.active,
            )
        )
    if publication.publication_status == "gepubliceerd":
        publication.publication_status = "synchronisatie_nodig"
    db.commit()
    return list_publication_media(item_id, db)


@router.post("/product-publications/{item_id}/publish")
def publish_product_publication(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductPlatformPublication, item_id)
    return publish_publication(db, item)


@router.post("/product-publications/{item_id}/sync")
def sync_product_publication(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductPlatformPublication, item_id)
    return sync_publication(db, item)


@router.post("/product-publications/{item_id}/pause")
def pause_product_publication(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductPlatformPublication, item_id)
    item.publication_status = "gepauzeerd"
    db.commit()
    return to_dict(item)


@router.get("/product-publications/{item_id}/check")
def check_product_publication(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductPlatformPublication, item_id)
    return validate_publication_record(db, item)



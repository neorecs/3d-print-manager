from sqlalchemy import select
from sqlalchemy.orm import Session

from api.utils import to_dict
from core.config import get_settings
from models import Product, ProductTag, ProductTranslation
from publishing.service import mark_product_publications_sync_needed
from schemas.common import ProductTranslationGenerate
from services.ai_product_assistant import generate_product_translation


def generate_product_translations_for_product(db: Session, product: Product, payload: ProductTranslationGenerate) -> dict:
    tags = [item.tag for item in db.scalars(select(ProductTag).where(ProductTag.product_id == product.id)).all()]
    source = {
        "name": product.name,
        "title": product.internal_title or product.name,
        "short_description": product.short_description,
        "long_description": product.long_description,
        "sales_description": product.sales_description,
        "seo_title": product.seo_title,
        "seo_description": product.seo_description,
        "tags": tags,
    }
    generated = []
    skipped = []
    for language_code in [code.strip().lower() for code in payload.language_codes if code.strip()]:
        existing = db.scalar(select(ProductTranslation).where(ProductTranslation.product_id == product.id, ProductTranslation.language_code == language_code))
        if existing and not payload.overwrite:
            skipped.append(language_code)
            continue
        translated = generate_product_translation(source, language_code, get_settings())
        data = {
            "language_code": language_code,
            "title": translated.get("title"),
            "short_description": translated.get("short_description"),
            "long_description": translated.get("long_description"),
            "sales_description": translated.get("sales_description"),
            "seo_title": translated.get("seo_title"),
            "seo_description": translated.get("seo_description"),
            "tags": translated.get("tags"),
            "source": translated.get("source") or "ai_translation",
            "status": "concept",
        }
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            item = existing
        else:
            item = ProductTranslation(product_id=product.id, **data)
            db.add(item)
        generated.append(item)
    if generated:
        mark_product_publications_sync_needed(db, product.id)
    db.commit()
    return {"generated": [to_dict(item) for item in generated], "skipped": skipped}

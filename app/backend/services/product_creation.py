from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.utils import to_dict
from models import Product, ProductVariant
from schemas.common import ProductWithVariantCreate


def save_product_with_variant(db: Session, payload: ProductWithVariantCreate) -> dict:
    product = Product(**payload.model_dump(exclude={"first_variant"}))
    try:
        db.add(product)
        db.flush()
        if payload.first_variant:
            variant = payload.first_variant.model_dump(exclude={"product_id"})
            db.add(ProductVariant(product_id=product.id, **variant))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Product niet opgeslagen. Controleer of de SKU al bestaat.") from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(product)
    return to_dict(product)

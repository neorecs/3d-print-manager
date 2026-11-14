from fastapi import APIRouter
from api.routes_shared import *
from pydantic import BaseModel, Field

from models import Product, ProductMedia
from services.ai_listing_studio import PHOTO_PRESETS, apply_channel_listing, edit_product_photo, generate_channel_listings
from services.ai_usage_service import ai_usage_status

router = APIRouter()

@router.get("/ai/product-draft/status")
def ai_product_draft_status(db: Session = Depends(get_db)) -> dict[str, object]:
    settings = get_settings()
    return {
        "enabled": settings.ai_openai_enabled,
        "configured": bool(settings.openai_api_key),
        "model": settings.openai_product_model,
        "ready": settings.ai_openai_enabled and bool(settings.openai_api_key),
        "note": "Echte AI gebruikt OpenAI API-tegoed en valt niet binnen ChatGPT Plus.",
        **ai_usage_status(db, settings.ai_daily_request_limit, settings.ai_daily_image_limit),
        "image_model": settings.openai_image_model,
    }


@router.post("/ai/product-draft/generate")
def ai_generate_product_draft(payload: AIProductDraftRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    return generate_ai_product_draft(payload, get_settings(), db)




class ChannelListingsRequest(BaseModel):
    channels: list[str]
    use_photos: bool = True


class ChannelListingApply(BaseModel):
    channel: str
    title: str
    description: str
    tags: list[str] = []


class PhotoEditRequest(BaseModel):
    preset: str | None = None
    instruction: str | None = Field(default=None, max_length=500)


def _product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product niet gevonden.")
    return product


@router.get("/ai/studio/photo-presets")
def ai_photo_presets() -> dict[str, object]:
    labels = {"witte_achtergrond": "Witte achtergrond", "lichte_studio": "Lichte studio", "woonkamer": "In de woonkamer", "buiten": "Buiten"}
    return {"presets": [{"key": key, "label": labels.get(key, key), "prompt": prompt} for key, prompt in PHOTO_PRESETS.items()]}


@router.post("/products/{product_id}/ai/listings")
def ai_channel_listings(product_id: int, payload: ChannelListingsRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    return generate_channel_listings(db, _product(db, product_id), payload.channels, get_settings(), payload.use_photos)


@router.post("/products/{product_id}/ai/listings/apply")
def ai_apply_channel_listing(product_id: int, payload: ChannelListingApply, db: Session = Depends(get_db)) -> dict[str, object]:
    updated = apply_channel_listing(db, _product(db, product_id), payload.channel, payload.title, payload.description, payload.tags)
    return {"updated": updated}


@router.post("/products/{product_id}/media/{media_id}/ai-edit")
def ai_edit_product_photo(product_id: int, media_id: int, payload: PhotoEditRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    media = db.get(ProductMedia, media_id)
    if media is None:
        raise HTTPException(status_code=404, detail="Foto niet gevonden.")
    return edit_product_photo(db, _product(db, product_id), media, payload.preset, payload.instruction, get_settings())

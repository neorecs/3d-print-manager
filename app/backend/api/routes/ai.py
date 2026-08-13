from fastapi import APIRouter
from api.routes_shared import *
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
        **ai_usage_status(db, settings.ai_daily_request_limit),
    }


@router.post("/ai/product-draft/generate")
def ai_generate_product_draft(payload: AIProductDraftRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    return generate_ai_product_draft(payload, get_settings(), db)



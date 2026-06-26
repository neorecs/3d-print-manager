import json
import urllib.error
import urllib.request
from typing import Any

from fastapi import HTTPException

from core.config import Settings
from schemas.common import AIProductDraftRequest


PRODUCT_DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["product", "tags", "variants", "platform_publications", "checklist"],
    "properties": {
        "product": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "name",
                "internal_title",
                "short_description",
                "long_description",
                "sales_description",
                "seo_title",
                "seo_description",
                "product_type",
                "internal_category",
                "status",
                "active",
            ],
            "properties": {
                "name": {"type": "string"},
                "internal_title": {"type": "string"},
                "short_description": {"type": "string"},
                "long_description": {"type": "string"},
                "sales_description": {"type": "string"},
                "seo_title": {"type": "string"},
                "seo_description": {"type": "string"},
                "product_type": {"type": "string"},
                "internal_category": {"type": "string"},
                "status": {"type": "string", "enum": ["concept"]},
                "active": {"type": "boolean"},
            },
        },
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 12},
        "variants": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "variant_name",
                    "sku",
                    "color",
                    "material",
                    "size",
                    "finish",
                    "estimated_print_time_minutes",
                    "estimated_filament_grams",
                    "default_sale_price",
                    "active",
                ],
                "properties": {
                    "variant_name": {"type": "string"},
                    "sku": {"type": "string"},
                    "color": {"type": "string"},
                    "material": {"type": "string"},
                    "size": {"type": ["string", "null"]},
                    "finish": {"type": "string"},
                    "estimated_print_time_minutes": {"type": ["integer", "null"]},
                    "estimated_filament_grams": {"type": ["number", "null"]},
                    "default_sale_price": {"type": ["number", "null"]},
                    "active": {"type": "boolean"},
                },
            },
        },
        "platform_publications": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "platform_title",
                    "platform_description",
                    "platform_category",
                    "platform_tags",
                    "platform_price_override",
                    "publication_status",
                ],
                "properties": {
                    "platform_title": {"type": "string"},
                    "platform_description": {"type": "string"},
                    "platform_category": {"type": "string"},
                    "platform_tags": {"type": "string"},
                    "platform_price_override": {"type": ["number", "null"]},
                    "publication_status": {"type": "string", "enum": ["concept"]},
                },
            },
        },
        "checklist": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 8},
    },
}


def generate_ai_product_draft(payload: AIProductDraftRequest, settings: Settings) -> dict[str, Any]:
    if not settings.ai_openai_enabled:
        raise HTTPException(status_code=403, detail="Echte AI-generatie staat uit. Zet AI_OPENAI_ENABLED=true om dit te gebruiken.")
    if not settings.openai_api_key:
        raise HTTPException(status_code=403, detail="OPENAI_API_KEY ontbreekt in de backend environment.")

    request_body = {
        "model": settings.openai_product_model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Je bent een Nederlandse productcopywriter voor een 3D-print webshop. "
                            "Maak producttitels, tags, omschrijvingen, SEO-velden en platformconcepten. "
                            "Gebruik alleen controleerbare claims. Verzin geen levertijden, keurmerken, garantie of technische eigenschappen. "
                            "Houd Bambu Studio/printbestanden buiten de verkooptekst. Status is altijd concept."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": json.dumps(payload.model_dump(), ensure_ascii=False)}],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "product_draft",
                "schema": PRODUCT_DRAFT_SCHEMA,
                "strict": True,
            }
        },
        "max_output_tokens": settings.ai_product_max_output_tokens,
    }

    response_data = post_openai_response(request_body, settings)
    draft = extract_json_response(response_data)
    draft["source"] = f"openai_api:{settings.openai_product_model}"
    draft["usage"] = response_data.get("usage") or {}
    return draft


def post_openai_response(request_body: dict[str, Any], settings: Settings) -> dict[str, Any]:
    data = json.dumps(request_body).encode("utf-8")
    request = urllib.request.Request(
        f"{settings.openai_api_base_url.rstrip('/')}/responses",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"OpenAI API fout: {detail}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI API niet bereikbaar: {exc}") from exc


def extract_json_response(response_data: dict[str, Any]) -> dict[str, Any]:
    if response_data.get("output_text"):
        return json.loads(response_data["output_text"])

    for item in response_data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return json.loads(content["text"])

    raise HTTPException(status_code=502, detail="OpenAI gaf geen bruikbare JSON-output terug.")

"""AI studio: listing texts per sales channel and photo edits.

Texts: one request writes a title, description and tags for every chosen
channel. The model sees the product data, the channel rules (from the channel
profiles) and, when available, a few product photos, so it describes what is
really in the picture. Every answer is checked against the channel rules; when
something is off the model gets one chance to repair it, after which the app
trims what is still too long. Nothing is saved until the seller takes it over.

Photos: an edit always becomes a NEW photo marked ai_edited, linked to the
original. The original stays, because Etsy requires at least one unedited photo
and buyers must see the real product.
"""

import base64
import json
import mimetypes
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.config import Settings
from models import Platform, Product, ProductMedia, ProductPlatformPublication
from publishing.channel_profiles import ChannelProfile, channel_profile, listing_issues
from publishing.service import mark_product_publications_sync_needed
from services.ai_product_assistant import extract_json_response, post_openai_response
from services.ai_usage_service import complete_ai_request, fail_ai_request, reserve_ai_request

UPLOAD_ROOT = Path("uploads")
MAX_PHOTOS_TO_AI = 4
MAX_PHOTO_BYTES_TO_AI = 8 * 1024 * 1024
DESCRIPTION_MAX = 5000

LISTINGS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["listings", "photo_notes"],
    "properties": {
        "listings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["channel", "title", "description", "tags"],
                "properties": {
                    "channel": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "photo_notes": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
    },
}

PHOTO_PRESETS: dict[str, str] = {
    "witte_achtergrond": "Plaats het product op een egale, helderwitte studioachtergrond met een zachte natuurlijke schaduw eronder.",
    "lichte_studio": "Maak er een heldere productfoto van op een lichtgrijze studioachtergrond met zacht, gelijkmatig licht.",
    "woonkamer": "Zet het product in een rustige, lichte Scandinavische woonkamer op een houten plank of tafel, met natuurlijk daglicht.",
    "buiten": "Zet het product buiten op een houten tuintafel in zacht ochtendlicht met wat groen onscherp op de achtergrond.",
}
PRESERVE_PRODUCT = (
    "Belangrijk: het product zelf moet exact hetzelfde blijven: zelfde vorm, afmetingen, kleur, laagstructuur van de 3D-print, "
    "details en aantal onderdelen. Voeg geen tekst, logo's, watermerken of extra producten toe."
)


# ----- channel rules ---------------------------------------------------------
def channel_rules(profile: ChannelProfile) -> dict[str, Any]:
    rules: dict[str, Any] = {"kanaal": profile.key, "naam": profile.label}
    if profile.title_max:
        rules["titel_max_tekens"] = profile.title_max
    if profile.tags_max_count:
        rules["max_tags"] = profile.tags_max_count
    if profile.tag_max_length:
        rules["tag_max_tekens"] = profile.tag_max_length
    style = {
        "etsy": "Titel begint met wat het is en voor wie; zoekwoorden die kopers echt typen. Beschrijving: eerste twee zinnen verkopen, daarna maten, materiaal en onderhoud.",
        "shopify": "Eigen webshop: merktoon, korte alinea's, opsomming van kenmerken.",
        "bol": "Zakelijk en feitelijk; bol-klanten scannen. Geen emoji's, geen hoofdletters-schreeuwen.",
        "marktplaats": "Kort en persoonlijk, alsof een particulier verkoopt. Vermeld ophalen/verzenden niet, dat kiest de verkoper zelf.",
        "vinted": "Kort, vriendelijk en eerlijk over staat (nieuw, zelf geprint). Hashtags zijn niet nodig.",
    }.get(profile.key)
    if style:
        rules["stijl"] = style
    if profile.notes:
        rules["let_op"] = list(profile.notes)
    return rules


def normalize_tags(tags: list[str] | str | None) -> list[str]:
    if isinstance(tags, str):
        tags = tags.split(",")
    seen, result = set(), []
    for tag in tags or []:
        clean = " ".join(str(tag).replace("#", " ").split()).strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            result.append(clean)
    return result


def _trim_title(title: str, limit: int) -> str:
    if len(title) <= limit:
        return title
    cut = title[:limit].rsplit(" ", 1)[0].rstrip(" ,-–|")
    return cut or title[:limit]


def enforce_rules(profile: ChannelProfile, listing: dict[str, Any]) -> dict[str, Any]:
    """Last line of defence after the model: make the listing fit the documented limits."""
    title = " ".join(str(listing.get("title") or "").split())
    if profile.title_max:
        title = _trim_title(title, profile.title_max)
    tags = normalize_tags(listing.get("tags"))
    if profile.tag_max_length:
        tags = [tag for tag in tags if len(tag) <= profile.tag_max_length]
    if profile.tags_max_count:
        tags = tags[: profile.tags_max_count]
    description = str(listing.get("description") or "").strip()[:DESCRIPTION_MAX]
    return {"channel": profile.key, "title": title, "description": description, "tags": tags}


def rule_issues(profile: ChannelProfile, listing: dict[str, Any]) -> list[str]:
    tags = normalize_tags(listing.get("tags"))
    issues = listing_issues(profile, profile.label, listing.get("title"), tags, photo_count=1)
    if not str(listing.get("title") or "").strip():
        issues.append(f"{profile.label}: titel ontbreekt.")
    return issues


# ----- photos ------------------------------------------------------------------
def resolve_upload(file_path: str | None) -> Path | None:
    root = UPLOAD_ROOT.resolve()
    target = (root / (file_path or "").removeprefix("/uploads/")).resolve()
    if root not in target.parents or not target.is_file():
        return None
    return target


def product_photos(db: Session, product: Product) -> list[ProductMedia]:
    return list(db.scalars(
        select(ProductMedia)
        .where(ProductMedia.product_id == product.id, ProductMedia.media_type == "image")
        .order_by(ProductMedia.is_primary.desc(), ProductMedia.sort_order, ProductMedia.id)
    ).all())


def photo_inputs(db: Session, product: Product) -> list[dict[str, str]]:
    """Original photos first: they show the real product."""
    photos = sorted(product_photos(db, product), key=lambda item: item.ai_edited)
    inputs = []
    for media in photos:
        path = resolve_upload(media.file_path)
        if path is None or path.stat().st_size > MAX_PHOTO_BYTES_TO_AI:
            continue
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        if mime not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
            continue
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        inputs.append({"type": "input_image", "image_url": f"data:{mime};base64,{data}", "detail": "low"})
        if len(inputs) >= MAX_PHOTOS_TO_AI:
            break
    return inputs


# ----- texts -------------------------------------------------------------------
def _product_facts(db: Session, product: Product) -> dict[str, Any]:
    variants = [
        {key: getattr(variant, key, None) for key in ("variant_name", "color", "material", "size", "finish")}
        | {"prijs": float(variant.default_sale_price) if variant.default_sale_price is not None else None}
        for variant in product.variants
        if variant.active
    ]
    return {
        "naam": product.name,
        "type": product.product_type,
        "categorie": product.internal_category,
        "korte_omschrijving": product.short_description,
        "omschrijving": product.long_description or product.sales_description,
        "varianten": variants,
    }


def _mock_listing(profile: ChannelProfile, facts: dict[str, Any]) -> dict[str, Any]:
    name = facts.get("naam") or "Product"
    colors = ", ".join(sorted({variant["color"] for variant in facts["varianten"] if variant.get("color")}))
    title = f"{name} – 3D-geprint" + (f" in {colors}" if colors else "")
    description = "\n\n".join(part for part in [facts.get("korte_omschrijving"), facts.get("omschrijving")] if part) or f"{name}, zelf ontworpen en 3D-geprint."
    tags = [name, facts.get("type") or "", facts.get("categorie") or "", "3D print", "cadeau", *(colors.split(", ") if colors else [])]
    return {"channel": profile.key, "title": title, "description": f"[Voorbeeldtekst zonder AI] {description}", "tags": tags}


def _request_body(settings: Settings, facts: dict, rules: list[dict], photos: list[dict], repair: dict | None = None) -> dict:
    instructions = (
        "Je schrijft verkoopteksten voor een kleine Nederlandse maker van 3D-geprinte producten. "
        "Schrijf in het Nederlands, per gevraagd kanaal precies één advertentie, en houd je strikt aan de regels van dat kanaal. "
        "Beschrijf alleen wat in de productgegevens staat of duidelijk op de foto's te zien is. "
        "Verzin geen maten, levertijden, keurmerken, garanties of materialen. "
        "Als iets belangrijks ontbreekt (bijvoorbeeld afmetingen), noem dat in photo_notes in plaats van het te verzinnen. "
        "Gebruik in photo_notes ook korte tips over welke foto nog ontbreekt."
    )
    payload: dict[str, Any] = {"product": facts, "kanalen": rules}
    if repair:
        payload["vorige_versie"] = repair["listings"]
        payload["te_herstellen"] = repair["issues"]
        instructions += " Je krijgt je vorige versie met de overtredingen; herstel alleen wat nodig is."
    content: list[dict[str, Any]] = [{"type": "input_text", "text": json.dumps(payload, ensure_ascii=False)}]
    content.extend(photos)
    return {
        "model": settings.openai_product_model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": instructions}]},
            {"role": "user", "content": content},
        ],
        "text": {"format": {"type": "json_schema", "name": "channel_listings", "schema": LISTINGS_SCHEMA, "strict": True}},
        "max_output_tokens": settings.ai_product_max_output_tokens,
    }


def _call(db: Session, settings: Settings, action: str, body: dict) -> dict:
    usage_log = reserve_ai_request(db, action, settings.openai_product_model, settings.ai_daily_request_limit)
    try:
        response = post_openai_response(body, settings)
    except Exception as exc:
        fail_ai_request(db, usage_log, exc)
        raise
    complete_ai_request(db, usage_log, response.get("usage"))
    return extract_json_response(response)


def generate_channel_listings(db: Session, product: Product, channels: list[str], settings: Settings, use_photos: bool = True) -> dict[str, Any]:
    profiles: list[ChannelProfile] = []
    for channel in channels:
        profile = channel_profile(channel)
        if channel.strip() and profile.key not in {item.key for item in profiles}:
            profiles.append(profile)
    if not profiles:
        raise HTTPException(status_code=400, detail="Kies minstens één verkoopkanaal.")
    by_key = {profile.key: profile for profile in profiles}
    facts = _product_facts(db, product)
    ai_ready = settings.ai_openai_enabled and bool(settings.openai_api_key)

    notes: list[str] = []
    repaired = False
    photos_used = 0
    if not ai_ready:
        raw = [_mock_listing(profile, facts) for profile in profiles]
        notes.append("AI staat uit (AI_OPENAI_ENABLED) of de OpenAI-sleutel ontbreekt; dit zijn voorbeeldteksten uit de productgegevens.")
        source = "voorbeeld"
    else:
        photos = photo_inputs(db, product) if use_photos else []
        photos_used = len(photos)
        rules = [channel_rules(profile) for profile in profiles]
        result = _call(db, settings, f"listings:{product.id}", _request_body(settings, facts, rules, photos))
        raw = result.get("listings") or []
        notes.extend(result.get("photo_notes") or [])
        issues = [issue for item in raw if item.get("channel") in by_key for issue in rule_issues(by_key[item["channel"]], item)]
        missing = [key for key in by_key if key not in {item.get("channel") for item in raw}]
        issues.extend(f"Advertentie voor {by_key[key].label} ontbreekt." for key in missing)
        if issues:
            repaired = True
            result = _call(db, settings, f"listings-repair:{product.id}", _request_body(settings, facts, rules, [], {"listings": raw, "issues": issues}))
            raw = result.get("listings") or raw
        source = f"openai_api:{settings.openai_product_model}"

    listings = []
    for profile in profiles:
        item = next((entry for entry in raw if entry.get("channel") == profile.key), None)
        if item is None:
            continue
        before = rule_issues(profile, item)
        fitted = enforce_rules(profile, item)
        fitted["adjusted"] = bool(before)
        fitted["rules"] = channel_rules(profile)
        listings.append(fitted)
    return {"listings": listings, "notes": notes, "source": source, "repaired": repaired, "photos_used": photos_used}


def apply_channel_listing(db: Session, product: Product, channel: str, title: str, description: str, tags: list[str]) -> list[dict]:
    """Write an approved text into every publication of this product on channels of that type."""
    profile = channel_profile(channel)
    fitted = enforce_rules(profile, {"title": title, "description": description, "tags": tags})
    publications = db.scalars(
        select(ProductPlatformPublication)
        .join(Platform, Platform.id == ProductPlatformPublication.platform_id)
        .where(ProductPlatformPublication.product_id == product.id, func.lower(Platform.type) == profile.key)
    ).all()
    if not publications:
        raise HTTPException(status_code=404, detail=f"Dit product heeft nog geen publicatie op een {profile.label}-kanaal. Voeg die eerst toe onder Publicaties.")
    for publication in publications:
        publication.platform_title = fitted["title"][:255]
        publication.platform_description = fitted["description"]
        publication.platform_tags = ", ".join(fitted["tags"])
    mark_product_publications_sync_needed(db, product.id)
    db.commit()
    return [{"publication_id": publication.id, "platform_id": publication.platform_id} for publication in publications]


# ----- photo edits ----------------------------------------------------------------
def _multipart(fields: dict[str, str], file_field: str, filename: str, content: bytes, mime: str) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n'.encode() + content + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def post_openai_image_edit(settings: Settings, image: bytes, filename: str, mime: str, prompt: str) -> dict[str, Any]:
    body, content_type = _multipart(
        {"model": settings.openai_image_model, "prompt": prompt, "quality": settings.openai_image_quality, "n": "1"},
        "image", filename, image, mime,
    )
    request = urllib.request.Request(
        f"{settings.openai_api_base_url.rstrip('/')}/images/edits",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": content_type},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"OpenAI beeldbewerking mislukt: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI niet bereikbaar: {exc}") from exc


def edit_product_photo(db: Session, product: Product, media: ProductMedia, preset: str | None, instruction: str | None, settings: Settings) -> dict[str, Any]:
    if media.product_id != product.id or media.media_type != "image":
        raise HTTPException(status_code=404, detail="Foto niet gevonden bij dit product.")
    if not (settings.ai_openai_enabled and settings.openai_api_key):
        raise HTTPException(status_code=403, detail="Fotobewerking met AI staat uit. Zet AI_OPENAI_ENABLED=true en vul OPENAI_API_KEY in.")
    wish = PHOTO_PRESETS.get(preset or "") or (instruction or "").strip()
    if not wish:
        raise HTTPException(status_code=400, detail="Kies een stijl of beschrijf wat je wilt.")
    if instruction and preset in PHOTO_PRESETS:
        wish = f"{wish} {instruction.strip()}"
    source_path = resolve_upload(media.file_path)
    if source_path is None:
        raise HTTPException(status_code=404, detail="Het fotobestand is niet gevonden op de server.")
    mime = mimetypes.guess_type(source_path.name)[0] or "image/png"

    usage_log = reserve_ai_request(db, f"image:edit:{media.id}", settings.openai_image_model, settings.ai_daily_image_limit)
    try:
        response = post_openai_image_edit(settings, source_path.read_bytes(), source_path.name, mime, f"{wish}\n\n{PRESERVE_PRODUCT}")
        encoded = ((response.get("data") or [{}])[0]).get("b64_json")
        if not encoded:
            raise HTTPException(status_code=502, detail="OpenAI gaf geen afbeelding terug.")
        image = base64.b64decode(encoded)
    except Exception as exc:
        fail_ai_request(db, usage_log, exc)
        raise
    complete_ai_request(db, usage_log, response.get("usage"))

    target_dir = UPLOAD_ROOT / "product_media" / str(product.id)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"ai-{uuid.uuid4().hex}.png"
    (target_dir / filename).write_bytes(image)
    next_order = (db.scalar(select(func.max(ProductMedia.sort_order)).where(ProductMedia.product_id == product.id)) or 0) + 1
    created = ProductMedia(
        product_id=product.id,
        file_path=f"/uploads/product_media/{product.id}/{filename}",
        media_type="image",
        alt_text=f"{product.name} (AI-bewerkte foto)"[:255],
        sort_order=next_order,
        is_primary=False,
        ai_edited=True,
        source_media_id=media.id,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return {"id": created.id, "file_path": created.file_path, "ai_edited": True, "source_media_id": media.id}

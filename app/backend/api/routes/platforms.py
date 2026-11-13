import hmac
import secrets
import time

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func

from api.routes_shared import *
from connectors.etsy import oauth as etsy_oauth
from connectors.factory import load_platform_credentials, store_platform_credentials
from services.platform_service import connector_status_payload, normalize_language_list, sync_platform_inventory_payload
from services.auth_service import record_audit_log

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
        record_audit_log(db, None, "platform.credential_updated", "platform", str(platform_id), f"Credential {key_name} bijgewerkt.")
        return public_credential_dict(existing)
    item = PlatformCredential(platform_id=platform_id, key_name=key_name, encrypted_value=encrypt_credential(payload.encrypted_value))
    db.add(item)
    db.commit()
    db.refresh(item)
    record_audit_log(db, None, "platform.credential_created", "platform", str(platform_id), f"Credential {key_name} opgeslagen.")
    return public_credential_dict(item)


@router.delete("/platform-credentials/{item_id}")
def delete_platform_credential(item_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, PlatformCredential, item_id)
    platform_id = item.platform_id
    key_name = item.key_name
    db.delete(item)
    db.commit()
    record_audit_log(db, None, "platform.credential_deleted", "platform", str(platform_id), f"Credential {key_name} verwijderd.")
    return {"status": "deleted"}


@router.get("/platforms/{platform_id}/connector-status")
def platform_connector_status(platform_id: int, db: Session = Depends(get_db)):
    platform = get_or_404(db, Platform, platform_id)
    return connector_status_payload(db, platform)


@router.post("/platforms/{platform_id}/sync-inventory")
def sync_platform_inventory(platform_id: int, db: Session = Depends(get_db)):
    platform = get_or_404(db, Platform, platform_id)
    return sync_platform_inventory_payload(db, platform)




ETSY_OAUTH_MAX_AGE_SECONDS = 15 * 60
ETSY_OAUTH_KEYS = ("oauth_state", "oauth_code_verifier", "oauth_started_at")


class EtsyOAuthCallback(BaseModel):
    code: str
    state: str


def _etsy_redirect_uri() -> str:
    redirect_uri = (get_settings().etsy_redirect_uri or "").strip()
    if not redirect_uri:
        raise HTTPException(status_code=409, detail="ETSY_REDIRECT_URI is niet ingesteld. Zet het terugkeeradres van de Etsy-app in de configuratie.")
    return redirect_uri


@router.post("/platform-credentials/etsy/{platform_id}/oauth/start")
def start_etsy_oauth(platform_id: int, request: Request, db: Session = Depends(get_db)):
    platform = get_or_404(db, Platform, platform_id)
    if (platform.type or "").lower() != "etsy":
        raise HTTPException(status_code=400, detail="Dit verkoopkanaal is geen Etsy-kanaal.")
    credentials = load_platform_credentials(db, platform)
    if not credentials.get("api_key"):
        raise HTTPException(status_code=409, detail="Sla eerst de Etsy API-key op.")
    redirect_uri = _etsy_redirect_uri()
    state = secrets.token_urlsafe(32)
    verifier, challenge = etsy_oauth.new_pkce_pair()
    store_platform_credentials(db, platform.id, {
        "oauth_state": state,
        "oauth_code_verifier": verifier,
        "oauth_started_at": str(int(time.time())),
    })
    db.commit()
    record_audit_log(db, None, "platform.etsy_oauth_started", "platform", str(platform.id), f"Etsy-koppeling gestart door {getattr(request.state, 'user_email', 'onbekend')}.")
    return {"authorize_url": etsy_oauth.authorize_url(credentials["api_key"].split(":", 1)[0], redirect_uri, state, challenge)}


@router.post("/platform-credentials/etsy/oauth/callback")
def finish_etsy_oauth(payload: EtsyOAuthCallback, request: Request, db: Session = Depends(get_db)):
    match = None
    for platform in db.scalars(select(Platform).where(func.lower(Platform.type) == "etsy")).all():
        credentials = load_platform_credentials(db, platform)
        stored_state = credentials.get("oauth_state") or ""
        if stored_state and hmac.compare_digest(stored_state, payload.state):
            match = (platform, credentials)
            break
    if not match:
        raise HTTPException(status_code=400, detail="Onbekende of verlopen Etsy-koppeling. Start het verbinden opnieuw.")
    platform, credentials = match
    started_at = int(credentials.get("oauth_started_at") or 0)
    if time.time() - started_at > ETSY_OAUTH_MAX_AGE_SECONDS:
        store_platform_credentials(db, platform.id, {key: "" for key in ETSY_OAUTH_KEYS})
        db.commit()
        raise HTTPException(status_code=400, detail="De Etsy-koppeling is verlopen. Start het verbinden opnieuw.")
    try:
        tokens = etsy_oauth.exchange_code(credentials["api_key"], _etsy_redirect_uri(), payload.code, credentials["oauth_code_verifier"])
    except etsy_oauth.EtsyOAuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    store_platform_credentials(db, platform.id, {**tokens, **{key: "" for key in ETSY_OAUTH_KEYS}})
    db.commit()
    record_audit_log(db, None, "platform.etsy_oauth_connected", "platform", str(platform.id), f"Etsy verbonden door {getattr(request.state, 'user_email', 'onbekend')}.")
    return {"status": "connected", "platform_id": platform.id}

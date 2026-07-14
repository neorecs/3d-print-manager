from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core.config import get_settings
from database import get_db
from schemas.common import AuthBootstrapAdmin, AuthLogin, AuthMfaConfirm, AuthMfaSetup
from services.auth_service import authenticate_user, confirm_mfa_setup, create_admin_user, has_admin_user, start_mfa_setup

router = APIRouter(prefix="/auth", tags=["auth"])


def user_payload(user) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "mfa_enabled": user.mfa_enabled,
    }


@router.post("/login")
def login(payload: AuthLogin, request: Request, db: Session = Depends(get_db)) -> dict:
    user = authenticate_user(
        db,
        payload.email,
        payload.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"user": user_payload(user)}


@router.post("/bootstrap-admin")
def bootstrap_admin(payload: AuthBootstrapAdmin, db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    if not settings.auth_bootstrap_secret:
        raise HTTPException(status_code=403, detail="Admin-bootstrap staat niet aan.")
    if payload.bootstrap_secret != settings.auth_bootstrap_secret:
        raise HTTPException(status_code=403, detail="Bootstrap-secret klopt niet.")
    if has_admin_user(db):
        raise HTTPException(status_code=409, detail="Er bestaat al een admingebruiker.")

    user = create_admin_user(db, payload.email, payload.password, payload.display_name)
    return {"user": user_payload(user)}


@router.post("/mfa/setup")
def mfa_setup(payload: AuthMfaSetup, db: Session = Depends(get_db)) -> dict:
    return start_mfa_setup(db, payload.email, payload.password)


@router.post("/mfa/confirm")
def mfa_confirm(payload: AuthMfaConfirm, db: Session = Depends(get_db)) -> dict:
    user = confirm_mfa_setup(db, payload.email, payload.password, payload.code)
    return {"user": user_payload(user)}

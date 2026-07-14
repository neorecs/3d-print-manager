from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core.config import get_settings
from database import get_db
from schemas.common import AuthBootstrapAdmin, AuthLogin, AuthMfaConfirm, AuthMfaSetup, AuthPasswordReset, AuthUserCreate, AuthUserUpdate
from services.auth_service import (
    authenticate_user,
    confirm_mfa_setup,
    create_admin_user,
    create_user,
    has_admin_user,
    list_audit_logs,
    list_users,
    reset_user_mfa,
    reset_user_password,
    start_mfa_setup,
    update_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def user_payload(user) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "is_active": user.is_active,
        "mfa_enabled": user.mfa_enabled,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def audit_log_payload(log) -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "summary": log.summary,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "created_at": log.created_at.isoformat() if log.created_at else None,
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


@router.get("/users")
def users_list(db: Session = Depends(get_db)) -> list[dict]:
    return [user_payload(user) for user in list_users(db)]


@router.post("/users")
def users_create(payload: AuthUserCreate, db: Session = Depends(get_db)) -> dict:
    user = create_user(db, payload.email, payload.password, payload.display_name, payload.role, payload.is_active)
    return user_payload(user)


@router.patch("/users/{user_id}")
def users_update(user_id: int, payload: AuthUserUpdate, db: Session = Depends(get_db)) -> dict:
    user = update_user(db, user_id, payload.display_name, payload.role, payload.is_active)
    return user_payload(user)


@router.post("/users/{user_id}/reset-password")
def users_reset_password(user_id: int, payload: AuthPasswordReset, db: Session = Depends(get_db)) -> dict:
    user = reset_user_password(db, user_id, payload.password)
    return user_payload(user)


@router.post("/users/{user_id}/mfa/reset")
def users_reset_mfa(user_id: int, db: Session = Depends(get_db)) -> dict:
    user = reset_user_mfa(db, user_id)
    return user_payload(user)


@router.get("/audit-logs")
def audit_logs(limit: int = 100, db: Session = Depends(get_db)) -> list[dict]:
    return [audit_log_payload(log) for log in list_audit_logs(db, limit)]


@router.post("/mfa/setup")
def mfa_setup(payload: AuthMfaSetup, db: Session = Depends(get_db)) -> dict:
    return start_mfa_setup(db, payload.email, payload.password)


@router.post("/mfa/confirm")
def mfa_confirm(payload: AuthMfaConfirm, db: Session = Depends(get_db)) -> dict:
    user = confirm_mfa_setup(db, payload.email, payload.password, payload.code)
    return {"user": user_payload(user)}

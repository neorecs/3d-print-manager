from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.credentials import decrypt_credential, encrypt_credential
from core.security import generate_totp_secret, hash_password, verify_password, verify_totp_code
from models import AuditLog, User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def has_admin_user(db: Session) -> bool:
    return db.scalar(select(User).where(User.role == "admin").limit(1)) is not None


def create_admin_user(db: Session, email: str, password: str, display_name: str | None = None) -> User:
    normalized_email = email.strip().lower()
    if not normalized_email or "@" not in normalized_email:
        raise HTTPException(status_code=400, detail="Geef een geldig e-mailadres op.")
    if len(password) < 12:
        raise HTTPException(status_code=400, detail="Gebruik minimaal 12 tekens voor het adminwachtwoord.")
    if get_user_by_email(db, normalized_email):
        raise HTTPException(status_code=409, detail="Deze gebruiker bestaat al.")

    user = User(
        email=normalized_email,
        display_name=display_name,
        password_hash=hash_password(password),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    record_audit_log(db, user, "auth.admin_created", "user", str(user.id), "Eerste admingebruiker aangemaakt.")
    return user


def authenticate_user(db: Session, email: str, password: str, ip_address: str | None = None, user_agent: str | None = None) -> User:
    user = get_user_by_email(db, email)
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        record_audit_log(db, None, "auth.login_failed", "user", None, f"Mislukte login voor {email}.", ip_address, user_agent)
        raise HTTPException(status_code=401, detail="E-mailadres of wachtwoord klopt niet.")

    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)
    record_audit_log(db, user, "auth.login_success", "user", str(user.id), "Gebruiker ingelogd.", ip_address, user_agent)
    return user


def start_mfa_setup(db: Session, email: str, password: str) -> dict:
    user = authenticate_user(db, email, password)
    if user.mfa_enabled:
        raise HTTPException(status_code=409, detail="MFA staat al aan voor deze gebruiker.")

    secret = generate_totp_secret()
    user.totp_secret_encrypted = encrypt_credential(secret)
    db.add(user)
    db.commit()
    db.refresh(user)
    record_audit_log(db, user, "auth.mfa_setup_started", "user", str(user.id), "MFA setup gestart.")

    return {
        "secret": secret,
        "otpauth_url": build_totp_uri(user.email, secret),
        "mfa_enabled": user.mfa_enabled,
    }


def confirm_mfa_setup(db: Session, email: str, password: str, code: str) -> User:
    user = authenticate_user(db, email, password)
    if not user.totp_secret_encrypted:
        raise HTTPException(status_code=400, detail="Start eerst MFA setup.")

    secret = decrypt_credential(user.totp_secret_encrypted)
    if not verify_totp_code(secret, code):
        record_audit_log(db, user, "auth.mfa_confirm_failed", "user", str(user.id), "Ongeldige MFA bevestigingscode.")
        raise HTTPException(status_code=401, detail="MFA-code klopt niet.")

    user.mfa_enabled = True
    db.add(user)
    db.commit()
    db.refresh(user)
    record_audit_log(db, user, "auth.mfa_enabled", "user", str(user.id), "MFA ingeschakeld.")
    return user


def build_totp_uri(email: str, secret: str) -> str:
    issuer = "3D Print Manager"
    label = f"{issuer}:{email}"
    return (
        "otpauth://totp/"
        f"{quote(label)}?secret={quote(secret)}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"
    )


def record_audit_log(
    db: Session,
    user: User | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    summary: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    return log

from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from core.credentials import decrypt_credential, encrypt_credential
from core.security import generate_totp_secret, hash_password, verify_password, verify_totp_code
from models import AuditLog, User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def has_admin_user(db: Session) -> bool:
    return db.scalar(select(User).where(User.role == "admin").limit(1)) is not None


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.email)).all())


def list_audit_logs(db: Session, limit: int = 100) -> list[AuditLog]:
    bounded_limit = min(max(limit, 1), 500)
    return list(db.scalars(select(AuditLog).order_by(desc(AuditLog.created_at), desc(AuditLog.id)).limit(bounded_limit)).all())


def create_admin_user(db: Session, email: str, password: str, display_name: str | None = None) -> User:
    return create_user(db, email=email, password=password, display_name=display_name, role="admin", is_active=True)


def create_user(
    db: Session,
    email: str,
    password: str,
    display_name: str | None = None,
    role: str = "operator",
    is_active: bool = True,
) -> User:
    normalized_email = email.strip().lower()
    if not normalized_email or "@" not in normalized_email:
        raise HTTPException(status_code=400, detail="Geef een geldig e-mailadres op.")
    if len(password) < 12:
        raise HTTPException(status_code=400, detail="Gebruik minimaal 12 tekens voor het wachtwoord.")
    normalized_role = normalize_role(role)
    if get_user_by_email(db, normalized_email):
        raise HTTPException(status_code=409, detail="Deze gebruiker bestaat al.")

    user = User(
        email=normalized_email,
        display_name=display_name,
        password_hash=hash_password(password),
        role=normalized_role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    action = "auth.admin_created" if normalized_role == "admin" else "auth.user_created"
    record_audit_log(db, user, action, "user", str(user.id), f"Gebruiker {normalized_email} aangemaakt.")
    return user


def update_user(
    db: Session,
    user_id: int,
    display_name: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
) -> User:
    user = get_user_or_404(db, user_id)
    new_role = normalize_role(role) if role is not None else user.role
    new_active = is_active if is_active is not None else user.is_active
    ensure_not_removing_last_active_admin(db, user, new_role, new_active)

    if display_name is not None:
        user.display_name = display_name
    user.role = new_role
    user.is_active = new_active
    db.add(user)
    db.commit()
    db.refresh(user)
    record_audit_log(db, user, "auth.user_updated", "user", str(user.id), f"Gebruiker {user.email} bijgewerkt.")
    return user


def reset_user_password(db: Session, user_id: int, password: str) -> User:
    if len(password) < 12:
        raise HTTPException(status_code=400, detail="Gebruik minimaal 12 tekens voor het wachtwoord.")
    user = get_user_or_404(db, user_id)
    user.password_hash = hash_password(password)
    db.add(user)
    db.commit()
    db.refresh(user)
    record_audit_log(db, user, "auth.password_reset", "user", str(user.id), f"Wachtwoord reset voor {user.email}.")
    return user


def reset_user_mfa(db: Session, user_id: int) -> User:
    user = get_user_or_404(db, user_id)
    user.mfa_enabled = False
    user.totp_secret_encrypted = None
    db.add(user)
    db.commit()
    db.refresh(user)
    record_audit_log(db, user, "auth.mfa_reset", "user", str(user.id), f"MFA reset voor {user.email}.")
    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
    mfa_code: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User:
    user = get_user_by_email(db, email)
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        record_audit_log(db, None, "auth.login_failed", "user", None, f"Mislukte login voor {email}.", ip_address, user_agent)
        raise HTTPException(status_code=401, detail="E-mailadres of wachtwoord klopt niet.")

    if user.mfa_enabled:
        if not user.totp_secret_encrypted:
            record_audit_log(db, user, "auth.mfa_missing_secret", "user", str(user.id), "MFA staat aan zonder secret.", ip_address, user_agent)
            raise HTTPException(status_code=403, detail="MFA is niet goed ingesteld. Vraag een admin om MFA te resetten.")
        if not mfa_code:
            record_audit_log(db, user, "auth.mfa_required", "user", str(user.id), "MFA-code vereist voor login.", ip_address, user_agent)
            raise HTTPException(status_code=401, detail={"message": "MFA-code vereist.", "mfa_required": True})
        secret = decrypt_credential(user.totp_secret_encrypted)
        if not verify_totp_code(secret, mfa_code):
            record_audit_log(db, user, "auth.mfa_login_failed", "user", str(user.id), "Ongeldige MFA-code bij login.", ip_address, user_agent)
            raise HTTPException(status_code=401, detail={"message": "MFA-code klopt niet.", "mfa_required": True})

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


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Gebruiker niet gevonden.")
    return user


def normalize_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized not in {"admin", "operator", "viewer"}:
        raise HTTPException(status_code=400, detail="Rol moet admin, operator of viewer zijn.")
    return normalized


def ensure_not_removing_last_active_admin(db: Session, user: User, new_role: str, new_active: bool) -> None:
    if user.role != "admin" or (new_role == "admin" and new_active):
        return
    active_admin_count = db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.is_active.is_(True)))
    if active_admin_count == 1:
        raise HTTPException(status_code=400, detail="De laatste actieve admin mag niet worden gedeactiveerd of gedegradeerd.")

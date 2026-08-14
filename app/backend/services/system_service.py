import os
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.config import get_settings


def system_readiness_payload(db: Session) -> dict:
    settings = get_settings()
    encryption_configured = bool(os.getenv("CREDENTIAL_ENCRYPTION_KEY"))
    internal_api_configured = bool(settings.backend_internal_token)
    session_signing_configured = bool(settings.auth_secret)
    database_configured = bool(settings.database_url)
    database_reachable = False
    if database_configured:
        try:
            db.execute(text("SELECT 1"))
            database_reachable = True
        except Exception:  # noqa: BLE001
            db.rollback()
    upload_root = Path("uploads")
    upload_storage_writable = upload_root.exists() and os.access(upload_root, os.W_OK)
    upload_backup_configured = os.getenv("UPLOAD_BACKUP_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    backup_status_dir = Path(os.getenv("BACKUP_STATUS_DIR", "/backup-status/status"))
    backup_max_age_seconds = max(int(os.getenv("BACKUP_MAX_AGE_HOURS", "48")), 1) * 3600
    database_backup_recent = _marker_is_recent(backup_status_dir / "postgres-last-success", backup_max_age_seconds)
    upload_backup_recent = _marker_is_recent(backup_status_dir / "uploads-last-success", backup_max_age_seconds)
    restore_test_recent = _marker_is_recent(backup_status_dir / "restore-test-last-success", 90 * 24 * 3600)
    auth_enabled = os.getenv("AUTH_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    auth_backend_login = os.getenv("AUTH_BACKEND_LOGIN", "false").strip().lower() in {"1", "true", "yes", "on"}
    connectors_live_mode = os.getenv("CONNECTORS_LIVE_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
    secure_cookie_enabled = os.getenv("AUTH_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes", "on"}
    ai_configured = bool(settings.openai_api_key)

    blockers = []
    if not encryption_configured:
        blockers.append("Stel CREDENTIAL_ENCRYPTION_KEY in voordat echte tokens worden opgeslagen.")
    if not internal_api_configured or not session_signing_configured:
        blockers.append("Interne backendauthenticatie en sessieondertekening zijn niet volledig ingesteld.")
    if not database_reachable:
        blockers.append("De PostgreSQL databaseverbinding kon niet worden bevestigd.")
    if not upload_storage_writable:
        blockers.append("De opslag voor foto's, documenten en printbestanden is niet schrijfbaar.")
    if not upload_backup_configured or not upload_backup_recent:
        blockers.append("Er is geen recente geslaagde backup van foto's, documenten en printbestanden bevestigd.")
    if not database_backup_recent:
        blockers.append("Er is geen recente geslaagde PostgreSQL-backup bevestigd.")
    if not restore_test_recent:
        blockers.append("Er is de afgelopen 90 dagen geen gezamenlijke hersteltest bevestigd.")
    if not auth_enabled or not auth_backend_login:
        blockers.append("Login met databasegebruikers is niet volledig actief.")
    if not secure_cookie_enabled:
        blockers.append("HTTPS/secure cookies zijn nog niet actief. Gebruik daarom nog geen externe toegang.")
    if connectors_live_mode:
        blockers.append("CONNECTORS_LIVE_MODE staat aan. Zet deze uit zolang je alleen veilig wilt voorbereiden.")

    return {
        "connectors_live_mode": connectors_live_mode,
        "live_calls_blocked": not connectors_live_mode,
        "credential_encryption_configured": encryption_configured,
        "internal_api_configured": internal_api_configured,
        "session_signing_configured": session_signing_configured,
        "database_configured": database_configured,
        "database_reachable": database_reachable,
        "upload_storage_writable": upload_storage_writable,
        "upload_backup_configured": upload_backup_configured,
        "database_backup_recent": database_backup_recent,
        "upload_backup_recent": upload_backup_recent,
        "restore_test_recent": restore_test_recent,
        "auth_enabled": auth_enabled,
        "auth_backend_login": auth_backend_login,
        "secure_cookie_enabled": secure_cookie_enabled,
        "ai_enabled": settings.ai_openai_enabled,
        "ai_configured": ai_configured,
        "openai_model": settings.openai_product_model,
        "platform_subscription_required_now": False,
        "safe_without_platform_subscription": not connectors_live_mode,
        "backup_plan_documented": True,
        "ready_for_real_tokens": all(
            [
                encryption_configured,
                internal_api_configured,
                session_signing_configured,
                database_reachable,
                upload_storage_writable,
                upload_backup_configured,
                database_backup_recent,
                upload_backup_recent,
                restore_test_recent,
                auth_enabled,
                auth_backend_login,
                secure_cookie_enabled,
                not connectors_live_mode,
            ]
        ),
        "blockers": blockers,
        "next_checks": [
            "Controleer of de postgres_backup container dagelijks een .dump en .sha256 bestand maakt.",
            "Laat CONNECTORS_LIVE_MODE uit totdat de Etsy/Shopify OAuth-flow bewust getest wordt.",
            "Voeg platformtokens pas toe via de app nadat de juiste callback-URL bekend is.",
            "Test eerst lezen/importeren met een beperkt platformaccount voordat je publicatie of sync activeert.",
        ],
    }


def _marker_is_recent(path: Path, max_age_seconds: int) -> bool:
    try:
        return path.is_file() and time.time() - path.stat().st_mtime <= max_age_seconds
    except OSError:
        return False

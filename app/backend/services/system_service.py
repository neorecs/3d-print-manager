import os
import time
from datetime import datetime, timezone
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
    upload_root = Path(os.getenv("UPLOAD_STORAGE_PATH", "uploads"))
    upload_storage_writable = upload_root.exists() and os.access(upload_root, os.W_OK)
    upload_backup_configured = os.getenv("UPLOAD_BACKUP_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    backup_status_dir = Path(os.getenv("BACKUP_STATUS_DIR", "/backup-status/status"))
    backup_max_age_seconds = max(int(os.getenv("BACKUP_MAX_AGE_HOURS", "48")), 1) * 3600
    database_backup_recent = _marker_is_recent(backup_status_dir / "postgres-last-success", backup_max_age_seconds)
    upload_backup_recent = _marker_is_recent(backup_status_dir / "uploads-last-success", backup_max_age_seconds)
    restore_test_recent = _marker_is_recent(backup_status_dir / "restore-test-last-success", 90 * 24 * 3600)
    database_backup_last_success = _marker_timestamp(backup_status_dir / "postgres-last-success")
    upload_backup_last_success = _marker_timestamp(backup_status_dir / "uploads-last-success")
    restore_test_last_success = _marker_timestamp(backup_status_dir / "restore-test-last-success")
    auth_enabled = os.getenv("AUTH_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    auth_backend_login = os.getenv("AUTH_BACKEND_LOGIN", "false").strip().lower() in {"1", "true", "yes", "on"}
    connectors_live_mode = os.getenv("CONNECTORS_LIVE_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
    secure_cookie_enabled = os.getenv("AUTH_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes", "on"}
    ai_configured = bool(settings.openai_api_key)

    internal_blockers = []
    if not internal_api_configured or not session_signing_configured:
        internal_blockers.append("Interne backendauthenticatie en sessieondertekening zijn niet volledig ingesteld.")
    if not database_reachable:
        internal_blockers.append("De PostgreSQL databaseverbinding kon niet worden bevestigd.")
    if not upload_storage_writable:
        internal_blockers.append("De opslag voor foto's, documenten en printbestanden is niet schrijfbaar.")
    if not auth_enabled or not auth_backend_login:
        internal_blockers.append("Login met databasegebruikers is niet volledig actief.")

    data_protection_blockers = []
    if not encryption_configured:
        data_protection_blockers.append("Stel CREDENTIAL_ENCRYPTION_KEY in voordat echte platformtokens worden opgeslagen.")
    if not upload_backup_configured or not upload_backup_recent:
        data_protection_blockers.append("Er is geen recente geslaagde backup van foto's, documenten en printbestanden bevestigd.")
    if not database_backup_recent:
        data_protection_blockers.append("Er is geen recente geslaagde PostgreSQL-backup bevestigd.")
    if not restore_test_recent:
        data_protection_blockers.append("Er is de afgelopen 90 dagen geen gezamenlijke hersteltest van database en bestanden bevestigd.")

    internal_blockers = list(dict.fromkeys(
        internal_blockers
        + [blocker for blocker in data_protection_blockers if "CREDENTIAL_ENCRYPTION_KEY" not in blocker]
    ))
    platform_blockers = list(dict.fromkeys(internal_blockers + data_protection_blockers))

    external_access_blockers = []
    if not secure_cookie_enabled:
        external_access_blockers.append("Internettoegang is uitgesteld. Gebruik eerst een domein, HTTPS en secure cookies voordat de site buiten het lokale netwerk bereikbaar wordt.")

    internal_use_ready = not internal_blockers
    ready_for_real_tokens = not platform_blockers

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
        "database_backup_last_success": database_backup_last_success,
        "upload_backup_last_success": upload_backup_last_success,
        "restore_test_last_success": restore_test_last_success,
        "auth_enabled": auth_enabled,
        "auth_backend_login": auth_backend_login,
        "secure_cookie_enabled": secure_cookie_enabled,
        "ai_enabled": settings.ai_openai_enabled,
        "ai_configured": ai_configured,
        "openai_model": settings.openai_product_model,
        "platform_subscription_required_now": False,
        "safe_without_platform_subscription": not connectors_live_mode,
        "backup_plan_documented": True,
        "internal_use_ready": internal_use_ready,
        "ready_for_real_tokens": ready_for_real_tokens,
        "external_access_ready": not external_access_blockers and not internal_blockers,
        "internal_blockers": internal_blockers,
        "platform_blockers": platform_blockers,
        "external_access_blockers": external_access_blockers,
        "blockers": platform_blockers,
        "next_checks": [
            "Controleer de getoonde datum van de laatste databasebackup, bestandsbackup en gezamenlijke hersteltest.",
            "Laat CONNECTORS_LIVE_MODE uit totdat een afzonderlijke Etsy- of Shopify-proef bewust wordt gestart.",
            "Voeg platformtokens alleen via de app toe en gebruik de site via het vertrouwde lokale netwerk zolang HTTPS is uitgesteld.",
            "Test per verkoopkanaal eerst lezen/importeren en daarna pas publiceren of synchroniseren.",
        ],
    }


def _marker_is_recent(path: Path, max_age_seconds: int) -> bool:
    timestamp = _marker_epoch(path)
    if timestamp is None:
        return False
    age = time.time() - timestamp
    return -300 <= age <= max_age_seconds


def _marker_timestamp(path: Path) -> str | None:
    timestamp = _marker_epoch(path)
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _marker_epoch(path: Path) -> float | None:
    try:
        if not path.is_file():
            return None
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        return path.stat().st_mtime
    except (OSError, ValueError):
        return None

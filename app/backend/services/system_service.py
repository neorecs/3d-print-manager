import os

from core.config import get_settings


def system_readiness_payload() -> dict:
    settings = get_settings()
    encryption_configured = bool(os.getenv("CREDENTIAL_ENCRYPTION_KEY"))
    database_configured = bool(settings.database_url)
    connectors_live_mode = os.getenv("CONNECTORS_LIVE_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
    ai_configured = bool(settings.openai_api_key)

    blockers = []
    if not encryption_configured:
        blockers.append("Stel CREDENTIAL_ENCRYPTION_KEY in voordat echte tokens worden opgeslagen.")
    if not database_configured:
        blockers.append("Stel DATABASE_URL in voor PostgreSQL.")
    if connectors_live_mode:
        blockers.append("CONNECTORS_LIVE_MODE staat aan. Zet deze uit zolang je alleen veilig wilt voorbereiden.")

    return {
        "connectors_live_mode": connectors_live_mode,
        "live_calls_blocked": not connectors_live_mode,
        "credential_encryption_configured": encryption_configured,
        "database_configured": database_configured,
        "ai_enabled": settings.ai_openai_enabled,
        "ai_configured": ai_configured,
        "openai_model": settings.openai_product_model,
        "platform_subscription_required_now": False,
        "safe_without_platform_subscription": not connectors_live_mode,
        "backup_plan_documented": True,
        "ready_for_real_tokens": encryption_configured and database_configured and not connectors_live_mode,
        "blockers": blockers,
        "next_checks": [
            "Controleer of de postgres_backup container dagelijks een .dump en .sha256 bestand maakt.",
            "Laat CONNECTORS_LIVE_MODE uit totdat de Etsy/Shopify OAuth-flow bewust getest wordt.",
            "Voeg platformtokens pas toe via de app nadat de juiste callback-URL bekend is.",
            "Test eerst lezen/importeren met een beperkt platformaccount voordat je publicatie of sync activeert.",
        ],
    }

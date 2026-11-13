"""Import orders from one sales channel; shared by the import buttons and the worker.

Without an explicit start date the import continues where the last successful
import of that channel started (minus one hour overlap, so nothing slips through
between runs). A channel that was never imported starts 30 days back. Re-importing
an order is harmless: orders are matched on their external id.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from connectors.factory import get_platform_connector
from models import Platform, PlatformImportLog
from services.order_import_service import upsert_imported_order

IMPORT_OVERLAP = timedelta(hours=1)
FIRST_IMPORT_WINDOW = timedelta(days=30)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def default_since(db: Session, platform: Platform, now: datetime | None = None) -> datetime:
    last_success = db.scalar(
        select(PlatformImportLog)
        .where(
            PlatformImportLog.platform_id == platform.id,
            PlatformImportLog.import_type == "orders",
            PlatformImportLog.status == "klaar",
            PlatformImportLog.started_at.is_not(None),
        )
        .order_by(PlatformImportLog.started_at.desc(), PlatformImportLog.id.desc())
        .limit(1)
    )
    if last_success is not None:
        return _aware(last_success.started_at) - IMPORT_OVERLAP
    return (now or datetime.now(timezone.utc)) - FIRST_IMPORT_WINDOW


def finish_import_log(
    log: PlatformImportLog,
    status: str,
    created_count: int,
    updated_count: int,
    skipped_count: int,
    errors: list[str],
    message: str | None = None,
) -> None:
    log.status = status
    log.finished_at = datetime.now(timezone.utc)
    log.created_count = created_count
    log.updated_count = updated_count
    log.skipped_count = skipped_count
    log.error_count = len(errors)
    default_message = f"{created_count} nieuw, {updated_count} bijgewerkt, {skipped_count} overgeslagen"
    if errors:
        log.message = "; ".join(errors)
    elif message:
        log.message = f"{default_message}. {message}".strip()
    else:
        log.message = default_message


def import_platform_orders(
    db: Session,
    platform: Platform,
    *,
    since: datetime | None = None,
    limit: int = 100,
    page_size: int = 50,
) -> dict:
    """Import one channel. Writes an import log; the caller commits."""
    label = (platform.type or platform.name or "platform").capitalize()
    effective_since = since or default_since(db, platform)
    log = PlatformImportLog(
        platform_id=platform.id,
        import_type="orders",
        status="bezig",
        started_at=datetime.now(timezone.utc),
        since=effective_since,
    )
    db.add(log)
    db.flush()
    result_summary = {"platform_id": platform.id, "platform": platform.name, "created": [], "updated": [], "skipped": [], "errors": [], "warnings": []}

    connector = get_platform_connector(db, platform)
    if (platform.type or "").lower() == "shopify":
        status = connector.status()
        if connector.live_mode and status.missing_credentials:
            message = f"Ontbrekende Shopify credentials: {', '.join(status.missing_credentials)}"
            result_summary["errors"].append(message)
            finish_import_log(log, "fout", 0, 0, 0, [message])
            return result_summary

    kwargs = {"limit": limit, "since": effective_since.isoformat()}
    if (platform.type or "").lower() == "shopify":
        kwargs["page_size"] = page_size
    result = connector.import_orders(**kwargs)
    if not result.get("success"):
        message = result.get("message") or f"{label} import mislukt"
        result_summary["errors"].append(message)
        finish_import_log(log, "fout", 0, 0, 0, [message])
        return result_summary

    for payload in result.get("orders", []):
        imported = upsert_imported_order(db, platform, payload)
        result_summary["warnings"].extend(imported.get("warnings") or [])
        result_summary.setdefault(imported["action"], []).append(imported["order"])

    message = result.get("message") or ""
    if result_summary["warnings"]:
        message = f"{message} Controle nodig: {'; '.join(result_summary['warnings'])}"
    if result.get("has_next_page") or len(result.get("orders", [])) >= limit:
        message = f"{message} Importlimiet bereikt; er zijn mogelijk nog meer orders."
    finish_import_log(
        log, "klaar",
        len(result_summary["created"]), len(result_summary["updated"]), len(result_summary["skipped"]),
        [], message,
    )
    return result_summary

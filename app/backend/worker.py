"""Background worker: imports orders from every sales channel and sends notifications.

    python worker.py          # run every WORKER_INTERVAL_SECONDS (default 300)
    python worker.py --once   # one round, for testing

Only one worker runs at a time (PostgreSQL advisory lock). Imports only run when
CONNECTORS_LIVE_MODE is on; failed notifications are retried every round.
"""

import argparse
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from connectors.factory import connector_live_mode
from database import SessionLocal, engine
from models import Order, Platform
from services.notification_service import notify, notify_new_order, retry_failed_notifications
from services.order_import_runner import import_platform_orders
from services.order_processing import process_order
from services.platform_service import sync_platform_inventory_payload

logger = logging.getLogger("worker")
IMPORTABLE_PLATFORM_TYPES = ("etsy", "shopify")
ADVISORY_LOCK_ID = 727001


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def run_once(db: Session) -> dict:
    report = {"imported_platforms": 0, "new_orders": 0, "notifications": 0, "errors": []}
    if connector_live_mode():
        platforms = db.scalars(
            select(Platform).where(Platform.active.is_(True), Platform.type.in_(IMPORTABLE_PLATFORM_TYPES)).order_by(Platform.id)
        ).all()
        for platform in platforms:
            report["imported_platforms"] += 1
            try:
                summary = import_platform_orders(db, platform)
                db.commit()
            except Exception as exc:  # noqa: BLE001 - one channel must never stop the others
                db.rollback()
                logger.exception("Import for platform %s failed", platform.id)
                summary = {"created": [], "errors": [str(exc)]}
            for message in summary["errors"]:
                report["errors"].append(f"{platform.name}: {message}")
                day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                report["notifications"] += len(notify(
                    db, "import.failed", "platform", f"{platform.id}:{day}",
                    f"Orderimport {platform.name} mislukt", message[:500],
                ))
            for created in summary["created"]:
                order = db.get(Order, created["id"])
                if order is None:
                    continue
                report["new_orders"] += 1
                if _flag("WORKER_AUTO_PROCESS_ORDERS"):
                    try:
                        process_order(db, order.id)
                    except HTTPException as exc:
                        logger.info("Order %s not processed automatically: %s", order.id, exc.detail)
                report["notifications"] += len(notify_new_order(db, order))
            if _flag("WORKER_SYNC_INVENTORY") and (platform.type or "").lower() == "shopify":
                try:
                    sync_platform_inventory_payload(db, platform)
                    db.commit()
                except Exception:  # noqa: BLE001
                    db.rollback()
                    logger.exception("Inventory sync for platform %s failed", platform.id)
    else:
        logger.info("CONNECTORS_LIVE_MODE is off; skipping order imports.")
    report["notifications"] += retry_failed_notifications(db)
    _write_heartbeat()
    return report


def _write_heartbeat() -> None:
    status_dir = os.getenv("WORKER_STATUS_DIR")
    if not status_dir:
        return
    path = Path(status_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "worker-last-run").write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")


def _acquire_lock():
    """Hold a PostgreSQL advisory lock for the lifetime of the worker; None means another worker runs."""
    if engine.dialect.name != "postgresql":
        return engine.connect()
    connection = engine.connect()
    if connection.execute(text("SELECT pg_try_advisory_lock(:id)"), {"id": ADVISORY_LOCK_ID}).scalar():
        return connection
    connection.close()
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="3D Print Manager worker")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    interval = max(int(os.getenv("WORKER_INTERVAL_SECONDS", "300")), 60)

    lock = None
    while lock is None:
        lock = _acquire_lock()
        if lock is None:
            logger.info("Another worker is active; waiting.")
            time.sleep(interval)
    try:
        while True:
            with SessionLocal() as db:
                try:
                    report = run_once(db)
                    logger.info("Round done: %s", report)
                except Exception:  # noqa: BLE001 - keep the worker alive
                    logger.exception("Worker round failed")
            if args.once:
                return
            time.sleep(interval)
    finally:
        lock.close()


if __name__ == "__main__":
    main()

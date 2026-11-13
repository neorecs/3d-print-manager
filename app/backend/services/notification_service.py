"""Push notifications to the owner's phone via Telegram and/or ntfy.

Both channels only need an outgoing HTTPS connection, so they work from a NAS
that is not reachable from the internet. Each event is stored once per channel
(unique key), so the same order never triggers two messages; failed sends are
retried by the worker a few times.
"""

import json
import logging
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Notification, Order, OrderItem, Platform, Product

logger = logging.getLogger(__name__)

MAX_SEND_ATTEMPTS = 3
STATUS_PENDING = "wachtend"
STATUS_SENT = "verstuurd"
STATUS_FAILED = "mislukt"


class NotificationError(Exception):
    pass


def configured_channels() -> list[str]:
    channels = []
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        channels.append("telegram")
    if os.getenv("NTFY_URL"):
        channels.append("ntfy")
    return channels


def public_link(path: str) -> str | None:
    base = (os.getenv("APP_PUBLIC_URL") or "").strip().rstrip("/")
    return f"{base}{path}" if base else None


def _post(request: Request) -> None:
    try:
        with urlopen(request, timeout=15) as response:
            response.read()
    except HTTPError as exc:
        raise NotificationError(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:200]}") from exc
    except (URLError, OSError) as exc:
        raise NotificationError(str(exc)) from exc


def send_telegram(title: str, body: str, link: str | None) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    text = f"{title}\n{body}" + (f"\n{link}" if link else "")
    payload = json.dumps({"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text, "disable_web_page_preview": True}).encode("utf-8")
    _post(Request(f"https://api.telegram.org/bot{quote(token, safe=':')}/sendMessage", data=payload,
                  headers={"Content-Type": "application/json"}, method="POST"))


def send_ntfy(title: str, body: str, link: str | None) -> None:
    headers = {"Title": title.encode("latin-1", errors="ignore").decode("latin-1") or "3D Print Manager", "Tags": "package"}
    if link:
        headers["Click"] = link
    if os.getenv("NTFY_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['NTFY_TOKEN']}"
    _post(Request(os.environ["NTFY_URL"], data=body.encode("utf-8"), headers=headers, method="POST"))


SENDERS = {"telegram": send_telegram, "ntfy": send_ntfy}


def _deliver(db: Session, notification: Notification) -> None:
    notification.attempts += 1
    try:
        SENDERS[notification.channel](notification.title, notification.body, notification.link)
    except (NotificationError, KeyError) as exc:
        notification.status = STATUS_FAILED
        notification.last_error = str(exc)[:500]
        logger.warning("Notification %s via %s failed: %s", notification.id, notification.channel, exc)
    else:
        notification.status = STATUS_SENT
        notification.sent_at = datetime.now(timezone.utc)
        notification.last_error = None
    db.commit()


def notify(db: Session, event_type: str, entity_type: str, entity_id: str, title: str, body: str, link: str | None = None) -> list[Notification]:
    """Record and send one event on every configured channel, at most once per channel."""
    sent = []
    for channel in configured_channels():
        notification = Notification(
            event_type=event_type, entity_type=entity_type, entity_id=str(entity_id), channel=channel,
            status=STATUS_PENDING, title=title[:255], body=body, link=link, attempts=0,
            created_at=datetime.now(timezone.utc),
        )
        exists = db.scalar(select(Notification.id).where(
            Notification.event_type == event_type, Notification.entity_type == entity_type,
            Notification.entity_id == str(entity_id), Notification.channel == channel,
        ))
        if exists:
            continue  # already recorded for this channel
        db.add(notification)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # recorded concurrently
            continue
        _deliver(db, notification)
        sent.append(notification)
    return sent


def retry_failed_notifications(db: Session) -> int:
    rows = db.scalars(
        select(Notification).where(Notification.status == STATUS_FAILED, Notification.attempts < MAX_SEND_ATTEMPTS).order_by(Notification.id)
    ).all()
    for notification in rows:
        _deliver(db, notification)
    return len(rows)


def _money(amount, currency: str | None) -> str:
    if amount is None:
        return ""
    formatted = f"{float(amount):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€ {formatted}" if (currency or "EUR") == "EUR" else f"{formatted} {currency}"


def new_order_message(db: Session, order: Order) -> tuple[str, str]:
    platform = db.get(Platform, order.platform_id)
    channel = platform.name if platform else "onbekend kanaal"
    lines = []
    unknown = 0
    for item in db.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)).all():
        product = db.get(Product, item.product_id) if item.product_id else None
        if not product:
            unknown += 1
        lines.append(f"{item.quantity_ordered}× {product.name if product else (item.sku or 'onbekend product')}")
    title = f"Nieuwe order via {channel}"
    parts = [order.internal_order_number]
    if lines:
        parts.append(", ".join(lines))
    amount = _money(order.total_amount, order.currency)
    if amount:
        parts.append(amount)
    body = " · ".join(parts)
    if unknown:
        body += f"\nLet op: {unknown} regel(s) zonder bekende SKU; koppel die in de app."
    return title, body


def notify_new_order(db: Session, order: Order) -> list[Notification]:
    title, body = new_order_message(db, order)
    return notify(db, "order.created", "order", str(order.id), title, body, public_link(f"/orders/{order.id}"))

from datetime import datetime, time, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import AIUsageLog


IMAGE_ACTION_PREFIX = "image:"


def _is_image_filter(image: bool):
    return AIUsageLog.action.like(f"{IMAGE_ACTION_PREFIX}%") if image else AIUsageLog.action.not_like(f"{IMAGE_ACTION_PREFIX}%")


def reserve_ai_request(db: Session, action: str, model: str, daily_limit: int) -> AIUsageLog:
    """Text and image requests have separate daily limits; image actions start with "image:"."""
    image = action.startswith(IMAGE_ACTION_PREFIX)
    kind = "beeld" if image else "AI"
    if daily_limit <= 0:
        raise HTTPException(status_code=403, detail=f"{kind}-bewerking is geblokkeerd omdat de daglimiet op 0 staat.")
    start_of_day = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    used_today = db.scalar(
        select(func.count()).select_from(AIUsageLog).where(
            AIUsageLog.created_at >= start_of_day,
            AIUsageLog.status.in_(["gestart", "geslaagd"]),
            _is_image_filter(image),
        )
    ) or 0
    if used_today >= daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"{kind}-daglimiet bereikt ({daily_limit} aanvragen). Probeer morgen opnieuw of verhoog de limiet bewust.",
        )
    item = AIUsageLog(action=action, model=model, status="gestart")
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def complete_ai_request(db: Session, item: AIUsageLog, usage: dict | None = None) -> None:
    usage = usage or {}
    item.status = "geslaagd"
    item.input_tokens = int(usage.get("input_tokens") or 0)
    item.output_tokens = int(usage.get("output_tokens") or 0)
    db.commit()


def fail_ai_request(db: Session, item: AIUsageLog, error: Exception) -> None:
    item.status = "mislukt"
    item.error_message = str(error)[:1000]
    db.commit()


def ai_usage_status(db: Session, daily_limit: int, image_daily_limit: int | None = None) -> dict:
    start_of_day = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    all_rows = db.scalars(select(AIUsageLog).where(AIUsageLog.created_at >= start_of_day)).all()
    rows = [row for row in all_rows if not (row.action or "").startswith(IMAGE_ACTION_PREFIX)]
    image_used = sum(1 for row in all_rows if (row.action or "").startswith(IMAGE_ACTION_PREFIX) and row.status in {"gestart", "geslaagd"})
    successful = [row for row in rows if row.status == "geslaagd"]
    active_count = sum(1 for row in rows if row.status in {"gestart", "geslaagd"})
    return {
        "daily_limit": daily_limit,
        "used_today": active_count,
        "remaining_today": max(0, daily_limit - active_count),
        "input_tokens_today": sum(row.input_tokens for row in successful),
        "output_tokens_today": sum(row.output_tokens for row in successful),
        "image_daily_limit": image_daily_limit,
        "image_used_today": image_used,
        "image_remaining_today": max(0, (image_daily_limit or 0) - image_used),
    }

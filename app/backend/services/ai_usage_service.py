from datetime import datetime, time, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import AIUsageLog


def reserve_ai_request(db: Session, action: str, model: str, daily_limit: int) -> AIUsageLog:
    if daily_limit <= 0:
        raise HTTPException(status_code=403, detail="Echte AI is geblokkeerd omdat de daglimiet op 0 staat.")
    start_of_day = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    used_today = db.scalar(
        select(func.count()).select_from(AIUsageLog).where(
            AIUsageLog.created_at >= start_of_day,
            AIUsageLog.status.in_(["gestart", "geslaagd"]),
        )
    ) or 0
    if used_today >= daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"AI-daglimiet bereikt ({daily_limit} aanvragen). Probeer morgen opnieuw of verhoog de limiet bewust.",
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


def ai_usage_status(db: Session, daily_limit: int) -> dict:
    start_of_day = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    rows = db.scalars(select(AIUsageLog).where(AIUsageLog.created_at >= start_of_day)).all()
    successful = [row for row in rows if row.status == "geslaagd"]
    active_count = sum(1 for row in rows if row.status in {"gestart", "geslaagd"})
    return {
        "daily_limit": daily_limit,
        "used_today": active_count,
        "remaining_today": max(0, daily_limit - active_count),
        "input_tokens_today": sum(row.input_tokens for row in successful),
        "output_tokens_today": sum(row.output_tokens for row in successful),
    }

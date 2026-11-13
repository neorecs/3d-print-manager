from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from services.notification_service import configured_channels, notify, public_link
from services.system_service import system_readiness_payload

router = APIRouter()


@router.get("/system/readiness")
def system_readiness(db: Session = Depends(get_db)) -> dict:
    return system_readiness_payload(db)


@router.post("/system/notifications/test")
def send_test_notification(request: Request, db: Session = Depends(get_db)):
    if getattr(request.state, "user_role", None) != "admin":
        raise HTTPException(status_code=403, detail="Alleen een beheerder kan een testmelding sturen.")
    channels = configured_channels()
    if not channels:
        raise HTTPException(status_code=409, detail="Er is nog geen meldingskanaal ingesteld (Telegram of ntfy).")
    sent = notify(
        db, "system.test", "system", datetime.now(timezone.utc).isoformat(),
        "Testmelding 3D Print Manager", "Meldingen werken. Zo krijg je straks bericht bij elke nieuwe order.",
        public_link("/instellingen"),
    )
    return {"channels": [{"channel": item.channel, "status": item.status, "error": item.last_error} for item in sent]}

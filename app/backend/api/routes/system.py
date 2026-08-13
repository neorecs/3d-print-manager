from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.system_service import system_readiness_payload

router = APIRouter()


@router.get("/system/readiness")
def system_readiness(db: Session = Depends(get_db)) -> dict:
    return system_readiness_payload(db)

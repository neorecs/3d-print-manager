from fastapi import APIRouter

from services.system_service import system_readiness_payload

router = APIRouter()


@router.get("/system/readiness")
def system_readiness() -> dict:
    return system_readiness_payload()

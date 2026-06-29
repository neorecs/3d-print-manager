from fastapi import APIRouter
from api.routes_shared import *

router = APIRouter()

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/credentials/generate-key")
def generate_credentials_key() -> dict[str, str]:
    return {"credential_encryption_key": generate_credential_key()}



@router.post("/seed")
def seed(db: Session = Depends(get_db)) -> dict[str, str]:
    seed_dummy_data(db)
    return {"status": "seeded"}



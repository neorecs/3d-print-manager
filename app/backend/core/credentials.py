import os

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException


ENCRYPTED_PREFIX = "fernet:"


def generate_credential_key() -> str:
    return Fernet.generate_key().decode("utf-8")


def get_fernet() -> Fernet:
    key = os.getenv("CREDENTIAL_ENCRYPTION_KEY")
    if not key:
        raise HTTPException(
            status_code=500,
            detail="CREDENTIAL_ENCRYPTION_KEY ontbreekt. Stel deze in voordat credentials worden opgeslagen.",
        )
    try:
        return Fernet(key.encode("utf-8"))
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="CREDENTIAL_ENCRYPTION_KEY is ongeldig.") from exc


def encrypt_credential(value: str) -> str:
    return ENCRYPTED_PREFIX + get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_credential(value: str) -> str:
    if not value.startswith(ENCRYPTED_PREFIX):
        return value
    token = value.removeprefix(ENCRYPTED_PREFIX)
    try:
        return get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="Credential kan niet worden ontsleuteld.") from exc


def is_encrypted_credential(value: str | None) -> bool:
    return bool(value and value.startswith(ENCRYPTED_PREFIX))

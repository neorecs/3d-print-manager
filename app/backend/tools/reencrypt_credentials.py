"""Re-encrypt every stored secret with a new CREDENTIAL_ENCRYPTION_KEY.

Used when rotating the encryption key. Reads the old key from
CREDENTIAL_ENCRYPTION_KEY_OLD and the new key from CREDENTIAL_ENCRYPTION_KEY.

    python tools/reencrypt_credentials.py           # dry run: only reports
    python tools/reencrypt_credentials.py --apply   # re-encrypts in one transaction

Values that are already encrypted with the new key are left alone, so the
command is safe to run more than once. Nothing is printed except counts.
"""

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ENCRYPTED_PREFIX = "fernet:"


class RotationError(Exception):
    pass


@dataclass
class RotationReport:
    reencrypted: int = 0
    encrypted_plaintext: int = 0
    already_new: int = 0
    failed: list[str] = field(default_factory=list)


def rotate_value(value: str | None, old: Fernet, new: Fernet) -> tuple[str | None, str]:
    """Return (new value, outcome). Outcome: empty, already_new, reencrypted, encrypted_plaintext."""
    if not value:
        return value, "empty"
    if not value.startswith(ENCRYPTED_PREFIX):
        return ENCRYPTED_PREFIX + new.encrypt(value.encode("utf-8")).decode("utf-8"), "encrypted_plaintext"
    token = value.removeprefix(ENCRYPTED_PREFIX).encode("utf-8")
    try:
        new.decrypt(token)
        return value, "already_new"
    except InvalidToken:
        pass
    try:
        plaintext = old.decrypt(token)
    except InvalidToken as exc:
        raise RotationError("value can be decrypted with neither the old nor the new key") from exc
    return ENCRYPTED_PREFIX + new.encrypt(plaintext).decode("utf-8"), "reencrypted"


def load_key(name: str) -> Fernet:
    key = os.getenv(name, "").strip()
    if not key:
        raise SystemExit(f"{name} ontbreekt.")
    try:
        return Fernet(key.encode("utf-8"))
    except ValueError as exc:
        raise SystemExit(f"{name} is geen geldige Fernet-sleutel.") from exc


def rotate_all(db, old: Fernet, new: Fernet) -> RotationReport:
    from sqlalchemy import select

    from models import BambuPrinter, PlatformCredential, User

    targets = [
        (PlatformCredential, "encrypted_value", "platformcredential"),
        (User, "totp_secret_encrypted", "gebruiker (MFA)"),
        (BambuPrinter, "access_code_encrypted", "printer"),
    ]
    report = RotationReport()
    for model, column, label in targets:
        for row in db.scalars(select(model).with_for_update()).all():
            try:
                updated, outcome = rotate_value(getattr(row, column), old, new)
            except RotationError:
                report.failed.append(f"{label} #{row.id}")
                continue
            if outcome == "reencrypted":
                report.reencrypted += 1
            elif outcome == "encrypted_plaintext":
                report.encrypted_plaintext += 1
            elif outcome == "already_new":
                report.already_new += 1
            if updated != getattr(row, column):
                setattr(row, column, updated)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Versleutel opgeslagen secrets opnieuw met een nieuwe CREDENTIAL_ENCRYPTION_KEY.")
    parser.add_argument("--apply", action="store_true", help="Wijzigingen echt opslaan (standaard alleen controleren).")
    args = parser.parse_args()

    old = load_key("CREDENTIAL_ENCRYPTION_KEY_OLD")
    new = load_key("CREDENTIAL_ENCRYPTION_KEY")

    from database import SessionLocal

    with SessionLocal() as db:
        report = rotate_all(db, old, new)
        print(f"Opnieuw versleuteld: {report.reencrypted}")
        print(f"Onversleuteld aangetroffen en nu versleuteld: {report.encrypted_plaintext}")
        print(f"Al met de nieuwe sleutel: {report.already_new}")
        if report.failed:
            db.rollback()
            print("Niet te ontsleutelen met oude of nieuwe sleutel: " + ", ".join(report.failed))
            raise SystemExit("Afgebroken; er is niets gewijzigd.")
        if args.apply:
            db.commit()
            print("Opgeslagen.")
        else:
            db.rollback()
            print("Controle zonder wijzigingen. Voer opnieuw uit met --apply om op te slaan.")


if __name__ == "__main__":
    main()

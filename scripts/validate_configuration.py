import argparse
import base64
from pathlib import Path
from urllib.parse import urlparse


def read_env(path: Path) -> dict[str, str]:
    values = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="Controleer het configuratiecontract van 3D Print Manager.")
    parser.add_argument("--env", default=".env")
    args = parser.parse_args()
    path = Path(args.env)
    if not path.is_file():
        raise SystemExit(f"Configuratiebestand ontbreekt: {path}")
    values = read_env(path)
    required = ["POSTGRES_PASSWORD", "DATABASE_URL", "CREDENTIAL_ENCRYPTION_KEY", "AUTH_SECRET", "BACKEND_INTERNAL_TOKEN"]
    errors = [f"{key} ontbreekt" for key in required if not values.get(key)]
    for key in ("POSTGRES_PASSWORD", "AUTH_SECRET", "BACKEND_INTERNAL_TOKEN"):
        if values.get(key) and len(values[key]) < 32:
            errors.append(f"{key} is te kort")
    database_url = values.get("DATABASE_URL", "")
    parsed = urlparse(database_url.replace("postgresql+psycopg://", "postgresql://", 1))
    if database_url and (parsed.scheme != "postgresql" or not parsed.hostname or not parsed.path.strip("/")):
        errors.append("DATABASE_URL is geen volledige PostgreSQL-URL")
    if values.get("CREDENTIAL_ENCRYPTION_KEY"):
        try:
            encryption_key = base64.urlsafe_b64decode(values["CREDENTIAL_ENCRYPTION_KEY"])
            if len(encryption_key) != 32:
                errors.append("CREDENTIAL_ENCRYPTION_KEY moet een Fernet-sleutel van 32 bytes zijn")
        except Exception:
            errors.append("CREDENTIAL_ENCRYPTION_KEY is geen geldige URL-veilige base64-sleutel")
    if values.get("AUTH_SECRET") and values.get("AUTH_SECRET") == values.get("BACKEND_INTERNAL_TOKEN"):
        errors.append("AUTH_SECRET en BACKEND_INTERNAL_TOKEN moeten verschillend zijn")
    if values.get("AUTH_ENABLED", "").lower() != "true" or values.get("AUTH_BACKEND_LOGIN", "").lower() != "true":
        errors.append("AUTH_ENABLED en AUTH_BACKEND_LOGIN moeten true zijn")
    if values.get("CONNECTORS_LIVE_MODE", "").lower() != "false":
        errors.append("CONNECTORS_LIVE_MODE moet tijdens voorbereiding false blijven")
    if errors:
        raise SystemExit("Configuratie ongeldig:\n- " + "\n- ".join(errors))
    print(f"Configuratiecontract is geldig: {path}")


if __name__ == "__main__":
    main()

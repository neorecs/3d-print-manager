import argparse
import base64
import os
import secrets
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_value(lines: list[str], key: str, value: str) -> None:
    prefix = f"{key}="
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{prefix}{value}"
            return
    lines.append(f"{prefix}{value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Maak een veilige lokale .env voor 3D Print Manager.")
    parser.add_argument("--output", default=str(ROOT / ".env"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.exists() and not args.force:
        raise SystemExit(f"{output} bestaat al. Gebruik --force alleen als je de huidige lokale configuratie bewust wilt vervangen.")
    output.parent.mkdir(parents=True, exist_ok=True)

    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    template_values = {
        key: value
        for line in lines
        if line and not line.startswith("#") and "=" in line
        for key, value in [line.split("=", 1)]
    }
    database_name = template_values.get("POSTGRES_DB") or "print_manager"
    database_user = template_values.get("POSTGRES_USER") or "print_manager"
    database_password = secrets.token_urlsafe(24)
    values = {
        "POSTGRES_PASSWORD": database_password,
        "DATABASE_URL": f"postgresql+psycopg://{database_user}:{database_password}@db:5432/{database_name}",
        "CREDENTIAL_ENCRYPTION_KEY": base64.urlsafe_b64encode(os.urandom(32)).decode(),
        "AUTH_SECRET": secrets.token_urlsafe(48),
        "BACKEND_INTERNAL_TOKEN": secrets.token_urlsafe(48),
        "AUTH_BOOTSTRAP_SECRET": secrets.token_urlsafe(32),
        "AUTH_ENABLED": "true",
        "AUTH_BACKEND_LOGIN": "true",
        "AUTH_COOKIE_SECURE": "false",
        "CONNECTORS_LIVE_MODE": "false",
        "BACKUP_TARGET_PATH": "postgres_backups",
    }
    for key, value in values.items():
        replace_value(lines, key, value)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Veilige lokale configuratie gemaakt: {output}")
    print("Live verkoopkoppelingen blijven uit. Start hierna met: docker compose up --build")


if __name__ == "__main__":
    main()

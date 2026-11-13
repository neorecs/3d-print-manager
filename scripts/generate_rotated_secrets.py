"""Print fresh values for every secret that must be rotated.

Runs on any computer with Python 3, needs no packages and writes nothing to disk.
Copy the output into Dockhand by following docs/SECRETROTATIE.md.
"""

import argparse
import base64
import os
import secrets


def generate(database_user: str, database_host: str, database_name: str) -> dict[str, str]:
    database_password = secrets.token_urlsafe(24)
    return {
        "POSTGRES_PASSWORD": database_password,
        "DATABASE_URL": f"postgresql+psycopg://{database_user}:{database_password}@{database_host}/{database_name}",
        "CREDENTIAL_ENCRYPTION_KEY": base64.urlsafe_b64encode(os.urandom(32)).decode(),
        "AUTH_SECRET": secrets.token_urlsafe(48),
        "BACKEND_INTERNAL_TOKEN": secrets.token_urlsafe(48),
        "AUTH_BOOTSTRAP_SECRET": "",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Genereer nieuwe secrets voor de secretrotatie.")
    parser.add_argument("--db-user", default="print_manager")
    parser.add_argument("--db-host", default="db:5432", help="Host en poort zoals in je huidige DATABASE_URL.")
    parser.add_argument("--db-name", default="print_manager")
    args = parser.parse_args()
    for key, value in generate(args.db_user, args.db_host, args.db_name).items():
        print(f"{key}={value}")
    print()
    print("# Zet de HUIDIGE CREDENTIAL_ENCRYPTION_KEY tijdelijk als CREDENTIAL_ENCRYPTION_KEY_OLD (stap 4 in docs/SECRETROTATIE.md).")


if __name__ == "__main__":
    main()

"""Run the isolated database and uploads recovery test."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.recovery-test.yml"
SERVICES = (
    "recovery_seed",
    "recovery_postgres_backup",
    "recovery_uploads_backup",
    "recovery_verify",
)


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), *args],
        cwd=ROOT,
        check=check,
        text=True,
    )


def main() -> int:
    try:
        for service in SERVICES:
            run("run", "--rm", service)
    except FileNotFoundError:
        print("Docker is niet gevonden. Installeer of start Docker Desktop.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"Hersteltest mislukt bij Docker-stap: {exc.cmd[-1]}", file=sys.stderr)
        return exc.returncode or 1
    finally:
        try:
            run("down", "--volumes", check=False)
        except FileNotFoundError:
            pass

    print("Gecombineerde database- en uploadshersteltest geslaagd.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

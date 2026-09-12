import subprocess
import sys


def run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    output = f"{result.stdout}{result.stderr}"
    print(output, end="")
    if result.returncode:
        summary = output[-6000:].replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::error title=PostgreSQL integration failed::{summary}")
        raise SystemExit(result.returncode)


run(["alembic", "upgrade", "head"])
run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_postgres_integration.py", "-v"])

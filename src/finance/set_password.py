"""Set or change the dashboard login password.

Usage:
    uv run python -m finance.set_password
"""

from __future__ import annotations

import getpass
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv

from finance.auth import hash_password


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def _read_env() -> list[str]:
    if not ENV_PATH.exists():
        return []
    return ENV_PATH.read_text().splitlines()


def _write_env(lines: list[str]) -> None:
    ENV_PATH.write_text("\n".join(lines) + "\n")


def _upsert(lines: list[str], key: str, value: str) -> list[str]:
    found = False
    out = []
    for ln in lines:
        if ln.startswith(f"{key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(ln)
    if not found:
        out.append(f"{key}={value}")
    return out


def main() -> int:
    load_dotenv(ENV_PATH)
    pw1 = getpass.getpass("Nové heslo: ")
    if len(pw1) < 6:
        print("Heslo musí mať aspoň 6 znakov.", file=sys.stderr)
        return 1
    pw2 = getpass.getpass("Zopakuj heslo: ")
    if pw1 != pw2:
        print("Heslá sa nezhodujú.", file=sys.stderr)
        return 1

    h = hash_password(pw1)
    lines = _read_env()
    lines = _upsert(lines, "FINANCE_PASSWORD_HASH", h)

    import os
    if not os.getenv("APP_SECRET_KEY") or os.getenv("APP_SECRET_KEY", "").startswith("generate-with"):
        new_secret = secrets.token_urlsafe(32)
        lines = _upsert(lines, "APP_SECRET_KEY", new_secret)
        print("APP_SECRET_KEY vygenerovaný a uložený.")

    _write_env(lines)
    print(f"Heslo uložené do {ENV_PATH}")
    print("Reštartuj server aby sa zmena prejavila.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

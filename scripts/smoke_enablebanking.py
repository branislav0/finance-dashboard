"""Enable Banking smoke test.

Verifies:
  1. Private key loads and signs a JWT.
  2. GET /application authenticates successfully.
  3. GET /aspsps returns bank list (filter by country if requested).

Usage: uv run python scripts/smoke_enablebanking.py [COUNTRY_CODE]
"""
from __future__ import annotations

import json
import sys

from dotenv import load_dotenv

from finance.providers.enablebanking import from_env


def main() -> int:
    load_dotenv()
    country = sys.argv[1] if len(sys.argv) > 1 else None

    client = from_env()

    print("→ GET /application")
    app = client.get_application()
    print(json.dumps(app, indent=2, ensure_ascii=False))

    print(f"\n→ GET /aspsps{f'?country={country}' if country else ''}")
    aspsps = client.list_aspsps(country=country)
    items = aspsps.get("aspsps", [])
    print(f"Found {len(items)} ASPSPs")
    for a in items:
        print(f"  - {a.get('country')} | {a.get('name')} (auth: {a.get('auth_methods', '?')})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

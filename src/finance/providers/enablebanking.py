from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import httpx
import jwt

API_BASE = "https://api.enablebanking.com"
JWT_LIFETIME_SEC = 3600


class EnableBankingClient:
    def __init__(
        self,
        application_id: str,
        private_key_path: str | Path,
        base_url: str = API_BASE,
    ) -> None:
        self.application_id = application_id
        self.private_key = Path(private_key_path).read_text()
        self.base_url = base_url.rstrip("/")

    def _jwt(self) -> str:
        now = int(time.time())
        payload = {
            "iss": "enablebanking.com",
            "aud": "api.enablebanking.com",
            "iat": now,
            "exp": now + JWT_LIFETIME_SEC,
        }
        headers = {"typ": "JWT", "kid": self.application_id}
        return jwt.encode(payload, self.private_key, algorithm="RS256", headers=headers)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._jwt()}"}

    def get_application(self) -> dict[str, Any]:
        r = httpx.get(f"{self.base_url}/application", headers=self._headers(), timeout=15)
        r.raise_for_status()
        return r.json()

    def list_aspsps(self, country: str | None = None) -> dict[str, Any]:
        params = {"country": country} if country else None
        r = httpx.get(
            f"{self.base_url}/aspsps", headers=self._headers(), params=params, timeout=15
        )
        r.raise_for_status()
        return r.json()


def from_env() -> EnableBankingClient:
    app_id = os.environ["ENABLEBANKING_APPLICATION_ID"]
    key_path = os.environ["ENABLEBANKING_PRIVATE_KEY_PATH"]
    return EnableBankingClient(application_id=app_id, private_key_path=key_path)

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import jwt

API_BASE = "https://api.enablebanking.com"
JWT_LIFETIME_SEC = 3600
DEFAULT_ACCESS_DAYS = 90


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

    def start_auth(
        self,
        aspsp_name: str,
        aspsp_country: str,
        redirect_url: str,
        state: str,
        psu_type: str = "personal",
        access_days: int = DEFAULT_ACCESS_DAYS,
    ) -> dict[str, Any]:
        valid_until = datetime.now(timezone.utc) + timedelta(days=access_days)
        body = {
            "access": {"valid_until": valid_until.isoformat(timespec="seconds").replace("+00:00", "Z")},
            "aspsp": {"name": aspsp_name, "country": aspsp_country},
            "state": state,
            "redirect_url": redirect_url,
            "psu_type": psu_type,
        }
        r = httpx.post(f"{self.base_url}/auth", headers=self._headers(), json=body, timeout=15)
        r.raise_for_status()
        return r.json()

    def create_session(self, auth_code: str) -> dict[str, Any]:
        r = httpx.post(
            f"{self.base_url}/sessions",
            headers=self._headers(),
            json={"code": auth_code},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def get_session(self, session_id: str) -> dict[str, Any]:
        r = httpx.get(
            f"{self.base_url}/sessions/{session_id}", headers=self._headers(), timeout=15
        )
        r.raise_for_status()
        return r.json()

    def list_transactions(
        self, account_id: str, date_from: str, date_to: str | None = None
    ) -> dict[str, Any]:
        params = {"date_from": date_from}
        if date_to:
            params["date_to"] = date_to
        r = httpx.get(
            f"{self.base_url}/accounts/{account_id}/transactions",
            headers=self._headers(),
            params=params,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()


def from_env() -> EnableBankingClient:
    env = os.environ.get("ENABLEBANKING_ENV", "sandbox").lower()
    prefix = "ENABLEBANKING_PRODUCTION" if env == "production" else "ENABLEBANKING_SANDBOX"
    app_id = (
        os.environ.get(f"{prefix}_APPLICATION_ID")
        or os.environ["ENABLEBANKING_APPLICATION_ID"]
    )
    key_path = (
        os.environ.get(f"{prefix}_PRIVATE_KEY_PATH")
        or os.environ["ENABLEBANKING_PRIVATE_KEY_PATH"]
    )
    return EnableBankingClient(application_id=app_id, private_key_path=key_path)

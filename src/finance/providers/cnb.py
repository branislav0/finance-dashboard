"""ČNB daily exchange rate provider.

Fetches the official daily exchange rate fixing from cnb.cz.
- Free, no auth, returns text/plain with `;` delimiter.
- Weekends/holidays return the previous business day's rates.
- Rates are expressed as: `rate` CZK per `qty` units of foreign currency.
"""
from __future__ import annotations

from datetime import date
import httpx

CNB_URL = (
    "https://www.cnb.cz/en/financial-markets/foreign-exchange-market/"
    "central-bank-exchange-rate-fixing/central-bank-exchange-rate-fixing/daily.txt"
)


class CnbError(Exception):
    pass


def fetch_daily_rates(d: date, timeout: float = 5.0) -> dict[str, tuple[int, float]]:
    """Fetch ČNB rates for a given date.

    Returns dict: currency_code -> (qty, rate_czk_per_qty_units).
    E.g. {"EUR": (1, 25.235), "USD": (1, 22.450), "JPY": (100, 14.567)}

    Raises CnbError on network/parse failure.
    """
    params = {"date": d.strftime("%d.%m.%Y")}
    try:
        r = httpx.get(CNB_URL, params=params, timeout=timeout)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise CnbError(f"ČNB fetch failed: {e}") from e

    out: dict[str, tuple[int, float]] = {}
    lines = r.text.strip().splitlines()
    # Line 0: "13.05.2026 #91", line 1: header, rest: data
    for line in lines[2:]:
        parts = line.split("|")
        if len(parts) != 5:
            continue
        try:
            qty = int(parts[2])
            code = parts[3].strip().upper()
            rate = float(parts[4].replace(",", "."))
            out[code] = (qty, rate)
        except (ValueError, IndexError):
            continue
    if not out:
        raise CnbError("ČNB response had no usable rate rows")
    return out

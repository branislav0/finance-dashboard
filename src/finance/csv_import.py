from __future__ import annotations

import csv
import hashlib
import io
import re

CSOB_CZ_HEADERS = {
    "datum zaúčtování",
    "částka",
    "měna",
    "jméno protistrany",
    "zpráva",
    "označení operace",
    "ID transakce",
}

_OP_TO_CODE = {
    "transakce platební kartou": "CCRD",
    "došlá platba": "RCDT",
    "odeslaná platba": "ICDT",
    "inkaso": "DDBT",
    "trvalý příkaz": "STDO",
    "poplatek": "FEES",
    "úrok": "INTR",
    "výběr z bankomatu": "CWDL",
}


def parse_csob_csv(content: bytes) -> tuple[dict, list[dict]]:
    """Parse a ČSOB CZ CSV export.

    Returns (account_info, transactions) where transactions are EB-shaped dicts
    ready for db.upsert_transactions.
    """
    text = content.decode("utf-8-sig")
    lines = text.splitlines()
    if not lines:
        raise ValueError("Prázdny súbor")

    account_no = ""
    m = re.search(r"Pohyby na účtu\s+(\S+)", lines[0])
    data_lines = lines[1:] if m else lines
    if m:
        account_no = m.group(1)
    data_lines = [ln for ln in data_lines if ln.strip()]

    reader = csv.DictReader(io.StringIO("\n".join(data_lines)), delimiter=";")
    fields = set(reader.fieldnames or [])
    if not CSOB_CZ_HEADERS.issubset(fields):
        missing = CSOB_CZ_HEADERS - fields
        raise ValueError(f"Neznámy formát CSV (chýbajú stĺpce: {', '.join(missing)})")

    txs: list[dict] = []
    currency = "CZK"
    for row in reader:
        amount_raw = (row.get("částka") or "").strip()
        if not amount_raw:
            continue
        amount_clean = amount_raw.replace("\xa0", "").replace(" ", "").replace(",", ".")
        try:
            amount_val = float(amount_clean)
        except ValueError:
            continue
        ccy = (row.get("měna") or "CZK").strip() or "CZK"
        currency = ccy
        settle_date_raw = (row.get("datum zaúčtování") or "").strip()
        op = (row.get("označení operace") or "").strip()
        cp_name = (row.get("jméno protistrany") or "").strip() or op or None
        raw_msg = row.get("zpráva") or ""
        msg = _clean_remittance(raw_msg)
        # For card payments, the real tx date is embedded in `zpráva` as DD.MM.YYYY.
        # Prefer it over settlement date (`datum zaúčtování`) which can lag 1-5 days.
        tx_date = _extract_tx_date(raw_msg)
        booking_date = tx_date or _date_iso(settle_date_raw)
        date_raw = settle_date_raw  # kept for ref/synth backwards-compat
        ref = (row.get("ID transakce") or "").strip()
        if not ref:
            ref = _synth_ref(date_raw, amount_raw, msg or op)
        cd = "DBIT" if amount_val < 0 else "CRDT"
        code = _OP_TO_CODE.get(op.lower(), None)

        tx = {
            "entry_reference": ref,
            "booking_date": booking_date,
            "transaction_amount": {"amount": f"{abs(amount_val):.2f}", "currency": ccy},
            "credit_debit_indicator": cd,
            "status": "BOOK",
            "remittance_information": [msg] if msg else [],
            "bank_transaction_code": {"code": code} if code else None,
        }
        if cd == "CRDT":
            tx["debtor"] = {"name": cp_name} if cp_name else {}
        else:
            tx["creditor"] = {"name": cp_name} if cp_name else {}
        txs.append(tx)

    return ({"account_no": account_no, "currency": currency}, txs)


def _clean_remittance(s: str) -> str:
    """Strip redundant 'Částka:' segments and pick shortest unique 'Místo:' merchant.

    ČSOB CSV repeats info: 'Částka: X CZK DATE Místo: MERCHANT CITY, ..., Místo: MERCHANT, CITY'.
    Amount is already in its own column; merchant city is noise. Keep just the merchant.
    """
    if not s:
        return s
    s = s.strip()
    if "Místo:" not in s:
        return s
    parts = re.findall(r"Místo:\s*([^,]+)", s)
    candidates: list[str] = []
    for p in parts:
        p = p.strip().rstrip(",").strip()
        if p and p not in candidates:
            candidates.append(p)
    if not candidates:
        return s
    return min(candidates, key=len)


def _extract_tx_date(msg: str) -> str | None:
    """Extract the real transaction date from ČSOB `zpráva` field.

    Card payments have the format: 'Částka: X CZK DD.MM.YYYY Místo: ...'.
    The DD.MM.YYYY here is the actual purchase date (vs. settlement date
    which is in `datum zaúčtování` and can lag by several days).
    """
    if not msg:
        return None
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", msg)
    if not m:
        return None
    d, mo, y = m.groups()
    return f"{y}-{mo}-{d}"


def _date_iso(date_raw: str) -> str | None:
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", date_raw)
    if not m:
        return None
    d, mo, y = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def _synth_ref(date_raw: str, amount_raw: str, descr: str) -> str:
    h = hashlib.sha1(f"{date_raw}|{amount_raw}|{descr}".encode()).hexdigest()[:16]
    return f"csv-{h}"

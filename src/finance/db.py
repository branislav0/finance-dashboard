from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  aspsp_name TEXT NOT NULL,
  aspsp_country TEXT NOT NULL,
  access_valid_until TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  iban TEXT NOT NULL,
  currency TEXT NOT NULL,
  bic_fi TEXT,
  name TEXT,
  eb_uid TEXT NOT NULL,
  session_id TEXT NOT NULL REFERENCES sessions(session_id),
  raw_json TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (iban, currency)
);

CREATE TABLE IF NOT EXISTS transactions (
  account_id INTEGER NOT NULL REFERENCES accounts(id),
  entry_reference TEXT NOT NULL,
  booking_date TEXT,
  amount TEXT NOT NULL,
  currency TEXT NOT NULL,
  credit_debit TEXT,
  counterparty_name TEXT,
  remittance_info TEXT,
  status TEXT,
  raw_json TEXT NOT NULL,
  synced_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (account_id, entry_reference)
);

CREATE INDEX IF NOT EXISTS idx_tx_account_date
  ON transactions(account_id, booking_date DESC);
"""


def _db_path() -> str:
    return os.environ.get("DATABASE_PATH", "finance.db")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    Path(_db_path()).parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)


def save_session_and_accounts(session_payload: dict) -> list[int]:
    """Persist session + its accounts. Returns list of local account ids.

    Dedups by (iban, currency). Re-connecting the same bank only updates eb_uid.
    """
    session_id = session_payload["session_id"]
    accounts = session_payload.get("accounts", [])
    ids: list[int] = []
    with connect() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO sessions
               (session_id, aspsp_name, aspsp_country, access_valid_until)
               VALUES (?, ?, ?, ?)""",
            (
                session_id,
                session_payload.get("aspsp", {}).get("name", ""),
                session_payload.get("aspsp", {}).get("country", ""),
                (session_payload.get("access") or {}).get("valid_until"),
            ),
        )
        for a in accounts:
            iban = a.get("account_id", {}).get("iban") or a["uid"]
            currency = a.get("currency", "")
            raw = json.dumps(a, ensure_ascii=False)
            existing = conn.execute(
                "SELECT id FROM accounts WHERE iban = ? AND currency = ?",
                (iban, currency),
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE accounts SET eb_uid = ?, session_id = ?, bic_fi = ?,
                       name = ?, raw_json = ?, updated_at = datetime('now')
                       WHERE id = ?""",
                    (
                        a["uid"],
                        session_id,
                        a.get("bic_fi"),
                        a.get("name") or a.get("product"),
                        raw,
                        existing["id"],
                    ),
                )
                ids.append(existing["id"])
            else:
                cur = conn.execute(
                    """INSERT INTO accounts
                       (iban, currency, bic_fi, name, eb_uid, session_id, raw_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        iban,
                        currency,
                        a.get("bic_fi"),
                        a.get("name") or a.get("product"),
                        a["uid"],
                        session_id,
                        raw,
                    ),
                )
                ids.append(cur.lastrowid)
    return ids


def get_account(account_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()


def upsert_transactions(account_id: int, transactions: list[dict]) -> tuple[int, int]:
    inserted = updated = 0
    with connect() as conn:
        for t in transactions:
            ref = t.get("entry_reference") or _synth_ref(t)
            amt = t.get("transaction_amount") or {}
            cp = (t.get("creditor") or {}).get("name") or (t.get("debtor") or {}).get("name")
            info = (t.get("remittance_information") or [None])[0]
            row = conn.execute(
                "SELECT 1 FROM transactions WHERE account_id = ? AND entry_reference = ?",
                (account_id, ref),
            ).fetchone()
            conn.execute(
                """INSERT OR REPLACE INTO transactions
                   (account_id, entry_reference, booking_date, amount, currency,
                    credit_debit, counterparty_name, remittance_info, status,
                    raw_json, synced_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (
                    account_id,
                    ref,
                    t.get("booking_date"),
                    amt.get("amount", ""),
                    amt.get("currency", ""),
                    t.get("credit_debit_indicator"),
                    cp,
                    info,
                    t.get("status"),
                    json.dumps(t, ensure_ascii=False),
                ),
            )
            if row:
                updated += 1
            else:
                inserted += 1
    return inserted, updated


def _synth_ref(t: dict) -> str:
    amt = t.get("transaction_amount") or {}
    cp = (t.get("creditor") or {}).get("name") or (t.get("debtor") or {}).get("name") or ""
    return f"{t.get('booking_date', '')}:{amt.get('amount', '')}:{cp}"


def list_accounts() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM accounts ORDER BY updated_at DESC"
        ).fetchall()


def list_transactions(account_id: int, limit: int = 200) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            """SELECT * FROM transactions
               WHERE account_id = ?
               ORDER BY booking_date DESC, entry_reference DESC
               LIMIT ?""",
            (account_id, limit),
        ).fetchall()

from __future__ import annotations

import json
import os
import re
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

CREATE TABLE IF NOT EXISTS categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
  kind TEXT NOT NULL CHECK (kind IN ('income', 'expense', 'transfer')),
  UNIQUE (name, parent_id)
);

CREATE TABLE IF NOT EXISTS category_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
  pattern TEXT NOT NULL,
  field TEXT NOT NULL CHECK (field IN ('counterparty', 'remittance', 'any')),
  priority INTEGER NOT NULL DEFAULT 100,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_rules_priority ON category_rules(priority);
"""

SEED_CATEGORIES: list[tuple[str, str, list[str]]] = [
    ("Príjem z práce", "income", []),
    ("Vedľajší príjem", "income", []),
    ("Rodina", "income", []),
    ("Iné príjmy", "income", []),
    ("Bývanie", "expense", []),
    ("Nafta / doprava", "expense", []),
    ("Supermarkety", "expense", []),
    ("Oblečenie, topánky", "expense", []),
    ("Tabak", "expense", []),
    ("Reštaurácie / fastfood", "expense", []),
    ("Subscriptions", "expense", []),
    ("Darčeky", "expense", []),
    ("Zábava (hry, kultúra)", "expense", []),
    ("Fitness a zdravie", "expense", []),
    ("Hygiena", "expense", []),
    ("Výber z bankomatu", "expense", []),
    ("Investície", "expense", ["Akcie", "Crypto"]),
    ("Interné presuny / FX", "transfer", []),
]


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
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(transactions)")}
        if "category_id" not in cols:
            conn.execute(
                "ALTER TABLE transactions ADD COLUMN category_id INTEGER "
                "REFERENCES categories(id) ON DELETE SET NULL"
            )
        if "manual_override" not in cols:
            conn.execute(
                "ALTER TABLE transactions ADD COLUMN manual_override INTEGER NOT NULL DEFAULT 0"
            )
        if "tx_type" not in cols:
            conn.execute("ALTER TABLE transactions ADD COLUMN tx_type TEXT")
        if "note" not in cols:
            conn.execute("ALTER TABLE transactions ADD COLUMN note TEXT")
        if "hidden" not in cols:
            conn.execute("ALTER TABLE transactions ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0")
    _migrate_categories_allow_transfer()
    _seed_categories_if_empty()
    _ensure_transfer_category()


def _migrate_categories_allow_transfer() -> None:
    import sqlite3 as _sq
    conn = _sq.connect(_db_path())
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='categories'"
        ).fetchone()
        if not row or "'transfer'" in row["sql"]:
            return
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.executescript(
            """
            BEGIN;
            CREATE TABLE categories_new (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              parent_id INTEGER REFERENCES categories_new(id) ON DELETE SET NULL,
              kind TEXT NOT NULL CHECK (kind IN ('income', 'expense', 'transfer')),
              UNIQUE (name, parent_id)
            );
            INSERT INTO categories_new (id, name, parent_id, kind)
              SELECT id, name, parent_id, kind FROM categories;
            DROP TABLE categories;
            ALTER TABLE categories_new RENAME TO categories;
            COMMIT;
            """
        )
        conn.execute("PRAGMA foreign_keys = ON")
    finally:
        conn.close()


def _ensure_transfer_category() -> None:
    with connect() as conn:
        exists = conn.execute(
            "SELECT id FROM categories WHERE name = ? AND parent_id IS NULL",
            ("Interné presuny / FX",),
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO categories (name, parent_id, kind) VALUES (?, NULL, 'transfer')",
                ("Interné presuny / FX",),
            )


def _seed_categories_if_empty() -> None:
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        if count:
            return
        for name, kind, children in SEED_CATEGORIES:
            cur = conn.execute(
                "INSERT INTO categories (name, parent_id, kind) VALUES (?, NULL, ?)",
                (name, kind),
            )
            parent_id = cur.lastrowid
            for child in children:
                conn.execute(
                    "INSERT INTO categories (name, parent_id, kind) VALUES (?, ?, ?)",
                    (child, parent_id, kind),
                )


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


_TX_TYPE_LABELS = {
    "CCRD": "Kartová platba",
    "RCDT": "Prijatý prevod",
    "ICDT": "Odchádzajúci prevod",
    "DDBT": "Inkaso",
    "STDO": "Trvalý príkaz",
    "MCRD": "Mobilná platba",
    "ACMT": "Bankový poplatok",
}


def _bank_tx_label(t: dict) -> str | None:
    btc = t.get("bank_transaction_code") or {}
    code = btc.get("code")
    if code in _TX_TYPE_LABELS:
        return _TX_TYPE_LABELS[code]
    desc = btc.get("description")
    if desc == "PMNT":
        return "Platba"
    return desc


def upsert_transactions(account_id: int, transactions: list[dict]) -> tuple[int, int]:
    inserted = updated = 0
    with connect() as conn:
        rules = _load_rules(conn)
        for t in transactions:
            ref = t.get("entry_reference") or _synth_ref(t)
            amt = t.get("transaction_amount") or {}
            cp = (t.get("creditor") or {}).get("name") or (t.get("debtor") or {}).get("name")
            info = (t.get("remittance_information") or [None])[0]
            existing = conn.execute(
                "SELECT category_id, manual_override, note, hidden FROM transactions "
                "WHERE account_id = ? AND entry_reference = ?",
                (account_id, ref),
            ).fetchone()
            if existing and existing["manual_override"]:
                category_id = existing["category_id"]
            else:
                category_id = _match_rules(rules, cp, info)
            tx_type = _bank_tx_label(t)
            preserved_note = existing["note"] if existing else None
            preserved_hidden = existing["hidden"] if existing else 0
            conn.execute(
                """INSERT OR REPLACE INTO transactions
                   (account_id, entry_reference, booking_date, amount, currency,
                    credit_debit, counterparty_name, remittance_info, status,
                    raw_json, synced_at, category_id, manual_override, tx_type, note, hidden)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?, ?, ?)""",
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
                    category_id,
                    1 if (existing and existing["manual_override"]) else 0,
                    tx_type,
                    preserved_note,
                    preserved_hidden,
                ),
            )
            if existing:
                updated += 1
            else:
                inserted += 1
    return inserted, updated


def _load_rules(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, category_id, pattern, field FROM category_rules "
        "ORDER BY priority ASC, id ASC"
    ).fetchall()


def _match_rules(rules, counterparty: str | None, remittance: str | None) -> int | None:
    for r in rules:
        haystack = ""
        if r["field"] == "counterparty":
            haystack = counterparty or ""
        elif r["field"] == "remittance":
            haystack = remittance or ""
        else:
            haystack = f"{counterparty or ''} {remittance or ''}"
        try:
            if re.search(r["pattern"], haystack, re.IGNORECASE):
                return r["category_id"]
        except re.error:
            continue
    return None


def recategorize_all() -> tuple[int, int]:
    """Re-run rules on all non-manually-overridden transactions. Returns (changed, skipped)."""
    changed = skipped = 0
    with connect() as conn:
        rules = _load_rules(conn)
        for t in conn.execute(
            "SELECT account_id, entry_reference, counterparty_name, remittance_info, "
            "category_id, manual_override FROM transactions"
        ).fetchall():
            if t["manual_override"]:
                skipped += 1
                continue
            new_cat = _match_rules(rules, t["counterparty_name"], t["remittance_info"])
            if new_cat != t["category_id"]:
                conn.execute(
                    "UPDATE transactions SET category_id = ? "
                    "WHERE account_id = ? AND entry_reference = ?",
                    (new_cat, t["account_id"], t["entry_reference"]),
                )
                changed += 1
    return changed, skipped


def add_rule(category_id: int, pattern: str, field: str = "any", priority: int = 100) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO category_rules (category_id, pattern, field, priority) "
            "VALUES (?, ?, ?, ?)",
            (category_id, pattern, field, priority),
        )
        return cur.lastrowid


def list_rules() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT r.id, r.pattern, r.field, r.priority, r.category_id, c.name AS category_name "
            "FROM category_rules r LEFT JOIN categories c ON c.id = r.category_id "
            "ORDER BY r.priority, r.id"
        ).fetchall()


def delete_rule(rule_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM category_rules WHERE id = ?", (rule_id,))


def generate_rules_from_manual() -> int:
    """For each counterparty that was manually assigned to exactly one category,
    create an exact-match rule on counterparty. Skip if such rule already exists."""
    added = 0
    with connect() as conn:
        existing = {
            (r["pattern"], r["field"], r["category_id"])
            for r in conn.execute(
                "SELECT pattern, field, category_id FROM category_rules"
            )
        }
        rows = conn.execute(
            """SELECT counterparty_name, category_id, COUNT(DISTINCT category_id) AS cats
               FROM transactions
               WHERE manual_override = 1
                 AND counterparty_name IS NOT NULL AND counterparty_name != ''
                 AND category_id IS NOT NULL
               GROUP BY counterparty_name
               HAVING cats = 1"""
        ).fetchall()
        for r in rows:
            pattern = "^" + re.escape(r["counterparty_name"]) + "$"
            key = (pattern, "counterparty", r["category_id"])
            if key in existing:
                continue
            conn.execute(
                "INSERT INTO category_rules (category_id, pattern, field, priority) "
                "VALUES (?, ?, 'counterparty', 100)",
                (r["category_id"], pattern),
            )
            added += 1

        rem_rows = conn.execute(
            """SELECT remittance_info, category_id, COUNT(DISTINCT category_id) AS cats
               FROM transactions
               WHERE manual_override = 1
                 AND (counterparty_name IS NULL OR counterparty_name = '')
                 AND remittance_info IS NOT NULL AND remittance_info != ''
                 AND category_id IS NOT NULL
               GROUP BY remittance_info
               HAVING cats = 1"""
        ).fetchall()
        for r in rem_rows:
            pattern = "^" + re.escape(r["remittance_info"]) + "$"
            key = (pattern, "remittance", r["category_id"])
            if key in existing:
                continue
            conn.execute(
                "INSERT INTO category_rules (category_id, pattern, field, priority) "
                "VALUES (?, ?, 'remittance', 100)",
                (r["category_id"], pattern),
            )
            added += 1
    return added


def summary_by_category(month: str | None = None) -> list[sqlite3.Row]:
    """Aggregate transactions by category.

    Args:
        month: optional "YYYY-MM" string. If provided, filters to that month
            by `booking_date` prefix. None = all-time.
    """
    where = "WHERE COALESCE(t.hidden, 0) = 0"
    params: list = []
    if month:
        where += " AND t.booking_date LIKE ?"
        params.append(f"{month}-%")
    with connect() as conn:
        return conn.execute(
            f"""SELECT
                 COALESCE(c.name, '(nezaradené)') AS category_name,
                 COALESCE(c.kind, '') AS kind,
                 t.currency,
                 t.credit_debit,
                 ROUND(SUM(CAST(t.amount AS REAL)), 2) AS total,
                 COUNT(*) AS cnt
               FROM transactions t
               LEFT JOIN categories c ON c.id = t.category_id
               {where}
               GROUP BY t.category_id, t.currency, t.credit_debit
               ORDER BY c.kind DESC, category_name, t.currency""",
            params,
        ).fetchall()


def _synth_ref(t: dict) -> str:
    amt = t.get("transaction_amount") or {}
    cp = (t.get("creditor") or {}).get("name") or (t.get("debtor") or {}).get("name") or ""
    return f"{t.get('booking_date', '')}:{amt.get('amount', '')}:{cp}"


def consent_status(warn_days: int = 14) -> list[dict]:
    """Return one entry per linked bank session — only those expiring within
    `warn_days` or already expired. Each: {aspsp, country, valid_until,
    days_left, expired}."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    out: list[dict] = []
    with connect() as conn:
        rows = conn.execute(
            "SELECT aspsp_name, aspsp_country, access_valid_until "
            "FROM sessions WHERE access_valid_until IS NOT NULL"
        ).fetchall()
    for r in rows:
        try:
            exp = datetime.fromisoformat(r["access_valid_until"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        days_left = (exp - now).total_seconds() / 86400
        if days_left > warn_days:
            continue
        out.append({
            "aspsp": r["aspsp_name"],
            "country": r["aspsp_country"],
            "valid_until": r["access_valid_until"][:10],
            "days_left": int(days_left),
            "expired": days_left < 0,
        })
    return out


def list_accounts() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM accounts ORDER BY updated_at DESC"
        ).fetchall()


def list_categories() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT id, name, parent_id, kind FROM categories "
            "ORDER BY kind DESC, COALESCE(parent_id, id), id"
        ).fetchall()


def categories_with_parent_name() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT c.id, c.name, c.kind, p.name AS parent_name "
            "FROM categories c LEFT JOIN categories p ON p.id = c.parent_id "
            "ORDER BY c.kind DESC, COALESCE(c.parent_id, c.id), c.id"
        ).fetchall()
    return [dict(r) for r in rows]


def list_uncategorized_transactions(limit: int = 200) -> list[dict]:
    """All visible (non-hidden), non-transfer-categorized, uncategorized tx across accounts."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT t.account_id, t.entry_reference, t.counterparty_name, t.remittance_info, "
            "t.amount, t.currency, t.credit_debit "
            "FROM transactions t "
            "WHERE t.category_id IS NULL AND COALESCE(t.hidden, 0) = 0 "
            "ORDER BY t.booking_date DESC, t.entry_reference DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_manual_examples(limit: int = 40) -> list[dict]:
    """Recent manually-categorized tx (used as few-shot for AI)."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT t.counterparty_name, t.remittance_info, t.category_id, c.name AS category_name "
            "FROM transactions t JOIN categories c ON c.id = t.category_id "
            "WHERE t.manual_override = 1 AND COALESCE(t.hidden, 0) = 0 "
            "ORDER BY t.synced_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_category(name: str, kind: str, parent_id: int | None = None) -> int:
    if kind not in ("income", "expense", "transfer"):
        raise ValueError(f"invalid kind: {kind}")
    name = name.strip()
    if not name:
        raise ValueError("name required")
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO categories (name, parent_id, kind) VALUES (?, ?, ?)",
            (name, parent_id, kind),
        )
        return cur.lastrowid


def rename_category(category_id: int, new_name: str) -> None:
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("name required")
    with connect() as conn:
        conn.execute("UPDATE categories SET name = ? WHERE id = ?", (new_name, category_id))


def delete_category(category_id: int) -> None:
    """Delete category. Children become roots; transactions/rules unset (FK ON DELETE SET NULL)."""
    with connect() as conn:
        conn.execute(
            "UPDATE categories SET parent_id = NULL WHERE parent_id = ?", (category_id,)
        )
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))


def list_transactions(
    account_id: int,
    limit: int = 500,
    only_uncategorized: bool = False,
    include_hidden: bool = False,
) -> list[sqlite3.Row]:
    where = "t.account_id = ?"
    if only_uncategorized:
        where += " AND t.category_id IS NULL"
    if not include_hidden:
        where += " AND COALESCE(t.hidden, 0) = 0"
    with connect() as conn:
        return conn.execute(
            f"""SELECT t.*, c.name AS category_name
               FROM transactions t
               LEFT JOIN categories c ON c.id = t.category_id
               WHERE {where}
               ORDER BY t.booking_date DESC, t.entry_reference DESC
               LIMIT ?""",
            (account_id, limit),
        ).fetchall()


def set_transaction_hidden(account_id: int, entry_reference: str, hidden: bool) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE transactions SET hidden = ? WHERE account_id = ? AND entry_reference = ?",
            (1 if hidden else 0, account_id, entry_reference),
        )


def set_transaction_category(
    account_id: int, entry_reference: str, category_id: int | None, manual: bool = True
) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE transactions SET category_id = ?, manual_override = ? "
            "WHERE account_id = ? AND entry_reference = ?",
            (category_id, 1 if manual else 0, account_id, entry_reference),
        )


def set_transaction_note(account_id: int, entry_reference: str, note: str | None) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE transactions SET note = ? WHERE account_id = ? AND entry_reference = ?",
            (note, account_id, entry_reference),
        )

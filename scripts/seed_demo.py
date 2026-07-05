"""Vygeneruje samostatnú demo databázu s mock dátami pre screenshoty/portfólio.

Nepoužíva reálne dáta. Reálnej finance.db sa nedotkne — píše len do cesty
z DATABASE_PATH (default: demo.db) a pre istotu odmietne prepísať finance.db.

Použitie:
    DATABASE_PATH=demo.db uv run python scripts/seed_demo.py

Potom appku spusti nad demo DB:
    DATABASE_PATH=demo.db uv run python -m finance.main
"""

from __future__ import annotations

import json
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

# Cesta k demo DB — nastav PRED importom finance.db (číta env za behu).
DB_PATH = os.environ.setdefault("DATABASE_PATH", "demo.db")
if Path(DB_PATH).name == "finance.db":
    sys.exit("ODMIETNUTÉ: DATABASE_PATH ukazuje na finance.db. Demo nesmie prepísať reálne dáta.")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from finance import db  # noqa: E402

random.seed(42)
TODAY = date(2026, 6, 14)


def _raw(counterparty: str, info: str, amount: str, currency: str, cd: str) -> str:
    return json.dumps(
        {
            "transaction_amount": {"amount": amount, "currency": currency},
            "credit_debit_indicator": cd,
            "remittance_information": [info] if info else [],
            ("creditor" if cd == "DBIT" else "debtor"): {"name": counterparty},
        },
        ensure_ascii=False,
    )


def main() -> None:
    db.init_db()  # postaví schému + migrácie (a nasype default kategórie)

    with db.connect() as conn:
        # vyčisti všetko – chceme len pár kategórií a mock dáta
        for tbl in ("category_rules", "transactions", "accounts", "sessions",
                    "categories", "fx_rates"):
            conn.execute(f"DELETE FROM {tbl}")

        # --- session (FK pre accounts) ---
        conn.execute(
            "INSERT INTO sessions (session_id, aspsp_name, aspsp_country) VALUES (?, ?, ?)",
            ("demo-session", "Demo Bank", "CZ"),
        )

        # --- účty: CZK (hlavný) + EUR (multi-currency ukážka) ---
        acc = {}
        for key, iban, ccy, name in [
            ("czk", "CZ0000000000000000000001", "CZK", "Bežný účet"),
            ("eur", "LT000000000000000002", "EUR", "Revolut"),
        ]:
            cur = conn.execute(
                "INSERT INTO accounts (iban, currency, bic_fi, name, eb_uid, session_id, raw_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (iban, ccy, "DEMOXXXX", name, f"demo-{key}", "demo-session", "{}"),
            )
            acc[key] = cur.lastrowid

        # --- pár kategórií ---
        cats = {}
        cat_def = [
            ("Výplata", "income"),
            ("Potraviny", "expense"),
            ("Reštaurácie", "expense"),
            ("Doprava", "expense"),
            ("Bývanie", "expense"),
            ("Zábava", "expense"),
            ("Subscriptions", "expense"),
            ("Sporenie", "expense"),          # sleduje ho sporiaci tracker
            ("Interné presuny / FX", "transfer"),
        ]
        for name, kind in cat_def:
            cur = conn.execute(
                "INSERT INTO categories (name, parent_id, kind) VALUES (?, NULL, ?)",
                (name, kind),
            )
            cats[name] = cur.lastrowid

        # rozpočty pre master plan
        for name, budget in [("Potraviny", 13000), ("Reštaurácie", 5000),
                             ("Doprava", 7000), ("Zábava", 4000)]:
            conn.execute("UPDATE categories SET monthly_budget_czk = ? WHERE id = ?",
                         (budget, cats[name]))

        # pár pravidiel (nech rules page nie je prázdna)
        for cat, pattern in [("Subscriptions", "netflix|spotify|youtube"),
                            ("Potraviny", "lidl|albert|billa|tesco|kaufland"),
                            ("Doprava", "shell|omv|mhd|dpp")]:
            conn.execute(
                "INSERT INTO category_rules (category_id, pattern, field, priority) "
                "VALUES (?, ?, 'any', 50)",
                (cats[cat], pattern),
            )

        # --- transakcie ---
        seq = 0

        def tx(account, d, amount, ccy, cd, counterparty, info, cat, tx_type):
            nonlocal seq
            seq += 1
            conn.execute(
                """INSERT INTO transactions
                   (account_id, entry_reference, booking_date, amount, currency,
                    credit_debit, counterparty_name, remittance_info, status,
                    raw_json, category_id, manual_override, tx_type, note, hidden)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'BOOK', ?, ?, 0, ?, NULL, 0)""",
                (account, f"demo-{seq:04d}", d.isoformat(), f"{amount:.2f}", ccy, cd,
                 counterparty, info, _raw(counterparty, info, f"{amount:.2f}", ccy, cd),
                 cats[cat], tx_type),
            )

        groceries = ["Lidl", "Albert", "Billa", "Tesco", "Kaufland", "Penny Market"]
        restaurants = ["Pizzeria Roma", "Sushi Bar", "Bistro Praha", "KFC", "Kebab House"]
        fuel = ["Shell", "OMV", "Benzina"]
        fun = ["Cinema City", "Steam", "Kino Lucerna", "Booking.com"]

        czk, eur = acc["czk"], acc["eur"]
        last_czk = last_eur = None

        # 6 mesiacov: január → jún 2026
        for m in range(1, 7):
            day_cap = TODAY.day - 2 if m == TODAY.month else 27

            def rday(lo, hi):
                return date(2026, m, min(random.randint(lo, hi), day_cap))

            # príjem: výplata
            tx(czk, date(2026, m, min(2, day_cap)), random.uniform(100000, 108000), "CZK",
               "CRDT", "Zamestnávateľ s.r.o.", "Mzda", "Výplata", "Prijatý prevod")
            # bývanie (trvalý príkaz)
            tx(czk, date(2026, m, min(5, day_cap)), 24000, "CZK", "DBIT",
               "Prenájom bytu", "Nájom", "Bývanie", "Trvalý príkaz")
            # sporenie (buffer) — ~66k/mes → ~400k za 6 mes → 40 % cieľa 1 000 000
            tx(czk, date(2026, m, min(3, day_cap)), random.uniform(62000, 70000),
               "CZK", "DBIT", "Sporiaci účet", "Mesačné sporenie", "Sporenie", "Trvalý príkaz")
            # subscriptions
            for svc, amt in [("Netflix", 239), ("Spotify", 169), ("YouTube Premium", 179)]:
                tx(czk, rday(8, 20), amt, "CZK", "DBIT", svc, "Predplatné",
                   "Subscriptions", "Kartová platba")
            # potraviny
            for _ in range(random.randint(6, 9)):
                tx(czk, rday(1, 27), random.uniform(350, 2600), "CZK", "DBIT",
                   random.choice(groceries), "Nákup", "Potraviny", "Kartová platba")
            # reštaurácie
            for _ in range(random.randint(3, 5)):
                tx(czk, rday(1, 27), random.uniform(400, 1400), "CZK", "DBIT",
                   random.choice(restaurants), "", "Reštaurácie", "Kartová platba")
            # doprava
            tx(czk, rday(1, 5), 750, "CZK", "DBIT", "DPP MHD", "Mesačník",
               "Doprava", "Kartová platba")
            for _ in range(random.randint(1, 2)):
                tx(czk, rday(1, 27), random.uniform(1500, 2800), "CZK", "DBIT",
                   random.choice(fuel), "Tankovanie", "Doprava", "Kartová platba")
            # zábava
            for _ in range(random.randint(1, 3)):
                tx(czk, rday(1, 27), random.uniform(600, 2200), "CZK", "DBIT",
                   random.choice(fun), "", "Zábava", "Kartová platba")

            # EUR účet – pár online nákupov
            for _ in range(random.randint(2, 4)):
                cat = random.choice(["Zábava", "Reštaurácie", "Potraviny"])
                merch = {"Zábava": "Steam", "Reštaurácie": "Uber Eats",
                         "Potraviny": "Amazon"}[cat]
                tx(eur, rday(1, 27), random.uniform(10, 90), "EUR", "DBIT",
                   merch, "Online", cat, "Kartová platba")

        # zostatky? appka berie z transakcií, netreba.
        last_czk, last_eur  # noqa

    # report
    with db.connect() as conn:
        n = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    print(f"Demo DB hotová: {DB_PATH}")
    print(f"  účty: 2 (CZK + EUR), kategórie: {len(cat_def)}, transakcie: {n}")
    print()
    print("Spusti appku nad demo DB:")
    print(f"  DATABASE_PATH={DB_PATH} uv run python -m finance.main")


if __name__ == "__main__":
    main()

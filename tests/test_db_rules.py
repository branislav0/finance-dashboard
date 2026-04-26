from __future__ import annotations

from finance import db


def _make_session_and_account(session_id: str = "S1") -> int:
    payload = {
        "session_id": session_id,
        "aspsp": {"name": "Test Bank", "country": "SK"},
        "access": {"valid_until": "2099-01-01T00:00:00Z"},
        "accounts": [
            {
                "uid": "uid-1",
                "account_id": {"iban": "SK0000000000000000000001"},
                "currency": "EUR",
                "name": "Test",
            }
        ],
    }
    ids = db.save_session_and_accounts(payload)
    return ids[0]


def _tx(ref: str, *, cp: str | None = None, info: str | None = None,
        amount: str = "10.00", code: str | None = None) -> dict:
    t: dict = {
        "entry_reference": ref,
        "booking_date": "2026-04-20",
        "transaction_amount": {"amount": amount, "currency": "EUR"},
        "credit_debit_indicator": "DBIT",
    }
    if cp:
        t["creditor"] = {"name": cp}
    if info:
        t["remittance_information"] = [info]
    if code:
        t["bank_transaction_code"] = {"code": code}
    return t


def test_match_counterparty_rule(tmp_db):
    acc = _make_session_and_account()
    cats = {c["name"]: c["id"] for c in db.list_categories()}
    db.add_rule(cats["Supermarkety"], "tesco", field="counterparty")
    db.upsert_transactions(acc, [_tx("r1", cp="Tesco Stores")])
    rows = db.list_transactions(acc)
    assert rows[0]["category_id"] == cats["Supermarkety"]
    assert rows[0]["manual_override"] == 0


def test_match_remittance_rule(tmp_db):
    acc = _make_session_and_account()
    cats = {c["name"]: c["id"] for c in db.list_categories()}
    db.add_rule(cats["Bývanie"], "najomne", field="remittance")
    db.upsert_transactions(acc, [_tx("r1", info="najomne april")])
    rows = db.list_transactions(acc)
    assert rows[0]["category_id"] == cats["Bývanie"]


def test_priority_lower_wins(tmp_db):
    acc = _make_session_and_account()
    cats = {c["name"]: c["id"] for c in db.list_categories()}
    db.add_rule(cats["Supermarkety"], "shop", field="any", priority=200)
    db.add_rule(cats["Bývanie"], "shop", field="any", priority=50)
    db.upsert_transactions(acc, [_tx("r1", cp="Shop XYZ")])
    rows = db.list_transactions(acc)
    assert rows[0]["category_id"] == cats["Bývanie"]


def test_invalid_regex_skipped(tmp_db):
    acc = _make_session_and_account()
    cats = {c["name"]: c["id"] for c in db.list_categories()}
    db.add_rule(cats["Supermarkety"], "[invalid(", field="any")
    db.add_rule(cats["Bývanie"], "rent", field="any")
    db.upsert_transactions(acc, [_tx("r1", info="monthly rent")])
    rows = db.list_transactions(acc)
    assert rows[0]["category_id"] == cats["Bývanie"]


def test_recategorize_skips_manual_override(tmp_db):
    acc = _make_session_and_account()
    cats = {c["name"]: c["id"] for c in db.list_categories()}
    db.upsert_transactions(acc, [_tx("r1", cp="Tesco")])
    db.set_transaction_category(acc, "r1", cats["Darčeky"], manual=True)
    db.add_rule(cats["Supermarkety"], "tesco", field="counterparty")
    changed, skipped = db.recategorize_all()
    assert skipped == 1
    assert changed == 0
    rows = db.list_transactions(acc)
    assert rows[0]["category_id"] == cats["Darčeky"]


def test_recategorize_updates_non_manual(tmp_db):
    acc = _make_session_and_account()
    cats = {c["name"]: c["id"] for c in db.list_categories()}
    db.upsert_transactions(acc, [_tx("r1", cp="Tesco")])
    assert db.list_transactions(acc)[0]["category_id"] is None
    db.add_rule(cats["Supermarkety"], "tesco", field="counterparty")
    changed, _ = db.recategorize_all()
    assert changed == 1
    assert db.list_transactions(acc)[0]["category_id"] == cats["Supermarkety"]


def test_generate_rules_from_manual(tmp_db):
    acc = _make_session_and_account()
    cats = {c["name"]: c["id"] for c in db.list_categories()}
    db.upsert_transactions(acc, [
        _tx("r1", cp="Lidl"),
        _tx("r2", cp="Lidl"),
        _tx("r3", cp="Kaufland"),
    ])
    db.set_transaction_category(acc, "r1", cats["Supermarkety"], manual=True)
    db.set_transaction_category(acc, "r2", cats["Supermarkety"], manual=True)
    added = db.generate_rules_from_manual()
    assert added == 1
    patterns = [r["pattern"] for r in db.list_rules()]
    assert any("Lidl" in p for p in patterns)

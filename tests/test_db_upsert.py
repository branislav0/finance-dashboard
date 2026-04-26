from __future__ import annotations

from finance import db
from tests.test_db_rules import _make_session_and_account, _tx


def test_insert_then_update_counts(tmp_db):
    acc = _make_session_and_account()
    ins, upd = db.upsert_transactions(acc, [_tx("r1", cp="A"), _tx("r2", cp="B")])
    assert (ins, upd) == (2, 0)
    ins, upd = db.upsert_transactions(acc, [_tx("r1", cp="A"), _tx("r3", cp="C")])
    assert (ins, upd) == (1, 1)


def test_resync_preserves_note(tmp_db):
    acc = _make_session_and_account()
    db.upsert_transactions(acc, [_tx("r1", cp="A")])
    db.set_transaction_note(acc, "r1", "moja poznámka")
    db.upsert_transactions(acc, [_tx("r1", cp="A")])
    rows = db.list_transactions(acc)
    assert rows[0]["note"] == "moja poznámka"


def test_resync_preserves_manual_category(tmp_db):
    acc = _make_session_and_account()
    cats = {c["name"]: c["id"] for c in db.list_categories()}
    db.upsert_transactions(acc, [_tx("r1", cp="A")])
    db.set_transaction_category(acc, "r1", cats["Darčeky"], manual=True)
    db.add_rule(cats["Supermarkety"], "A", field="counterparty")
    db.upsert_transactions(acc, [_tx("r1", cp="A")])
    rows = db.list_transactions(acc)
    assert rows[0]["category_id"] == cats["Darčeky"]
    assert rows[0]["manual_override"] == 1


def test_tx_type_label_from_code(tmp_db):
    acc = _make_session_and_account()
    db.upsert_transactions(acc, [
        _tx("r1", code="CCRD"),
        _tx("r2", code="RCDT"),
        _tx("r3", code="ZZZ"),
    ])
    by_ref = {r["entry_reference"]: r for r in db.list_transactions(acc)}
    assert by_ref["r1"]["tx_type"] == "Kartová platba"
    assert by_ref["r2"]["tx_type"] == "Prijatý prevod"
    assert by_ref["r3"]["tx_type"] is None


def test_synth_ref_when_missing(tmp_db):
    acc = _make_session_and_account()
    t = {
        "booking_date": "2026-04-20",
        "transaction_amount": {"amount": "5.50", "currency": "EUR"},
        "credit_debit_indicator": "DBIT",
        "creditor": {"name": "X"},
    }
    ins, _ = db.upsert_transactions(acc, [t])
    assert ins == 1
    rows = db.list_transactions(acc)
    assert "5.50" in rows[0]["entry_reference"]


def test_only_uncategorized_filter(tmp_db):
    acc = _make_session_and_account()
    cats = {c["name"]: c["id"] for c in db.list_categories()}
    db.upsert_transactions(acc, [_tx("r1", cp="A"), _tx("r2", cp="B")])
    db.set_transaction_category(acc, "r1", cats["Darčeky"], manual=True)
    rows = db.list_transactions(acc, only_uncategorized=True)
    assert len(rows) == 1
    assert rows[0]["entry_reference"] == "r2"

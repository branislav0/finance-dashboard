from __future__ import annotations

import sqlite3

import pytest

from finance import db


def test_add_root_category(tmp_db):
    cid = db.add_category("Káva", "expense")
    cats = {c["id"]: c for c in db.list_categories()}
    assert cats[cid]["name"] == "Káva"
    assert cats[cid]["kind"] == "expense"
    assert cats[cid]["parent_id"] is None


def test_add_subcategory(tmp_db):
    parent = db.add_category("Doprava", "expense")
    child = db.add_category("MHD", "expense", parent_id=parent)
    cats = {c["id"]: c for c in db.list_categories()}
    assert cats[child]["parent_id"] == parent


def test_add_rejects_blank(tmp_db):
    with pytest.raises(ValueError):
        db.add_category("   ", "expense")


def test_add_rejects_invalid_kind(tmp_db):
    with pytest.raises(ValueError):
        db.add_category("X", "bogus")


def test_add_rejects_duplicate_under_same_parent(tmp_db):
    parent = db.add_category("Doprava", "expense")
    db.add_category("MHD", "expense", parent_id=parent)
    with pytest.raises(sqlite3.IntegrityError):
        db.add_category("MHD", "expense", parent_id=parent)


def test_rename_category(tmp_db):
    cid = db.add_category("Káva", "expense")
    db.rename_category(cid, "Nápoje")
    cats = {c["id"]: c for c in db.list_categories()}
    assert cats[cid]["name"] == "Nápoje"


def test_delete_category_promotes_children(tmp_db):
    parent = db.add_category("Doprava", "expense")
    child = db.add_category("MHD", "expense", parent_id=parent)
    db.delete_category(parent)
    cats = {c["id"]: c for c in db.list_categories()}
    assert parent not in cats
    assert cats[child]["parent_id"] is None


def test_delete_category_unsets_transaction_category(tmp_db):
    from tests.test_db_rules import _make_session_and_account, _tx
    acc = _make_session_and_account()
    cid = db.add_category("Káva", "expense")
    db.upsert_transactions(acc, [_tx("r1", cp="Bistro")])
    db.set_transaction_category(acc, "r1", cid, manual=True)
    db.delete_category(cid)
    rows = db.list_transactions(acc)
    assert rows[0]["category_id"] is None

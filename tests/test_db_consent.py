from __future__ import annotations

from datetime import datetime, timedelta, timezone

from finance import db


def _add_session(sid: str, valid_until: str | None, name: str = "Bank", country: str = "SK"):
    payload = {
        "session_id": sid,
        "aspsp": {"name": name, "country": country},
        "access": {"valid_until": valid_until},
        "accounts": [],
    }
    db.save_session_and_accounts(payload)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_consent_status_skips_far_future(tmp_db):
    _add_session("s1", _iso(datetime.now(timezone.utc) + timedelta(days=60)))
    assert db.consent_status(warn_days=14) == []


def test_consent_status_warns_within_window(tmp_db):
    _add_session("s1", _iso(datetime.now(timezone.utc) + timedelta(days=5)))
    out = db.consent_status(warn_days=14)
    assert len(out) == 1
    assert out[0]["expired"] is False
    assert 0 <= out[0]["days_left"] <= 5


def test_consent_status_flags_expired(tmp_db):
    _add_session("s1", _iso(datetime.now(timezone.utc) - timedelta(days=2)))
    out = db.consent_status(warn_days=14)
    assert len(out) == 1
    assert out[0]["expired"] is True
    assert out[0]["days_left"] < 0


def test_consent_status_skips_null_and_invalid(tmp_db):
    _add_session("s1", None)
    _add_session("s2", "not-a-date")
    assert db.consent_status() == []

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
    _add_session("s1", _iso(datetime.now(UTC) + timedelta(days=60)))
    assert db.consent_status(warn_days=14) == []


def test_consent_status_warns_within_window(tmp_db):
    _add_session("s1", _iso(datetime.now(UTC) + timedelta(days=5)))
    out = db.consent_status(warn_days=14)
    assert len(out) == 1
    assert out[0]["expired"] is False
    assert 0 <= out[0]["days_left"] <= 5


def test_consent_status_flags_expired(tmp_db):
    _add_session("s1", _iso(datetime.now(UTC) - timedelta(days=2)))
    out = db.consent_status(warn_days=14)
    assert len(out) == 1
    assert out[0]["expired"] is True
    assert out[0]["days_left"] < 0


def test_consent_status_skips_null_and_invalid(tmp_db):
    _add_session("s1", None)
    _add_session("s2", "not-a-date")
    assert db.consent_status() == []


def _reconnect(sid: str, valid_until: str):
    """Save a session for the same bank+account, mimicking a token refresh."""
    payload = {
        "session_id": sid,
        "aspsp": {"name": "Bank", "country": "SK"},
        "access": {"valid_until": valid_until},
        "accounts": [
            {
                "uid": f"uid-{sid}",
                "account_id": {"iban": "SK0000000000000000000009"},
                "currency": "EUR",
                "name": "Účet",
            }
        ],
    }
    db.save_session_and_accounts(payload)


def _session_count() -> int:
    with db.connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]


def test_reconnect_prunes_superseded_session(tmp_db):
    # Old consent expiring soon → would raise an alert.
    _reconnect("old", _iso(datetime.now(UTC) + timedelta(days=3)))
    assert _session_count() == 1
    assert len(db.consent_status(warn_days=14)) == 1

    # Refreshing the token re-points the account to a fresh, far-future session.
    _reconnect("new", _iso(datetime.now(UTC) + timedelta(days=90)))

    # The stale session is gone and the alert clears.
    assert _session_count() == 1
    assert db.consent_status(warn_days=14) == []


def test_account_less_session_is_kept(tmp_db):
    # A freshly linked consent with no accounts yet must survive.
    _add_session("s1", _iso(datetime.now(UTC) + timedelta(days=5)))
    assert _session_count() == 1
    assert len(db.consent_status(warn_days=14)) == 1

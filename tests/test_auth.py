from __future__ import annotations

import time

import pytest

from finance import auth


def test_hash_and_verify_roundtrip():
    h = auth.hash_password("correct horse battery staple")
    assert h.startswith("$argon2")
    assert auth.verify_password("correct horse battery staple", h) is True


def test_verify_rejects_wrong_password():
    h = auth.hash_password("right")
    assert auth.verify_password("wrong", h) is False


def test_verify_rejects_garbage_hash():
    assert auth.verify_password("anything", "not-a-hash") is False


def test_session_token_roundtrip(auth_env):
    token = auth.create_session_token()
    assert auth.verify_session_token(token) is True


def test_session_token_rejects_empty(auth_env):
    assert auth.verify_session_token("") is False
    assert auth.verify_session_token("garbage.token.value") is False


def test_session_token_requires_secret(monkeypatch):
    monkeypatch.delenv("APP_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="APP_SECRET_KEY"):
        auth.create_session_token()


def test_session_token_rejects_tampered(auth_env):
    token = auth.create_session_token()
    tampered = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    assert auth.verify_session_token(tampered) is False


def test_session_token_expires(auth_env, monkeypatch):
    monkeypatch.setattr(auth, "SESSION_LIFETIME_DAYS", 0)
    token = auth.create_session_token()
    time.sleep(1.1)
    assert auth.verify_session_token(token) is False

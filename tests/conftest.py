from __future__ import annotations

import os
import secrets
from pathlib import Path

import pytest


@pytest.fixture
def tmp_db(tmp_path, monkeypatch) -> Path:
    """Per-test SQLite DB with schema initialized."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    from finance import db

    db.init_db()
    return db_path


@pytest.fixture
def auth_env(monkeypatch):
    """Provide a valid APP_SECRET_KEY for auth tests."""
    monkeypatch.setenv("APP_SECRET_KEY", secrets.token_urlsafe(32))
    yield

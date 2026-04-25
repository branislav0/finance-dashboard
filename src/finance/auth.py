from __future__ import annotations

import os
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_hasher = PasswordHasher()

SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "finance_session")
SESSION_LIFETIME_DAYS = int(os.getenv("SESSION_LIFETIME_DAYS", "30"))


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except (VerifyMismatchError, InvalidHashError):
        return False


def _signer() -> URLSafeTimedSerializer:
    secret = os.getenv("APP_SECRET_KEY")
    if not secret or secret.startswith("generate-with"):
        raise RuntimeError("APP_SECRET_KEY not set in .env (generate with `python -c \"import secrets; print(secrets.token_urlsafe(32))\"`)")
    return URLSafeTimedSerializer(secret, salt="finance-session-v1")


def create_session_token() -> str:
    payload = {"v": 1, "nonce": secrets.token_urlsafe(8)}
    return _signer().dumps(payload)


def verify_session_token(token: str) -> bool:
    if not token:
        return False
    try:
        _signer().loads(token, max_age=SESSION_LIFETIME_DAYS * 86400)
        return True
    except (BadSignature, SignatureExpired):
        return False


def password_hash_from_env() -> str | None:
    h = os.getenv("FINANCE_PASSWORD_HASH")
    return h if h else None

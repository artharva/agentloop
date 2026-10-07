"""Login helpers for a small web app."""

import hashlib
import hmac

MAX_ATTEMPTS = 3


def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def check_password(password: str, salt: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password, salt), expected_hash)


def is_locked_out(failed_attempts: int) -> bool:
    """An account locks once it reaches MAX_ATTEMPTS failed logins."""
    return failed_attempts > MAX_ATTEMPTS


def login(password: str, salt: str, expected_hash: str, failed_attempts: int) -> str:
    """Return 'ok', 'wrong password' or 'locked'."""
    if is_locked_out(failed_attempts):
        return "locked"
    if not check_password(password, salt, expected_hash):
        return "wrong password"
    return "ok"

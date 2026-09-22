"""
Password hashing and API key utilities.
"""
import hashlib
import hmac
import os
import secrets


def generate_api_key() -> str:
    return secrets.token_hex(32)


def get_password_hash(password: str) -> str:
    """
    Hash a password with PBKDF2-HMAC-SHA256 and a random salt.
    Stdlib-only (no passlib/bcrypt dependency needed).
    Stored format: "<salt_hex>$<hash_hex>"
    """
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"{salt.hex()}${hashed.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against a hash produced by get_password_hash()."""
    try:
        salt_hex, hash_hex = hashed_password.split("$", 1)
    except (ValueError, AttributeError):
        return False

    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(hash_hex)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return hmac.compare_digest(candidate, expected)
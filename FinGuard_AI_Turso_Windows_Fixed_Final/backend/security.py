"""Password hashing, AES-256-GCM encryption, masking, hashing, and JWT helpers."""

from __future__ import annotations

import base64
import hashlib
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.exceptions import InvalidTag
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.config import get_field_encryption_key, settings

_password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
_raw_key = get_field_encryption_key()
_aes_key = hashlib.sha256(_raw_key).digest()  # 32 bytes = AES-256
_aes = AESGCM(_aes_key)
_legacy_fernet = Fernet(_raw_key) if len(_raw_key) == 44 else None
_PREFIX = "aesgcm:v1:"
_AAD = b"FinGuardAI:v1"


def hash_password(password: str) -> str:
    """Create a salted Argon2id password hash."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password without exposing timing-sensitive comparison logic."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def password_is_strong(password: str) -> tuple[bool, str]:
    checks = [
        (len(password) >= 8, "Password must contain at least 8 characters."),
        (bool(re.search(r"[A-Z]", password)), "Include at least one uppercase letter."),
        (bool(re.search(r"[a-z]", password)), "Include at least one lowercase letter."),
        (bool(re.search(r"\d", password)), "Include at least one number."),
        (bool(re.search(r"[^A-Za-z0-9]", password)), "Include at least one special character."),
    ]
    for passed, message in checks:
        if not passed:
            return False, message
    return True, "Password strength is acceptable."


def encrypt_text(value: Optional[str]) -> Optional[str]:
    """Encrypt a string with authenticated AES-256-GCM encryption.

    A fresh 96-bit nonce is generated for every value, so identical plaintexts
    produce different ciphertexts. Integrity is verified during decryption.
    """
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    nonce = os.urandom(12)
    ciphertext = _aes.encrypt(nonce, normalized.encode("utf-8"), _AAD)
    return _PREFIX + base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_text(value: Optional[str]) -> Optional[str]:
    """Decrypt AES-GCM data and retain legacy Fernet read compatibility."""
    if not value:
        return None
    try:
        if value.startswith(_PREFIX):
            payload = base64.urlsafe_b64decode(value[len(_PREFIX) :].encode("ascii"))
            if len(payload) < 29:  # 12-byte nonce + at least 1 byte + 16-byte tag
                return None
            nonce, ciphertext = payload[:12], payload[12:]
            return _aes.decrypt(nonce, ciphertext, _AAD).decode("utf-8")
        if _legacy_fernet:
            return _legacy_fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidTag, InvalidToken, ValueError, TypeError, UnicodeDecodeError):
        return None
    return None


def deterministic_hash(value: str) -> str:
    """Create a peppered non-reversible hash for matching and de-duplication."""
    normalized = str(value).strip().lower()
    payload = f"{settings.hash_pepper}|{normalized}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def create_access_token(user_id: int, role: str, expires_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    minutes = expires_minutes or settings.access_token_minutes
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=minutes),
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iss": "finguard-ai",
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=["HS256"],
        issuer="finguard-ai",
        options={"require": ["exp", "iat", "sub", "type"]},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Unsupported token type")
    return payload


def mask_account_number(value: Optional[str]) -> str:
    if not value:
        return "Not provided"
    cleaned = re.sub(r"\s+", "", value)
    return "•" * len(cleaned) if len(cleaned) <= 4 else f"{'•' * max(4, len(cleaned) - 4)}{cleaned[-4:]}"


def mask_transaction_id(value: Optional[str]) -> str:
    if not value:
        return "—"
    return "•" * len(value) if len(value) <= 6 else f"{value[:3]}{'•' * (len(value) - 6)}{value[-3:]}"


def mask_email(email: str) -> str:
    if "@" not in email:
        return "hidden"
    name, domain = email.split("@", 1)
    visible = name[:2] if len(name) >= 2 else name[:1]
    return f"{visible}{'•' * max(2, len(name) - len(visible))}@{domain}"


def mask_phone(value: Optional[str]) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) < 4:
        return "Not provided"
    return f"{'•' * max(4, len(digits) - 4)}{digits[-4:]}"


def mask_ifsc(value: Optional[str]) -> str:
    text = (value or "").upper()
    if len(text) < 7:
        return "Not provided"
    return f"{text[:4]}••••{text[-3:]}"


def mask_pan(value: Optional[str]) -> str:
    text = (value or "").upper()
    if len(text) != 10:
        return "Not provided"
    return f"{text[:2]}•••••{text[-3:]}"

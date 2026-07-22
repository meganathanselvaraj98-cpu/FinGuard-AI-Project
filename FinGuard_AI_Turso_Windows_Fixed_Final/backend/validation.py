"""Reusable validation and normalization helpers."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from backend.exceptions import ValidationError

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
_PHONE_RE = re.compile(r"^[6-9][0-9]{9}$")
_ACCOUNT_RE = re.compile(r"^[0-9]{6,20}$")


def validate_email(value: str) -> str:
    email = value.strip().lower()
    if not _EMAIL_RE.fullmatch(email):
        raise ValidationError("Enter a valid email address.")
    return email


def validate_full_name(value: str) -> str:
    name = " ".join(value.strip().split())
    if len(name) < 3 or len(name) > 120:
        raise ValidationError("Full name must contain 3 to 120 characters.")
    return name


def validate_phone(value: str, required: bool = False) -> str:
    cleaned = re.sub(r"\D", "", value or "")
    if not cleaned and not required:
        return ""
    if not _PHONE_RE.fullmatch(cleaned):
        raise ValidationError("Enter a valid 10-digit Indian mobile number.")
    return cleaned


def validate_pan(value: str) -> str:
    pan = (value or "").strip().upper()
    if pan and not _PAN_RE.fullmatch(pan):
        raise ValidationError("PAN must follow the format ABCDE1234F.")
    return pan


def validate_ifsc(value: str) -> str:
    ifsc = re.sub(r"\s+", "", value or "").upper()
    if not _IFSC_RE.fullmatch(ifsc):
        raise ValidationError("Enter a valid 11-character IFSC code, for example SBIN0001234.")
    return ifsc


def validate_account_number(value: str) -> str:
    account = re.sub(r"\D", "", value or "")
    if not _ACCOUNT_RE.fullmatch(account):
        raise ValidationError("Account number must contain 6 to 20 digits.")
    return account


def validate_date_text(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    try:
        parsed = date.fromisoformat(text)
    except ValueError as error:
        raise ValidationError("Date must use YYYY-MM-DD format.") from error
    if parsed > date.today():
        raise ValidationError("Date of birth cannot be in the future.")
    return text


def normalize_amount(value: object, *, allow_zero: bool = False) -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError) as error:
        raise ValidationError("Enter a valid amount.") from error
    if amount < 0 or (amount == 0 and not allow_zero):
        raise ValidationError("Amount must be greater than zero.")
    return amount


def normalize_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError as error:
        raise ValidationError("Transaction date is invalid.") from error

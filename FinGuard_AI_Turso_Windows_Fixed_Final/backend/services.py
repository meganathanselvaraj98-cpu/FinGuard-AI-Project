"""Business services for authentication, encrypted records, imports, and finance data."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.config import settings
from backend.exceptions import AuthorizationError, DuplicateRecordError, ValidationError
from backend.models import (
    AuditLog,
    BankAccount,
    Budget,
    Category,
    Prediction,
    Report,
    StatementImport,
    Transaction,
    TransactionType,
    User,
    UserProfile,
    UserPreference,
    UserRole,
    UserStatus,
)
from backend.security import (
    decrypt_text,
    deterministic_hash,
    encrypt_text,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from backend.validation import (
    normalize_amount,
    normalize_datetime,
    validate_account_number,
    validate_date_text,
    validate_email,
    validate_full_name,
    validate_ifsc,
    validate_pan,
    validate_phone,
)


DEFAULT_CATEGORIES = {
    TransactionType.EXPENSE: [
        ("Food & Dining", "🍽️"),
        ("Groceries", "🛒"),
        ("Transport", "🚕"),
        ("Housing", "🏠"),
        ("Rent", "🏡"),
        ("Utilities", "💡"),
        ("Healthcare", "🏥"),
        ("Education", "🎓"),
        ("Entertainment", "🎬"),
        ("Shopping", "🛍️"),
        ("Subscriptions", "🔁"),
        ("EMI & Debt", "💳"),
        ("Insurance", "🛡️"),
        ("Investment", "📈"),
        ("Household", "🧹"),
        ("Other Expense", "📌"),
    ],
    TransactionType.INCOME: [
        ("Salary", "💼"),
        ("Freelance", "🧑‍💻"),
        ("Business", "🏢"),
        ("Interest", "🏦"),
        ("Refund", "↩️"),
        ("Investment Return", "📊"),
        ("Other Income", "💰"),
    ],
    TransactionType.TRANSFER: [("Internal Transfer", "🔄")],
}


def log_audit(
    session: Session,
    action: str,
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist a privacy-aware audit event.

    Never place full account numbers, IFSC codes, PAN values, passwords, or
    decrypted transaction references in ``details``.
    """
    session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=(user_agent or "")[:255] or None,
            details_json=json.dumps(details or {}, default=str),
        )
    )


def seed_default_categories(session: Session) -> None:
    existing = {
        (item.name, item.category_type)
        for item in session.scalars(select(Category)).all()
    }
    for category_type, values in DEFAULT_CATEGORIES.items():
        for name, icon in values:
            if (name, category_type) not in existing:
                session.add(Category(name=name, category_type=category_type, icon=icon))


def seed_admin_from_environment(session: Session) -> None:
    if not settings.admin_email or not settings.admin_password:
        return
    email = validate_email(settings.admin_email)
    if session.scalar(select(User).where(User.email == email)):
        return
    session.add(
        User(
            full_name="FinGuard Developer",
            email=email,
            password_hash=hash_password(settings.admin_password),
            role=UserRole.ADMIN,
        )
    )


def register_user(session: Session, full_name: str, email: str, password: str) -> User:
    normalized_email = validate_email(email)
    normalized_name = validate_full_name(full_name)
    if session.scalar(select(User).where(User.email == normalized_email)):
        raise DuplicateRecordError("An account already exists with this email.")

    total_users = session.scalar(select(func.count(User.id))) or 0
    role = UserRole.ADMIN if total_users == 0 and not settings.admin_email and settings.local_only else UserRole.USER
    user = User(
        full_name=normalized_name,
        email=normalized_email,
        password_hash=hash_password(password),
        role=role,
    )
    session.add(user)
    session.flush()
    log_audit(
        session,
        "REGISTER",
        user.id,
        "USER",
        str(user.id),
        {"role": role.value},
    )
    return user


def authenticate_user(
    session: Session,
    email: str,
    password: str,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User | None:
    normalized_email = email.strip().lower()
    user = session.scalar(select(User).where(User.email == normalized_email))
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if not user:
        log_audit(
            session,
            "LOGIN_FAILED_UNKNOWN_EMAIL",
            None,
            "USER",
            None,
            {"email_hash": deterministic_hash(normalized_email)},
            ip_address,
            user_agent,
        )
        return None

    if user.status == UserStatus.INACTIVE:
        log_audit(session, "LOGIN_BLOCKED_INACTIVE", user.id, "USER", str(user.id), None, ip_address, user_agent)
        return None

    if user.locked_until and user.locked_until > now:
        log_audit(session, "LOGIN_BLOCKED_LOCKED", user.id, "USER", str(user.id), {"locked_until": user.locked_until}, ip_address, user_agent)
        raise PermissionError("Account is temporarily locked. Try again later.")

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        details = {"attempt": user.failed_login_attempts}
        if user.failed_login_attempts >= 5:
            user.status = UserStatus.LOCKED
            user.locked_until = now + timedelta(minutes=15)
            details["locked_until"] = user.locked_until
            log_audit(session, "ACCOUNT_LOCKED", user.id, "USER", str(user.id), details, ip_address, user_agent)
        else:
            log_audit(session, "LOGIN_FAILED", user.id, "USER", str(user.id), details, ip_address, user_agent)
        return None

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    user.failed_login_attempts = 0
    user.locked_until = None
    user.status = UserStatus.ACTIVE
    user.last_login_at = now
    log_audit(session, "LOGIN_SUCCESS", user.id, "USER", str(user.id), None, ip_address, user_agent)
    return user


def save_profile(session: Session, user_id: int, data: dict[str, Any]) -> UserProfile:
    user = session.get(User, user_id)
    if not user:
        raise AuthorizationError("User account was not found.")

    normalized = {
        "phone": validate_phone(str(data.get("phone", ""))),
        "dob": validate_date_text(str(data.get("dob", ""))),
        "gender": str(data.get("gender", "")).strip(),
        "address": str(data.get("address", "")).strip()[:500],
        "city": str(data.get("city", "")).strip()[:120],
        "occupation": str(data.get("occupation", "")).strip()[:120],
        "monthly_income": str(data.get("monthly_income", "")).strip()[:40],
        "pan": validate_pan(str(data.get("pan", ""))),
    }
    profile = session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if not profile:
        profile = UserProfile(user_id=user_id)
        session.add(profile)

    mapping = {
        "phone": "phone_encrypted",
        "dob": "dob_encrypted",
        "gender": "gender_encrypted",
        "address": "address_encrypted",
        "city": "city_encrypted",
        "occupation": "occupation_encrypted",
        "monthly_income": "monthly_income_encrypted",
        "pan": "pan_encrypted",
    }
    for source_key, model_field in mapping.items():
        setattr(profile, model_field, encrypt_text(normalized[source_key]))
    session.flush()
    log_audit(session, "PROFILE_UPDATED", user_id, "USER_PROFILE", str(profile.id), {"fields": sorted(mapping)})
    return profile


def get_profile(session: Session, user_id: int) -> dict[str, str]:
    profile = session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if not profile:
        return {}
    return {
        "phone": decrypt_text(profile.phone_encrypted) or "",
        "dob": decrypt_text(profile.dob_encrypted) or "",
        "gender": decrypt_text(profile.gender_encrypted) or "",
        "address": decrypt_text(profile.address_encrypted) or "",
        "city": decrypt_text(profile.city_encrypted) or "",
        "occupation": decrypt_text(profile.occupation_encrypted) or "",
        "monthly_income": decrypt_text(profile.monthly_income_encrypted) or "",
        "pan": decrypt_text(profile.pan_encrypted) or "",
    }


def add_bank_account(session: Session, user_id: int, data: dict[str, Any]) -> BankAccount:
    if not session.get(User, user_id):
        raise AuthorizationError("User account was not found.")

    account_number = validate_account_number(str(data.get("account_number", "")))
    ifsc = validate_ifsc(str(data.get("ifsc", "")))
    bank_name = str(data.get("bank_name", "")).strip()
    holder_name = str(data.get("holder_name", "")).strip()
    if len(bank_name) < 2 or len(holder_name) < 3:
        raise ValidationError("Bank name and account-holder name are required.")

    account_hash = deterministic_hash(account_number)
    exists = session.scalar(
        select(BankAccount).where(
            BankAccount.user_id == user_id,
            BankAccount.account_number_hash == account_hash,
        )
    )
    if exists:
        raise DuplicateRecordError("This bank account is already registered.")

    if data.get("is_primary"):
        for account in session.scalars(select(BankAccount).where(BankAccount.user_id == user_id)):
            account.is_primary = False

    account = BankAccount(
        user_id=user_id,
        nickname=(str(data.get("nickname") or "Bank Account").strip()[:80]),
        bank_name_encrypted=encrypt_text(bank_name) or "",
        holder_name_encrypted=encrypt_text(holder_name) or "",
        account_number_encrypted=encrypt_text(account_number) or "",
        account_number_hash=account_hash,
        account_last4=account_number[-4:],
        ifsc_encrypted=encrypt_text(ifsc) or "",
        account_type_encrypted=encrypt_text(str(data.get("account_type", ""))),
        branch_encrypted=encrypt_text(str(data.get("branch", ""))[:160]),
        is_primary=bool(data.get("is_primary", False)),
    )
    session.add(account)
    session.flush()
    log_audit(
        session,
        "BANK_ACCOUNT_ADDED",
        user_id,
        "BANK_ACCOUNT",
        str(account.id),
        {"last4": account.account_last4, "primary": account.is_primary},
    )
    return account


def list_bank_accounts(session: Session, user_id: int, decrypt: bool = False) -> list[dict[str, Any]]:
    accounts = session.scalars(
        select(BankAccount)
        .where(BankAccount.user_id == user_id)
        .order_by(BankAccount.is_primary.desc(), BankAccount.id)
    ).all()
    result: list[dict[str, Any]] = []
    for account in accounts:
        item: dict[str, Any] = {
            "id": account.id,
            "nickname": account.nickname,
            "last4": account.account_last4,
            "is_primary": account.is_primary,
        }
        if decrypt:
            item.update(
                {
                    "bank_name": decrypt_text(account.bank_name_encrypted) or "",
                    "holder_name": decrypt_text(account.holder_name_encrypted) or "",
                    "account_number": decrypt_text(account.account_number_encrypted) or "",
                    "ifsc": decrypt_text(account.ifsc_encrypted) or "",
                    "account_type": decrypt_text(account.account_type_encrypted) or "",
                    "branch": decrypt_text(account.branch_encrypted) or "",
                }
            )
        result.append(item)
    return result


def delete_bank_account(session: Session, user_id: int, account_id: int) -> bool:
    account = session.scalar(
        select(BankAccount).where(
            BankAccount.id == account_id,
            BankAccount.user_id == user_id,
        )
    )
    if not account:
        return False
    last4 = account.account_last4
    session.delete(account)
    log_audit(session, "BANK_ACCOUNT_DELETED", user_id, "BANK_ACCOUNT", str(account_id), {"last4": last4})
    return True


def get_categories(session: Session, transaction_type: TransactionType | None = None) -> list[Category]:
    query = select(Category).where(Category.is_active.is_(True)).order_by(Category.name)
    if transaction_type:
        query = query.where(Category.category_type == transaction_type)
    return list(session.scalars(query).all())


def resolve_category(session: Session, category_name: str, transaction_type: TransactionType) -> Category:
    default_name = "Other Income" if transaction_type == TransactionType.INCOME else (
        "Internal Transfer" if transaction_type == TransactionType.TRANSFER else "Other Expense"
    )
    name = category_name.strip() or default_name
    category = session.scalar(
        select(Category).where(
            Category.name == name,
            Category.category_type == transaction_type,
        )
    )
    if category:
        return category
    category = Category(name=name[:100], category_type=transaction_type, icon="•", is_system=False)
    session.add(category)
    session.flush()
    return category


def transaction_fingerprint(
    user_id: int,
    transaction_date: datetime,
    amount: Decimal,
    description: str,
    transaction_type: str,
    transaction_id: str = "",
) -> str:
    payload = "|".join(
        [
            str(user_id),
            transaction_date.isoformat(),
            f"{Decimal(amount):.2f}",
            description.strip().lower(),
            transaction_type.upper(),
            transaction_id.strip().lower(),
        ]
    )
    return deterministic_hash(payload)


def _validate_account_owner(session: Session, user_id: int, account_id: int | None) -> None:
    if account_id is None:
        return
    account = session.scalar(
        select(BankAccount.id).where(
            BankAccount.id == int(account_id),
            BankAccount.user_id == user_id,
        )
    )
    if not account:
        raise AuthorizationError("The selected bank account does not belong to this user.")


def _build_transaction(
    session: Session,
    user_id: int,
    data: dict[str, Any],
    *,
    category_cache: dict[tuple[str, TransactionType], Category] | None = None,
    skip_duplicate_query: bool = False,
) -> Transaction:
    tx_type = TransactionType(str(data.get("transaction_type", "EXPENSE")).upper())
    tx_date = normalize_datetime(data.get("transaction_date"))
    amount = normalize_amount(data.get("amount"))
    description = str(data.get("description") or "Transaction").strip()[:500]
    transaction_id = str(data.get("transaction_id") or "").strip()[:160]
    fingerprint = transaction_fingerprint(
        user_id,
        tx_date,
        amount,
        description,
        tx_type.value,
        transaction_id,
    )
    if not skip_duplicate_query:
        existing = session.scalar(
            select(Transaction.id).where(
                Transaction.user_id == user_id,
                Transaction.fingerprint == fingerprint,
            )
        )
        if existing:
            raise DuplicateRecordError("Duplicate transaction skipped.")

    account_id = int(data["bank_account_id"]) if data.get("bank_account_id") else None
    _validate_account_owner(session, user_id, account_id)

    category_name = str(data.get("category") or "").strip()
    cache_key = (category_name, tx_type)
    if category_cache is not None and cache_key in category_cache:
        category = category_cache[cache_key]
    else:
        category = resolve_category(session, category_name, tx_type)
        if category_cache is not None:
            category_cache[cache_key] = category

    balance_value = data.get("balance_after")
    normalized_balance: Decimal | None
    try:
        if balance_value is None or str(balance_value).strip() == "" or str(balance_value).lower() == "nan":
            normalized_balance = None
        else:
            normalized_balance = Decimal(str(balance_value)).quantize(Decimal("0.01"))
    except Exception:
        normalized_balance = None

    risk_level = str(data.get("risk_level") or "LOW").upper()
    if risk_level not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        risk_level = "LOW"

    return Transaction(
        user_id=user_id,
        bank_account_id=account_id,
        statement_import_id=(int(data["statement_import_id"]) if data.get("statement_import_id") else None),
        category_id=category.id,
        transaction_id_encrypted=encrypt_text(transaction_id),
        transaction_id_hash=deterministic_hash(transaction_id) if transaction_id else None,
        transaction_date=tx_date,
        description=description,
        transaction_type=tx_type,
        amount=amount,
        balance_after=normalized_balance,
        currency_code=str(data.get("currency_code") or "INR").upper()[:3],
        payment_mode=str(data.get("payment_mode") or "")[:60],
        merchant=str(data.get("merchant") or "")[:160],
        is_recurring=bool(data.get("is_recurring", False)),
        is_unusual=bool(data.get("is_unusual", False)),
        risk_level=risk_level,
        source=str(data.get("source") or "MANUAL").upper()[:20],
        source_file_name=(str(data.get("source_file_name") or "")[:255] or None),
        fingerprint=fingerprint,
    )


def add_transaction(session: Session, user_id: int, data: dict[str, Any]) -> Transaction:
    tx = _build_transaction(session, user_id, data)
    session.add(tx)
    session.flush()
    log_audit(
        session,
        "TRANSACTION_CREATED" if tx.source == "MANUAL" else "TRANSACTION_IMPORTED",
        user_id,
        "TRANSACTION",
        str(tx.id),
        {"source": tx.source, "account_id": tx.bank_account_id},
    )
    return tx


def _statement_digest(file_name: str, raw_rows: int, records: Iterable[dict[str, Any]]) -> str:
    hasher = hashlib.sha256()
    hasher.update(file_name.encode("utf-8", errors="ignore"))
    hasher.update(str(raw_rows).encode("ascii"))
    for record in list(records)[:20]:
        hasher.update(str(record.get("transaction_date", "")).encode("utf-8"))
        hasher.update(str(record.get("amount", "")).encode("utf-8"))
        hasher.update(str(record.get("description", "")).encode("utf-8"))
    return deterministic_hash(hasher.hexdigest())


def bulk_import_transactions(
    session: Session,
    user_id: int,
    records: list[dict[str, Any]],
    *,
    bank_account_id: int | None,
    file_name: str,
    file_type: str,
    raw_rows: int,
    statement_label: str | None = None,
) -> dict[str, Any]:
    """Import a complete statement with one duplicate prefetch and one flush.

    This avoids one database round-trip per row and materially reduces loading
    time for larger CSV/Excel statements.
    """
    _validate_account_owner(session, user_id, bank_account_id)
    label = (statement_label or file_name.rsplit(".", 1)[0]).strip()[:160]
    digest = _statement_digest(file_name, raw_rows, records)

    dates = [normalize_datetime(record.get("transaction_date")) for record in records]
    statement = StatementImport(
        user_id=user_id,
        bank_account_id=bank_account_id,
        label=label or "Bank statement",
        file_name=file_name[:255],
        file_type=file_type.upper()[:20],
        statement_hash=digest,
        period_start=min(dates).date() if dates else None,
        period_end=max(dates).date() if dates else None,
        raw_rows=raw_rows,
        status="PROCESSING",
    )
    session.add(statement)
    session.flush()

    prepared: list[tuple[dict[str, Any], str]] = []
    for record in records:
        record = dict(record)
        record["bank_account_id"] = bank_account_id
        record["statement_import_id"] = statement.id
        tx_type = str(record.get("transaction_type", "EXPENSE")).upper()
        tx_date = normalize_datetime(record.get("transaction_date"))
        amount = normalize_amount(record.get("amount"))
        description = str(record.get("description") or "Transaction").strip()[:500]
        transaction_id = str(record.get("transaction_id") or "").strip()[:160]
        fingerprint = transaction_fingerprint(user_id, tx_date, amount, description, tx_type, transaction_id)
        prepared.append((record, fingerprint))

    fingerprints = [item[1] for item in prepared]
    existing: set[str] = set()
    chunk_size = 700
    for offset in range(0, len(fingerprints), chunk_size):
        chunk = fingerprints[offset : offset + chunk_size]
        if chunk:
            existing.update(
                session.scalars(
                    select(Transaction.fingerprint).where(
                        Transaction.user_id == user_id,
                        Transaction.fingerprint.in_(chunk),
                    )
                ).all()
            )

    seen = set(existing)
    category_cache: dict[tuple[str, TransactionType], Category] = {}
    imported: list[Transaction] = []
    duplicates = 0
    errors: list[str] = []
    for record, fingerprint in prepared:
        if fingerprint in seen:
            duplicates += 1
            continue
        try:
            tx = _build_transaction(
                session,
                user_id,
                record,
                category_cache=category_cache,
                skip_duplicate_query=True,
            )
            imported.append(tx)
            seen.add(fingerprint)
        except (ValueError, PermissionError) as error:
            errors.append(str(error))

    session.add_all(imported)
    session.flush()
    statement.imported_rows = len(imported)
    statement.duplicate_rows = duplicates
    statement.error_rows = len(errors)
    statement.status = "COMPLETED" if not errors else "COMPLETED_WITH_WARNINGS"
    log_audit(
        session,
        "STATEMENT_IMPORTED",
        user_id,
        "STATEMENT_IMPORT",
        str(statement.id),
        {
            "file_type": statement.file_type,
            "raw_rows": raw_rows,
            "imported_rows": len(imported),
            "duplicate_rows": duplicates,
            "error_rows": len(errors),
            "account_id": bank_account_id,
        },
    )
    return {
        "statement_id": statement.id,
        "imported": len(imported),
        "duplicates": duplicates,
        "errors": errors,
        "status": statement.status,
    }


def list_statement_imports(session: Session, user_id: int) -> list[StatementImport]:
    return list(
        session.scalars(
            select(StatementImport)
            .where(StatementImport.user_id == user_id)
            .order_by(StatementImport.created_at.desc())
        ).all()
    )


def list_transactions(session: Session, user_id: int) -> list[Transaction]:
    return list(
        session.scalars(
            select(Transaction)
            .options(
                selectinload(Transaction.category),
                selectinload(Transaction.account),
                selectinload(Transaction.statement),
            )
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        ).all()
    )


def delete_transaction(session: Session, user_id: int, transaction_id: int) -> bool:
    tx = session.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
    )
    if not tx:
        return False
    session.delete(tx)
    log_audit(session, "TRANSACTION_DELETED", user_id, "TRANSACTION", str(transaction_id))
    return True


def upsert_budget(
    session: Session,
    user_id: int,
    category_name: str,
    budget_month,
    amount: float,
    threshold: float,
) -> Budget:
    month_date = budget_month.replace(day=1)
    normalized_amount = normalize_amount(amount)
    if not 1 <= float(threshold) <= 100:
        raise ValidationError("Budget threshold must be between 1 and 100.")
    budget = session.scalar(
        select(Budget).where(
            Budget.user_id == user_id,
            Budget.category_name == category_name,
            Budget.budget_month == month_date,
        )
    )
    if not budget:
        budget = Budget(user_id=user_id, category_name=category_name, budget_month=month_date)
        session.add(budget)
    budget.allocated_amount = normalized_amount
    budget.alert_threshold_percent = float(threshold)
    session.flush()
    log_audit(session, "BUDGET_SAVED", user_id, "BUDGET", str(budget.id), {"month": month_date, "category": category_name})
    return budget


def list_budgets(session: Session, user_id: int) -> list[Budget]:
    return list(
        session.scalars(
            select(Budget)
            .where(Budget.user_id == user_id)
            .order_by(Budget.budget_month.desc(), Budget.category_name)
        ).all()
    )


def save_prediction(
    session: Session,
    user_id: int,
    prediction_type: str,
    value: float | None,
    label: str | None,
    model_name: str,
    metrics: dict[str, Any] | None = None,
) -> Prediction:
    record = Prediction(
        user_id=user_id,
        prediction_type=prediction_type,
        predicted_value=value,
        predicted_label=label,
        model_name=model_name,
        metrics_json=json.dumps(metrics or {}, default=str),
    )
    session.add(record)
    session.flush()
    log_audit(session, "PREDICTION_SAVED", user_id, "PREDICTION", str(record.id), {"type": prediction_type, "model": model_name})
    return record


def save_report_record(
    session: Session,
    user_id: int,
    report_type: str,
    report_format: str,
    file_name: str,
    file_path: str,
) -> Report:
    record = Report(
        user_id=user_id,
        report_type=report_type,
        report_format=report_format,
        file_name=file_name,
        file_path=file_path,
    )
    session.add(record)
    session.flush()
    log_audit(session, "REPORT_GENERATED", user_id, "REPORT", str(record.id), {"format": report_format, "type": report_type})
    return record


def get_user_preferences(session: Session, user_id: int) -> dict[str, Any]:
    """Return persisted UI and investment preferences for one user."""
    preference = session.scalar(select(UserPreference).where(UserPreference.user_id == user_id))
    if not preference:
        return {
            "preferred_currency": "INR",
            "default_dashboard_scope": "ALL_ACCOUNTS",
            "risk_preference": "MODERATE",
            "investment_horizon": "3-5 YEARS",
            "monthly_investment_target": 0.0,
            "alerts_enabled": True,
            "compact_tables": True,
        }
    return {
        "preferred_currency": preference.preferred_currency,
        "default_dashboard_scope": preference.default_dashboard_scope,
        "risk_preference": preference.risk_preference,
        "investment_horizon": preference.investment_horizon,
        "monthly_investment_target": float(preference.monthly_investment_target or 0),
        "alerts_enabled": preference.alerts_enabled,
        "compact_tables": preference.compact_tables,
    }


def save_user_preferences(session: Session, user_id: int, data: dict[str, Any]) -> UserPreference:
    """Create or update user preferences in SQLite."""
    if not session.get(User, user_id):
        raise AuthorizationError("User account was not found.")
    preference = session.scalar(select(UserPreference).where(UserPreference.user_id == user_id))
    if not preference:
        preference = UserPreference(user_id=user_id)
        session.add(preference)
    currency = str(data.get("preferred_currency") or "INR").upper()[:3]
    scope = str(data.get("default_dashboard_scope") or "ALL_ACCOUNTS").upper()[:40]
    risk = str(data.get("risk_preference") or "MODERATE").upper()[:20]
    horizon = str(data.get("investment_horizon") or "3-5 YEARS").upper()[:30]
    target = Decimal(str(data.get("monthly_investment_target") or 0)).quantize(Decimal("0.01"))
    if target < 0:
        raise ValidationError("Monthly investment target cannot be negative.")
    preference.preferred_currency = currency
    preference.default_dashboard_scope = scope
    preference.risk_preference = risk
    preference.investment_horizon = horizon
    preference.monthly_investment_target = target
    preference.alerts_enabled = bool(data.get("alerts_enabled", True))
    preference.compact_tables = bool(data.get("compact_tables", True))
    session.flush()
    log_audit(session, "PREFERENCES_SAVED", user_id, "USER_PREFERENCE", str(preference.id))
    return preference


def delete_user_data(session: Session, user_id: int) -> None:
    user = session.get(User, user_id)
    if user:
        log_audit(session, "ACCOUNT_DELETE_REQUESTED", user_id, "USER", str(user_id))
        session.flush()
        session.delete(user)

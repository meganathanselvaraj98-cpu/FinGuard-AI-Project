"""SQLite inspection, maintenance, export, and backup helpers.

The functions in this module never decrypt application-layer encrypted values.
They are used by the admin storage console to prove what is persisted while
keeping passwords and banking identifiers protected.
"""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import inspect, text

from backend.config import settings
from backend.database import engine

_SYSTEM_TABLE_PREFIXES = ("sqlite_",)
_SENSITIVE_COLUMNS = {
    "password_hash",
    "account_number_hash",
    "transaction_id_hash",
}


def database_path() -> Path:
    """Return the active local SQLite database file."""
    return settings.active_database_path


def list_tables() -> list[str]:
    """Return application table names in stable alphabetical order."""
    names = inspect(engine).get_table_names()
    return sorted(name for name in names if not name.startswith(_SYSTEM_TABLE_PREFIXES))


def table_columns(table_name: str) -> list[str]:
    _validate_table(table_name)
    return [column["name"] for column in inspect(engine).get_columns(table_name)]


def table_counts() -> dict[str, int]:
    """Return row counts for every application table."""
    result: dict[str, int] = {}
    with engine.connect() as connection:
        for table in list_tables():
            quoted = _quote_identifier(table)
            result[table] = int(connection.execute(text(f"SELECT COUNT(*) FROM {quoted}")).scalar_one())
    return result


def database_size_bytes() -> int:
    path = database_path()
    total = path.stat().st_size if path.exists() else 0
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(path) + suffix)
        if sidecar.exists():
            total += sidecar.stat().st_size
    return total


def pragma_value(name: str) -> Any:
    allowed = {"journal_mode", "foreign_keys", "page_count", "page_size", "freelist_count", "user_version"}
    if name not in allowed:
        raise ValueError("Unsupported SQLite PRAGMA")
    with engine.connect() as connection:
        return connection.execute(text(f"PRAGMA {name}")).scalar()


def integrity_check() -> str:
    """Run SQLite's full integrity check."""
    with engine.connect() as connection:
        return str(connection.execute(text("PRAGMA integrity_check")).scalar() or "unknown")


def checkpoint() -> None:
    """Checkpoint only when the application uses local SQLite."""

    if settings.is_turso:
        return

    with engine.connect().execution_options(
        isolation_level="AUTOCOMMIT"
    ) as connection:
        connection.exec_driver_sql(
            "PRAGMA wal_checkpoint(TRUNCATE)"
        )

def optimize_database() -> None:
    """Refresh statistics and compact the local database or replica."""
    checkpoint()
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.exec_driver_sql("PRAGMA optimize")
        if not settings.is_turso:
            connection.exec_driver_sql("VACUUM")


def read_table(
    table_name: str,
    *,
    limit: int = 500,
    offset: int = 0,
    user_id: int | None = None,
    storage_safe: bool = True,
) -> pd.DataFrame:
    """Read a bounded table preview with optional ownership filtering.

    ``storage_safe`` replaces hashes/ciphertexts with descriptive markers. This
    lets an administrator inspect table structure without copying secret values.
    """
    _validate_table(table_name)
    limit = max(1, min(int(limit), 5000))
    offset = max(0, int(offset))
    columns = table_columns(table_name)
    query = f"SELECT * FROM {_quote_identifier(table_name)}"
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if user_id is not None:
        if "user_id" in columns:
            query += " WHERE user_id = :user_id"
            params["user_id"] = int(user_id)
        elif table_name == "users" and "id" in columns:
            query += " WHERE id = :user_id"
            params["user_id"] = int(user_id)
        elif table_name == "user_profiles" and "user_id" in columns:
            query += " WHERE user_id = :user_id"
            params["user_id"] = int(user_id)
    order_column = "id" if "id" in columns else columns[0]
    query += f" ORDER BY {_quote_identifier(order_column)} DESC LIMIT :limit OFFSET :offset"
    frame = pd.read_sql_query(text(query), engine, params=params)
    return _sanitize_frame(frame, storage_safe=storage_safe)


def table_csv_bytes(table_name: str, *, user_id: int | None = None) -> bytes:
    """Export the complete privacy-safe table as CSV."""
    _validate_table(table_name)
    columns = table_columns(table_name)
    query = f"SELECT * FROM {_quote_identifier(table_name)}"
    params: dict[str, Any] = {}
    if user_id is not None:
        if "user_id" in columns:
            query += " WHERE user_id = :user_id"
            params["user_id"] = int(user_id)
        elif table_name == "users" and "id" in columns:
            query += " WHERE id = :user_id"
            params["user_id"] = int(user_id)
    frame = pd.read_sql_query(text(query), engine, params=params)
    frame = _sanitize_frame(frame, storage_safe=True)
    return frame.to_csv(index=False).encode("utf-8-sig")


def create_backup_bytes() -> tuple[bytes, str]:
    """Create a backup for local SQLite databases only."""

    if settings.is_turso:
        raise RuntimeError(
            "Direct database-file backup is unavailable in cloud mode. "
            "Use the Reports page to export your personal data."
        )

    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    checkpoint()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"finguard_backup_{stamp}.db"

    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / filename

        source_connection = sqlite3.connect(path)
        target_connection = sqlite3.connect(target)

        try:
            source_connection.backup(target_connection)
        finally:
            target_connection.close()
            source_connection.close()

        return target.read_bytes(), filename

def create_persistent_backup() -> Path:
    """Write a timestamped backup under the project's backups directory."""
    data, filename = create_backup_bytes()
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    path = settings.backup_dir / filename
    path.write_bytes(data)
    return path


def database_overview() -> dict[str, Any]:
    """Return human-readable database health and storage metadata."""
    return {
        "path": str(database_path()),
        "mode": settings.database_mode,
        "size_bytes": database_size_bytes(),
        "integrity": integrity_check(),
        "journal_mode": pragma_value("journal_mode"),
        "foreign_keys": bool(pragma_value("foreign_keys")),
        "tables": len(list_tables()),
        "rows": sum(table_counts().values()),
    }


def _sanitize_frame(frame: pd.DataFrame, *, storage_safe: bool) -> pd.DataFrame:
    """Mask hashes and optionally replace encrypted ciphertext with markers."""
    if frame.empty:
        return frame
    output = frame.copy()
    for column in output.columns:
        lower = column.lower()
        if lower in _SENSITIVE_COLUMNS or lower.endswith("_hash"):
            output[column] = output[column].apply(lambda value: "[HASHED]" if pd.notna(value) and value else None)
        elif storage_safe and lower.endswith("_encrypted"):
            output[column] = output[column].apply(
                lambda value: "[AES-256-GCM ENCRYPTED]" if pd.notna(value) and value else None
            )
    if "email" in output.columns:
        output["email"] = output["email"].astype(str).map(_mask_email)
    return output


def _validate_table(table_name: str) -> None:
    if table_name not in list_tables():
        raise ValueError("Unknown SQLite table")


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _mask_email(value: str) -> str:
    if "@" not in value:
        return value
    local, domain = value.split("@", 1)
    if len(local) <= 2:
        return f"{local[:1]}***@{domain}"
    return f"{local[:2]}***@{domain}"

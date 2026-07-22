from __future__ import annotations

import sqlite3

from backend.config import settings
from backend.database import initialize_database, session_scope
from backend.services import get_user_preferences, register_user, save_user_preferences
from backend.sqlite_manager import (
    create_backup_bytes,
    database_overview,
    integrity_check,
    list_tables,
    read_table,
    table_counts,
)


def test_project_is_sqlite_only_and_database_is_healthy():
    initialize_database()
    assert settings.database_url.startswith("sqlite:///")
    assert settings.sqlite_path.exists()
    assert integrity_check() == "ok"
    required = {
        "users",
        "user_profiles",
        "user_preferences",
        "bank_accounts",
        "statement_imports",
        "categories",
        "transactions",
        "budgets",
        "predictions",
        "reports",
        "audit_logs",
    }
    assert required.issubset(set(list_tables()))
    overview = database_overview()
    assert overview["foreign_keys"] is True
    assert str(overview["journal_mode"]).lower() == "wal"


def test_preferences_persist_and_admin_preview_masks_secrets():
    initialize_database()
    with session_scope() as session:
        user = register_user(session, "SQLite Preference User", "sqlite.preferences@example.com", "Strong@123")
        save_user_preferences(
            session,
            user.id,
            {
                "preferred_currency": "INR",
                "default_dashboard_scope": "PRIMARY_ACCOUNT",
                "risk_preference": "CONSERVATIVE",
                "investment_horizon": "5-10 YEARS",
                "monthly_investment_target": 5000,
                "alerts_enabled": True,
                "compact_tables": False,
            },
        )
        session.flush()
        user_id = user.id
    with session_scope() as session:
        saved = get_user_preferences(session, user_id)
    assert saved["monthly_investment_target"] == 5000
    assert saved["risk_preference"] == "CONSERVATIVE"

    users = read_table("users", limit=100, storage_safe=False)
    row = users.loc[users["id"] == user_id].iloc[0]
    assert row["password_hash"] == "[HASHED]"
    assert "***@" in row["email"]


def test_consistent_sqlite_backup_can_be_opened():
    initialize_database()
    data, filename = create_backup_bytes()
    assert filename.endswith(".db")
    assert len(data) > 1024
    temp_path = settings.backup_dir / "pytest_backup_check.db"
    temp_path.write_bytes(data)
    try:
        connection = sqlite3.connect(temp_path)
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
        count = connection.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        connection.close()
        assert result == "ok"
        assert count > 0
    finally:
        temp_path.unlink(missing_ok=True)


def test_table_count_api_reports_rows():
    initialize_database()
    counts = table_counts()
    assert counts["categories"] > 0
    assert counts["users"] >= 0

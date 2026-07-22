from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_sqlite_schema_has_complete_security_and_storage_tables():
    schema = (ROOT / "database" / "sqlite_schema.sql").read_text(encoding="utf-8").lower()
    tables = (
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
    )
    for table in tables:
        assert f"create table {table}" in schema
    assert "statement_import_id" in schema
    assert "pragma foreign_keys=on" in schema
    assert "pragma journal_mode=wal" in schema


def test_streamlit_login_page_boots_without_exception():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
    app.run()
    assert not app.exception
    assert any(button.label == "Sign in securely" for button in app.button)
    assert any(button.label == "Create private account" for button in app.button)


def test_authenticated_admin_pages_boot_without_exception():
    from backend.database import initialize_database, session_scope
    from backend.models import UserRole
    from backend.services import register_user

    initialize_database()
    with session_scope() as session:
        user = register_user(session, "UI Smoke Admin", "ui.smoke.admin@example.com", "Strong@123")
        user.role = UserRole.ADMIN
        session.flush()
        user_id = user.id

    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=40)
    app.session_state["authenticated"] = True
    app.session_state["user_id"] = user_id
    app.session_state["user_name"] = "UI Smoke Admin"
    app.session_state["user_email"] = "ui.smoke.admin@example.com"
    app.session_state["user_role"] = "ADMIN"
    app.session_state["active_page"] = "Dashboard"
    app.run()
    assert not app.exception

    pages = [
        "Profile & Accounts",
        "Upload & Transactions",
        "Analytics",
        "Budgets",
        "Predictions",
        "Financial Health",
        "AI Advisor",
        "Investment Ideas",
        "Reports",
        "My Stored Data",
        "Developer Admin",
        "Database Console",
        "Settings",
    ]
    for page in pages:
        navigation = next(item for item in app.radio if item.label == "Navigation")
        navigation.set_value(page)
        app.run()
        assert not app.exception, f"{page} failed: {[str(item) for item in app.exception]}"

from pathlib import Path

import plotly.express as px

from frontend.charting import chart_config

ROOT = Path(__file__).resolve().parents[1]


def test_chart_download_uses_title_as_filename():
    fig = px.bar(x=["A", "B"], y=[1, 2], title="Monthly Expense Trend")
    config = chart_config(fig)
    assert config["displayModeBar"] is True
    assert config["responsive"] is True
    assert config["toImageButtonOptions"]["filename"] == "monthly_expense_trend"


def test_all_page_charts_use_shared_interactive_renderer():
    page_sources = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "frontend" / "pages").glob("*.py"))
    assert ".plotly_chart(" not in page_sources
    assert "show_chart(" in page_sources


def test_redundant_inline_comments_removed_from_application_code():
    sources = [ROOT / "app.py", *list((ROOT / "frontend").rglob("*.py")), *list((ROOT / "backend").rglob("*.py"))]
    comment_lines = []
    for path in sources:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("#"):
                comment_lines.append((path.name, line))
    assert not comment_lines


def test_populated_dashboard_and_analytics_render_without_exception():
    from datetime import datetime

    from streamlit.testing.v1 import AppTest

    from backend.database import initialize_database, session_scope
    from backend.services import add_transaction, register_user

    initialize_database()
    with session_scope() as session:
        user = register_user(session, "Chart Smoke User", "chart.smoke@example.com", "Strong@123")
        for index in range(1, 7):
            add_transaction(
                session,
                user.id,
                {
                    "transaction_date": datetime(2026, index, 1),
                    "description": "Salary credit",
                    "transaction_type": "INCOME",
                    "amount": 50000,
                    "category": "Salary",
                    "transaction_id": f"SMOKE-IN-{index}",
                },
            )
            add_transaction(
                session,
                user.id,
                {
                    "transaction_date": datetime(2026, index, 5),
                    "description": "Monthly groceries",
                    "transaction_type": "EXPENSE",
                    "amount": 2500 + index * 100,
                    "category": "Groceries",
                    "payment_mode": "UPI",
                    "merchant": "Market",
                    "transaction_id": f"SMOKE-OUT-{index}",
                },
            )
        session.flush()
        user_id = user.id

    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=40)
    app.session_state["authenticated"] = True
    app.session_state["user_id"] = user_id
    app.session_state["user_name"] = "Chart Smoke User"
    app.session_state["user_email"] = "chart.smoke@example.com"
    app.session_state["user_role"] = "USER"
    app.session_state["active_page"] = "Dashboard"
    app.run()
    assert not app.exception

    navigation = next(item for item in app.radio if item.label == "Navigation")
    navigation.set_value("Analytics")
    app.run()
    assert not app.exception

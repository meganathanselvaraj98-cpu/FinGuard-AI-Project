from __future__ import annotations

import streamlit as st

from backend.database import initialize_database, session_scope
from backend.logging_config import configure_logging
from backend.models import User, UserStatus
from frontend.components import brand
from frontend.pages.auth import render_auth_page
from frontend.pages.budget import render_budget_page
from frontend.pages.dashboard import render_analytics_page, render_dashboard_page
from frontend.pages.data import render_data_page
from frontend.pages.intelligence import (
    render_advisor_page,
    render_health_page,
    render_investment_page,
    render_predictions_page,
)
from frontend.pages.profile import render_profile_page
from frontend.pages.reports import render_admin_page, render_reports_page, render_settings_page
from frontend.pages.storage import render_my_data_page, render_sqlite_admin_console
from frontend.theme import apply_theme

st.set_page_config(
    page_title="FinGuard AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)
configure_logging()


@st.cache_resource(show_spinner=False)
def initialize_application() -> bool:
    initialize_database()
    return True


@st.cache_data(ttl=30, show_spinner=False, max_entries=100)
def _session_identity(user_id: int) -> tuple[str, str, str, str] | None:
    with session_scope() as session:
        user = session.get(User, user_id)
        if not user:
            return None
        return user.full_name, user.email, user.role.value, user.status.value


def initialize_state() -> None:
    defaults = {
        "authenticated": False,
        "user_id": None,
        "user_name": "",
        "user_email": "",
        "user_role": "USER",
        "active_page": "Dashboard",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def refresh_authenticated_session() -> bool:
    if not st.session_state.get("authenticated") or not st.session_state.get("user_id"):
        return False
    identity = _session_identity(int(st.session_state.user_id))
    if not identity or identity[3] != UserStatus.ACTIVE.value:
        st.session_state.clear()
        return False
    st.session_state.user_name, st.session_state.user_email, st.session_state.user_role, _ = identity
    return True


def logout() -> None:
    st.cache_data.clear()
    st.session_state.clear()
    st.rerun()


def _pages() -> list[str]:
    pages = [
        "Dashboard",
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
        "Settings",
    ]
    if st.session_state.user_role == "ADMIN":
        pages.extend(["Developer Admin", "Database Console"])
    return pages


def _display_name(page: str) -> str:
    return {
        "Profile & Accounts": "👤 Profile & Accounts",
        "Upload & Transactions": "💳 Upload & Transactions",
        "Dashboard": "🏠 Dashboard",
        "Analytics": "📊 Analytics",
        "Budgets": "🎯 Budgets",
        "Predictions": "🔮 Predictions",
        "Financial Health": "💚 Financial Health",
        "AI Advisor": "🧠 AI Advisor",
        "Investment Ideas": "📈 Investment Ideas",
        "Reports": "🧾 Reports",
        "My Stored Data": "🗂️ My Stored Data",
        "Settings": "⚙️ Settings",
        "Developer Admin": "🛡️ Admin Portal",
        "Database Console": "🗄️ Database Console",
    }.get(page, page)


def render_sidebar_navigation() -> str:
    pages = _pages()
    current = st.session_state.active_page if st.session_state.active_page in pages else "Dashboard"

    with st.sidebar:
        brand()
        st.markdown("---")
        st.markdown(f"**{st.session_state.user_name}**")
        st.caption(st.session_state.user_email)
        st.caption(f"Access level: {st.session_state.user_role.title()}")
        selected = st.radio(
            "Navigation",
            pages,
            index=pages.index(current),
            format_func=_display_name,
            key="sidebar_navigation",
            label_visibility="collapsed",
        )
        st.markdown("---")
        if st.button("Logout", type="primary", width="stretch"):
            logout()

    if selected != st.session_state.active_page:
        st.session_state.active_page = selected
        st.rerun()
    return st.session_state.active_page


def main() -> None:
    apply_theme()
    initialize_state()
    initialize_application()
    if not st.session_state.authenticated or not refresh_authenticated_session():
        render_auth_page()
        return

    page = render_sidebar_navigation()
    user_id = int(st.session_state.user_id)
    routes = {
        "Dashboard": lambda: render_dashboard_page(user_id, st.session_state.user_name),
        "Profile & Accounts": lambda: render_profile_page(user_id),
        "Upload & Transactions": lambda: render_data_page(user_id),
        "Analytics": lambda: render_analytics_page(user_id),
        "Budgets": lambda: render_budget_page(user_id),
        "Predictions": lambda: render_predictions_page(user_id),
        "Financial Health": lambda: render_health_page(user_id),
        "AI Advisor": lambda: render_advisor_page(user_id),
        "Investment Ideas": lambda: render_investment_page(user_id),
        "Reports": lambda: render_reports_page(user_id, st.session_state.user_name),
        "My Stored Data": lambda: render_my_data_page(user_id),
        "Settings": lambda: render_settings_page(user_id),
    }
    if page in {"Developer Admin", "Database Console"}:
        if st.session_state.user_role != "ADMIN":
            st.error("Administrator access is required.")
            return
        if page == "Developer Admin":
            render_admin_page(user_id)
        else:
            render_sqlite_admin_console(user_id)
        return
    routes.get(page, routes["Dashboard"])()


if __name__ == "__main__":
    main()

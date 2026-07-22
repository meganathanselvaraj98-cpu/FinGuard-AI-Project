"""Login and registration page."""

from __future__ import annotations

import streamlit as st

from backend.database import session_scope
from backend.security import password_is_strong
from backend.services import authenticate_user, register_user
from frontend.components import feature_chips
from frontend.theme import hero


def render_auth_page() -> None:
    hero(
        "Finance dashboard",
        "Understand every rupee. Make every decision with clarity.",
        "Create your account, connect your bank profiles, upload statements, and explore interactive insights in one place.",
    )
    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        login_tab, register_tab = st.tabs(["Sign in", "Create account"])
        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email address", placeholder="name@example.com")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign in securely", type="primary", width="stretch")
            if submitted:
                if not email.strip() or not password:
                    st.error("Enter your email and password.")
                else:
                    try:
                        with session_scope() as session:
                            user = authenticate_user(session, email, password)
                            if user:
                                st.session_state.authenticated = True
                                st.session_state.user_id = user.id
                                st.session_state.user_name = user.full_name
                                st.session_state.user_email = user.email
                                st.session_state.user_role = user.role.value
                                st.session_state.active_page = "Dashboard"
                                st.rerun()
                        st.error("Invalid email or password.")
                    except PermissionError as error:
                        st.error(str(error))
        with register_tab:
            with st.form("register_form", clear_on_submit=True):
                full_name = st.text_input("Full name", placeholder="Arish Khan A")
                email = st.text_input("Email", key="register_email")
                password = st.text_input("Create password", type="password", key="register_password", help="8+ characters with uppercase, lowercase, number and special character.")
                confirm = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button("Create private account", type="primary", width="stretch")
            if submitted:
                if password != confirm:
                    st.error("Passwords do not match.")
                else:
                    valid, message = password_is_strong(password)
                    if not valid:
                        st.error(message)
                    else:
                        try:
                            with session_scope() as session:
                                user = register_user(session, full_name, email, password)
                                role_text = " The first account receives Admin access." if user.role.value == "ADMIN" else ""
                            st.success(f"Account created successfully.{role_text} Sign in to continue.")
                        except ValueError as error:
                            st.error(str(error))
    with right:
        st.subheader("What you can do")
        feature_chips(["Profile setup", "Bank accounts", "Statement upload", "Smart dashboards", "Predictions", "Admin portal"])
        st.write("")
        st.markdown(
            """
            **Key highlights**
            - Track income, expenses, savings, and budgets
            - Switch between bank accounts and uploaded statements
            - View interactive charts and financial summaries
            - Generate downloadable reports
            - Use admin tools for user and activity monitoring
            """
        )

from __future__ import annotations

import streamlit as st

from backend.database import session_scope
from backend.security import mask_account_number, mask_ifsc, mask_pan, mask_phone
from backend.services import add_bank_account, delete_bank_account, get_profile, list_bank_accounts, save_profile
from frontend.components import security_notice
from frontend.pages.dashboard import clear_finance_cache
from frontend.theme import hero


def render_profile_page(user_id: int) -> None:
    hero(
        "Private profile",
        "Profile & bank accounts",
        "Manage your personal details and linked accounts. Sensitive values stay protected and normal screens show masked identifiers.",
    )
    security_notice()
    view = st.radio(
        "Profile view",
        ["Personal details", "Bank accounts", "Privacy preview"],
        horizontal=True,
        label_visibility="collapsed",
        key="profile_view",
    )

    if view == "Personal details":
        with session_scope() as session:
            current = get_profile(session, user_id)
        choices = ["", "Male", "Female", "Non-binary", "Prefer not to say"]
        with st.form("profile_form"):
            col1, col2 = st.columns(2)
            with col1:
                phone = st.text_input("Phone number", value=current.get("phone", ""), placeholder="10-digit mobile number")
                dob_text = st.text_input("Date of birth (YYYY-MM-DD)", value=current.get("dob", ""))
                current_gender = current.get("gender", "")
                gender = st.selectbox("Gender (optional)", choices, index=choices.index(current_gender) if current_gender in choices else 0)
                occupation = st.text_input("Occupation", value=current.get("occupation", ""))
            with col2:
                city = st.text_input("City", value=current.get("city", ""))
                address = st.text_area("Address", value=current.get("address", ""))
                monthly_income = st.text_input("Approximate monthly income", value=current.get("monthly_income", ""), placeholder="48000")
                pan = st.text_input("PAN (optional)", value=current.get("pan", ""), type="password", placeholder="ABCDE1234F")
            submitted = st.form_submit_button("Save profile", type="primary", width="stretch")
        if submitted:
            try:
                with session_scope() as session:
                    save_profile(
                        session,
                        user_id,
                        {
                            "phone": phone,
                            "dob": dob_text,
                            "gender": gender,
                            "address": address,
                            "city": city,
                            "occupation": occupation,
                            "monthly_income": monthly_income,
                            "pan": pan,
                        },
                    )
                st.success("Personal details saved securely.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
        return

    if view == "Bank accounts":
        left, right = st.columns([1.02, 0.98], gap="large")
        with left:
            st.subheader("Add bank account")
            with st.form("bank_account_form", clear_on_submit=True):
                nickname = st.text_input("Account nickname", placeholder="Salary account")
                bank_name = st.text_input("Bank name")
                holder_name = st.text_input("Account holder name")
                account_number = st.text_input("Account number", type="password")
                ifsc = st.text_input("IFSC code", placeholder="SBIN0001234")
                account_type = st.selectbox("Account type", ["Savings", "Current", "Salary", "NRE/NRO", "Other"])
                branch = st.text_input("Branch")
                is_primary = st.checkbox("Make this the primary account")
                submitted = st.form_submit_button("Add account", type="primary", width="stretch")
            if submitted:
                try:
                    with session_scope() as session:
                        add_bank_account(
                            session,
                            user_id,
                            {
                                "nickname": nickname,
                                "bank_name": bank_name,
                                "holder_name": holder_name,
                                "account_number": account_number,
                                "ifsc": ifsc,
                                "account_type": account_type,
                                "branch": branch,
                                "is_primary": is_primary,
                            },
                        )
                    clear_finance_cache()
                    st.success("Bank account saved securely.")
                    st.rerun()
                except (ValueError, PermissionError) as error:
                    st.error(str(error))

        with right:
            st.subheader("Saved accounts")
            with session_scope() as session:
                accounts = list_bank_accounts(session, user_id, decrypt=True)
            if not accounts:
                st.info("No bank account added yet.")
            for account in accounts:
                with st.container(border=True):
                    st.markdown(f"**{account['nickname']}** {'· Primary' if account['is_primary'] else ''}")
                    st.caption(f"{account['bank_name']} · {mask_account_number(account['account_number'])}")
                    st.caption(f"{account['account_type'] or 'Account'} · IFSC {mask_ifsc(account['ifsc'])} · {account['branch'] or 'Branch not provided'}")
                    confirm = st.checkbox("Confirm removal", key=f"confirm_account_{account['id']}")
                    if st.button("Remove account", key=f"delete_account_{account['id']}", disabled=not confirm):
                        with session_scope() as session:
                            removed = delete_bank_account(session, user_id, account["id"])
                        clear_finance_cache()
                        if removed:
                            st.success("Account removed. Linked transactions remain available but become unlinked.")
                            st.rerun()
                        st.error("Account was not found or does not belong to you.")
        return

    with session_scope() as session:
        profile = get_profile(session, user_id)
        accounts = list_bank_accounts(session, user_id, decrypt=True)
    st.subheader("How your data appears in normal screens")
    preview = {
        "Phone": mask_phone(profile.get("phone")),
        "PAN": mask_pan(profile.get("pan")),
        "City": profile.get("city") or "Not provided",
        "Occupation": profile.get("occupation") or "Not provided",
        "Account numbers": [mask_account_number(item.get("account_number")) for item in accounts] or ["No account"],
        "IFSC codes": [mask_ifsc(item.get("ifsc")) for item in accounts] or ["No account"],
    }
    st.json(preview)
    st.info("Normal screens keep sensitive identifiers masked while you review your profile and accounts.")

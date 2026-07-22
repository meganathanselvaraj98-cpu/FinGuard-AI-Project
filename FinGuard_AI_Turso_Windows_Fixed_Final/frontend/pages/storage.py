"""User-owned data centre and administrator database console."""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.charting import show_chart
from sqlalchemy import func, select

from backend.config import settings
from backend.database import session_scope
from backend.models import AuditLog, BankAccount, Budget, Prediction, Report, StatementImport, Transaction, User, UserProfile
from backend.security import mask_account_number, mask_ifsc, mask_pan, mask_phone
from backend.services import get_profile, get_user_preferences, list_bank_accounts, log_audit
from backend.sqlite_manager import (
    checkpoint,
    create_backup_bytes,
    create_persistent_backup,
    database_overview,
    integrity_check,
    list_tables,
    optimize_database,
    read_table,
    table_counts,
    table_csv_bytes,
)
from frontend.pages.dashboard import load_user_dataframe
from frontend.theme import hero


def _style(fig, height: int = 360):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin=dict(l=20, r=20, t=55, b=25),
        legend_title_text="",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(5,11,20,.35)",
    )
    return fig


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, indent=2, default=str, ensure_ascii=False).encode("utf-8")


def _user_counts(user_id: int) -> dict[str, int]:
    with session_scope() as session:
        return {
            "accounts": session.scalar(select(func.count()).select_from(BankAccount).where(BankAccount.user_id == user_id)) or 0,
            "statements": session.scalar(select(func.count()).select_from(StatementImport).where(StatementImport.user_id == user_id)) or 0,
            "transactions": session.scalar(select(func.count()).select_from(Transaction).where(Transaction.user_id == user_id)) or 0,
            "budgets": session.scalar(select(func.count()).select_from(Budget).where(Budget.user_id == user_id)) or 0,
            "predictions": session.scalar(select(func.count()).select_from(Prediction).where(Prediction.user_id == user_id)) or 0,
            "reports": session.scalar(select(func.count()).select_from(Report).where(Report.user_id == user_id)) or 0,
            "audits": session.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.user_id == user_id)) or 0,
        }


def render_my_data_page(user_id: int) -> None:
    hero(
        "Personal records",
        "My stored data",
        "Open one data category at a time to review your profile, accounts, statements, transactions, budgets, predictions, reports, preferences, and account activity.",
    )
    counts = _user_counts(user_id)
    cards = st.columns(7)
    values = [
        ("Accounts", counts["accounts"]),
        ("Statements", counts["statements"]),
        ("Transactions", counts["transactions"]),
        ("Budgets", counts["budgets"]),
        ("Predictions", counts["predictions"]),
        ("Reports", counts["reports"]),
        ("Activity", counts["audits"]),
    ]
    for column, (label, value) in zip(cards, values):
        column.metric(label, value)

    view = st.radio(
        "Stored data view",
        ["Identity", "Bank accounts", "Statements", "Transactions", "Budgets", "Predictions", "Reports", "Preferences & activity", "Export"],
        horizontal=True,
        label_visibility="collapsed",
        key="stored_data_view",
    )

    if view == "Identity":
        with session_scope() as session:
            user = session.get(User, user_id)
            profile = get_profile(session, user_id)
        identity = {
            "Full name": user.full_name if user else "",
            "Email": user.email if user else "",
            "Role": user.role.value if user else "",
            "Account status": user.status.value if user else "",
            "Phone": mask_phone(profile.get("phone")),
            "Date of birth": profile.get("dob") or "Not provided",
            "Gender": profile.get("gender") or "Not provided",
            "City": profile.get("city") or "Not provided",
            "Occupation": profile.get("occupation") or "Not provided",
            "Monthly income": profile.get("monthly_income") or "Not provided",
            "PAN": mask_pan(profile.get("pan")),
            "Address": profile.get("address") or "Not provided",
            "Registered": user.created_at if user else None,
            "Last login": user.last_login_at if user else None,
        }
        st.dataframe(pd.DataFrame([(key, str(value) if value is not None else "") for key, value in identity.items()], columns=["Field", "Stored value"]), width="stretch", hide_index=True)
        st.caption("Private identifiers are masked in normal views.")
        return

    if view == "Bank accounts":
        with session_scope() as session:
            accounts = list_bank_accounts(session, user_id, decrypt=True)
        reveal = st.toggle("Temporarily reveal my own account number and IFSC", value=False)
        rows = [
            {
                "Nickname": account["nickname"],
                "Bank": account.get("bank_name", ""),
                "Holder": account.get("holder_name", ""),
                "Account number": account.get("account_number", "") if reveal else mask_account_number(account.get("account_number", "")),
                "IFSC": account.get("ifsc", "") if reveal else mask_ifsc(account.get("ifsc", "")),
                "Type": account.get("account_type", ""),
                "Branch": account.get("branch", ""),
                "Primary": account.get("is_primary", False),
            }
            for account in accounts
        ]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True) if rows else st.info("No bank accounts are stored yet.")
        if reveal:
            st.warning("Do not reveal private account details on a shared screen.")
        return

    if view == "Statements":
        with session_scope() as session:
            statements = session.scalars(select(StatementImport).where(StatementImport.user_id == user_id).order_by(StatementImport.created_at.desc())).all()
        frame = pd.DataFrame([
            {
                "Label": item.label, "File": item.file_name, "Type": item.file_type,
                "Period start": item.period_start, "Period end": item.period_end,
                "Raw rows": item.raw_rows, "Imported": item.imported_rows,
                "Duplicates": item.duplicate_rows, "Errors": item.error_rows,
                "Status": item.status, "Imported at": item.created_at,
            }
            for item in statements
        ])
        if frame.empty:
            st.info("No bank statement imports are stored yet.")
        else:
            st.dataframe(frame, width="stretch", hide_index=True)
            file_counts = frame.groupby("Type", as_index=False).size()
            show_chart(_style(px.pie(file_counts, names="Type", values="size", hole=0.48, title="Stored statement formats")))
        return

    if view == "Transactions":
        transactions = load_user_dataframe(user_id)
        if transactions.empty:
            st.info("No transactions are stored yet.")
            return
        search = st.text_input("Search stored transactions", key="my_data_transaction_search")
        filtered = transactions
        if search:
            mask = filtered.astype(str).apply(lambda column: column.str.contains(search, case=False, na=False, regex=False)).any(axis=1)
            filtered = filtered[mask]
        columns = ["date", "transaction_id_masked", "description", "category", "type", "amount", "balance_after", "payment_mode", "merchant", "risk_level", "statement_label", "account_last4"]
        st.dataframe(filtered[[column for column in columns if column in filtered.columns]].sort_values("date", ascending=False).head(1000), width="stretch", hide_index=True)
        monthly = filtered.assign(month=pd.to_datetime(filtered["date"]).dt.to_period("M").astype(str)).groupby(["month", "type"], as_index=False)["amount"].sum()
        show_chart(_style(px.line(monthly, x="month", y="amount", color="type", markers=True, title="Stored transaction history")))
        return

    if view == "Budgets":
        with session_scope() as session:
            rows = session.scalars(select(Budget).where(Budget.user_id == user_id).order_by(Budget.budget_month.desc())).all()
        frame = pd.DataFrame([{
            "Month": item.budget_month, "Category": item.category_name,
            "Allocated amount": float(item.allocated_amount),
            "Alert threshold %": item.alert_threshold_percent, "Saved at": item.created_at,
        } for item in rows])
        st.dataframe(frame, width="stretch", hide_index=True) if not frame.empty else st.info("No budgets are stored yet.")
        return

    if view == "Predictions":
        with session_scope() as session:
            rows = session.scalars(select(Prediction).where(Prediction.user_id == user_id).order_by(Prediction.created_at.desc()).limit(500)).all()
        frame = pd.DataFrame([{
            "Created": item.created_at, "Prediction type": item.prediction_type,
            "Value": item.predicted_value, "Label": item.predicted_label,
        } for item in rows])
        st.dataframe(frame, width="stretch", hide_index=True) if not frame.empty else st.info("No prediction records are stored yet.")
        return

    if view == "Reports":
        with session_scope() as session:
            rows = session.scalars(select(Report).where(Report.user_id == user_id).order_by(Report.created_at.desc()).limit(500)).all()
        frame = pd.DataFrame([{
            "Created": item.created_at, "Report type": item.report_type,
            "Format": item.report_format, "File": item.file_name, "Status": item.status,
        } for item in rows])
        st.dataframe(frame, width="stretch", hide_index=True) if not frame.empty else st.info("No generated-report history is stored yet.")
        return

    if view == "Preferences & activity":
        with session_scope() as session:
            preferences = get_user_preferences(session, user_id)
            audits = session.scalars(select(AuditLog).where(AuditLog.user_id == user_id).order_by(AuditLog.created_at.desc()).limit(500)).all()
        left, right = st.columns(2)
        left.subheader("Saved preferences")
        left.json(preferences)
        audit_frame = pd.DataFrame([{
            "Time": item.created_at, "Action": item.action, "Entity": item.entity_type,
            "Entity ID": item.entity_id, "Details": item.details_json,
        } for item in audits])
        right.subheader("Recent account activity")
        right.dataframe(audit_frame, width="stretch", hide_index=True) if not audit_frame.empty else right.info("No activity events.")
        return

    with session_scope() as session:
        user = session.get(User, user_id)
        profile = get_profile(session, user_id)
        accounts = list_bank_accounts(session, user_id, decrypt=True)
        preferences = get_user_preferences(session, user_id)
    transactions = load_user_dataframe(user_id)
    payload = {
        "generated_at": datetime.now().isoformat(),
        "user": {
            "full_name": user.full_name if user else "",
            "email": user.email if user else "",
            "role": user.role.value if user else "",
            "status": user.status.value if user else "",
        },
        "profile": profile,
        "bank_accounts": [
            {
                "nickname": item["nickname"],
                "bank_name": item.get("bank_name", ""),
                "holder_name": item.get("holder_name", ""),
                "account_number_masked": mask_account_number(item.get("account_number", "")),
                "ifsc_masked": mask_ifsc(item.get("ifsc", "")),
                "account_type": item.get("account_type", ""),
                "branch": item.get("branch", ""),
                "is_primary": item.get("is_primary", False),
            }
            for item in accounts
        ],
        "preferences": preferences,
        "counts": counts,
    }
    st.download_button(
        "Download my privacy-safe JSON data",
        _json_bytes(payload),
        f"finguard_my_data_{datetime.now():%Y%m%d_%H%M%S}.json",
        "application/json",
        type="primary",
        width="stretch",
    )
    if not transactions.empty:
        st.download_button(
            "Download my transactions as CSV",
            transactions.to_csv(index=False).encode("utf-8-sig"),
            f"finguard_my_transactions_{datetime.now():%Y%m%d_%H%M%S}.csv",
            "text/csv",
            width="stretch",
        )
    st.info("Exports mask account number, IFSC, phone, and PAN.")


def render_sqlite_admin_console(admin_user_id: int) -> None:
    """Render shared/local database health, table previews, exports, and maintenance."""
    mode_label = "Shared cloud database" if settings.is_turso else "Local database"
    hero(
        "Administrator storage",
        "Database console",
        "Inspect table counts, preview stored records, export data, and verify database health from one restricted administrator view.",
    )

    if settings.is_turso:
        if st.button("Refresh from cloud", type="primary", width="stretch"):
            checkpoint()
            st.cache_data.clear()
            st.success("Latest cloud records synchronized.")

    overview = database_overview()
    cards = st.columns(5)
    values = [
        ("Mode", mode_label),
        ("Tables", overview["tables"]),
        ("Stored rows", f"{overview['rows']:,}"),
        ("Local cache size", f"{overview['size_bytes'] / 1024 / 1024:.2f} MB"),
        ("Integrity", overview["integrity"].upper()),
    ]
    for column, (label, value) in zip(cards, values):
        column.metric(label, value)

    counts = table_counts()
    count_frame = pd.DataFrame(
        [{"Table": table, "Rows": rows} for table, rows in counts.items()]
    ).sort_values("Rows", ascending=False)
    left, right = st.columns([1.2, 1], gap="large")
    left.dataframe(count_frame, width="stretch", hide_index=True)
    show_chart(
        _style(px.bar(count_frame, x="Rows", y="Table", orientation="h", title="Rows stored by section"), 430),
        container=right,
    )

    table = st.selectbox("Select data section", list_tables())
    c1, c2, c3 = st.columns([1, 1, 2])
    limit = c1.selectbox("Rows per page", [50, 100, 250, 500, 1000], index=2)
    page = c2.number_input("Page", min_value=1, value=1, step=1)
    storage_mode = c3.radio("Preview", ["Privacy-safe", "Encrypted storage"], horizontal=True)
    frame = read_table(
        table,
        limit=int(limit),
        offset=(int(page) - 1) * int(limit),
        storage_safe=storage_mode == "Privacy-safe",
    )
    st.dataframe(frame, width="stretch", hide_index=True)
    if storage_mode == "Encrypted storage":
        st.caption("Protected fields are shown as stored ciphertext; password hashes remain hidden.")

    st.download_button(
        f"Download {table} as CSV",
        table_csv_bytes(table),
        f"{table}_{datetime.now():%Y%m%d_%H%M%S}.csv",
        "text/csv",
        width="stretch",
    )

    st.subheader("Database actions")
    m1, m2 = st.columns(2)
    if m1.button("Run integrity check", width="stretch"):
        result = integrity_check()
        with session_scope() as session:
            log_audit(session, "DATABASE_INTEGRITY_CHECK", admin_user_id, "DATABASE", details={"result": result})
        st.success(f"Integrity result: {result}")
    if m2.button("Refresh database statistics", width="stretch"):
        optimize_database()
        with session_scope() as session:
            log_audit(session, "DATABASE_OPTIMIZED", admin_user_id, "DATABASE")
        st.success("Database statistics refreshed.")

    if not settings.is_turso:
        if st.button("Prepare complete local backup", type="primary", width="stretch"):
            backup_data, backup_name = create_backup_bytes()
            st.session_state["admin_database_backup"] = {"data": backup_data, "name": backup_name}
        prepared = st.session_state.get("admin_database_backup")
        if prepared:
            st.download_button(
                "Download prepared backup",
                prepared["data"],
                prepared["name"],
                "application/octet-stream",
                width="stretch",
            )
        if st.button("Save timestamped backup", width="stretch"):
            path = create_persistent_backup()
            with session_scope() as session:
                log_audit(session, "DATABASE_BACKUP_CREATED", admin_user_id, "DATABASE", details={"file": path.name})
            st.success(f"Backup saved: {path.name}")
    else:
        st.info("Shared deployment data is stored in the cloud database. Use the Turso dashboard for cloud-level backups and token management.")


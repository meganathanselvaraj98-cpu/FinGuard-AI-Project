"""Privacy-safe exports, administration analytics, audit review, and settings."""

from __future__ import annotations

from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.charting import show_chart
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.database import session_scope
from backend.models import AuditLog, BankAccount, Report, StatementImport, Transaction, User, UserProfile
from backend.reporting import csv_bytes, excel_dashboard_bytes, pdf_report_bytes
from backend.security import decrypt_text, mask_email, mask_pan, mask_phone
from backend.services import (
    delete_user_data,
    get_user_preferences,
    log_audit,
    save_report_record,
    save_user_preferences,
)
from backend.sqlite_manager import create_backup_bytes, database_overview
from frontend.pages.dashboard import load_user_dataframe
from frontend.theme import hero


def _style(fig, height: int = 380):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin=dict(l=20, r=20, t=55, b=25),
        legend_title_text="",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(5,11,20,.35)",
    )
    return fig


def render_reports_page(user_id: int, user_name: str) -> None:
    hero(
        "Portable insights",
        "Reports & downloads",
        "Generate privacy-safe CSV, Excel dashboard, and PDF outputs. Sensitive banking identifiers and decrypted transaction references are excluded.",
    )
    df = load_user_dataframe(user_id)
    if df.empty:
        st.info("No transactions are available for export.")
        return

    c1, c2 = st.columns([1, 1])
    report_title = c1.text_input("Report title", value="FinGuard AI Personal Finance Report")
    recent_only = c2.selectbox("Report period", ["All transactions", "Last 12 months", "Last 6 months", "Last 3 months"])
    report_df = df.copy()
    if recent_only != "All transactions":
        months = int(recent_only.split()[1])
        cutoff = pd.Timestamp.now().normalize() - pd.DateOffset(months=months)
        report_df = report_df[report_df["date"] >= cutoff]

    if st.button("Generate report package", type="primary", width="stretch"):
        if report_df.empty:
            st.warning("No transactions exist in the selected period.")
        else:
            with st.spinner("Building CSV, Excel dashboard, and PDF report..."):
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_data = csv_bytes(report_df)
                excel_data = excel_dashboard_bytes(report_df, report_title)
                pdf_data = pdf_report_bytes(report_df, user_name)
                package = {
                    "stamp": stamp,
                    "csv": csv_data,
                    "excel": excel_data,
                    "pdf": pdf_data,
                    "rows": len(report_df),
                }
                st.session_state[f"report_package_{user_id}"] = package

                files = [
                    (f"finguard_transactions_{stamp}.csv", csv_data, "CSV"),
                    (f"finguard_dashboard_{stamp}.xlsx", excel_data, "XLSX"),
                    (f"finguard_report_{stamp}.pdf", pdf_data, "PDF"),
                ]
                with session_scope() as session:
                    for file_name, content, report_format in files:
                        path = settings.report_dir / file_name
                        path.write_bytes(content)
                        save_report_record(session, user_id, "PERSONAL_FINANCE", report_format, file_name, str(path))
            st.success("Report package generated and recorded in the audit log.")

    package = st.session_state.get(f"report_package_{user_id}")
    if package:
        st.caption(f"Generated package · {package['rows']:,} rows · {package['stamp']}")
        d1, d2, d3 = st.columns(3)
        d1.download_button("Download CSV", package["csv"], f"finguard_transactions_{package['stamp']}.csv", "text/csv", width="stretch")
        d2.download_button("Download Excel dashboard", package["excel"], f"finguard_dashboard_{package['stamp']}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
        d3.download_button("Download PDF report", package["pdf"], f"finguard_report_{package['stamp']}.pdf", "application/pdf", width="stretch")

    st.info("Exports exclude full account number, IFSC, PAN, phone, address, and decrypted transaction references. Excel contains dashboard charts, filterable tables, and pivot-style summary sheets.")
    with session_scope() as session:
        history = session.scalars(select(Report).where(Report.user_id == user_id).order_by(Report.created_at.desc()).limit(50)).all()
    if history:
        st.subheader("Report history")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Created": item.created_at, "Type": item.report_type, "Format": item.report_format, "File": item.file_name, "Status": item.status}
                    for item in history
                ]
            ),
            width="stretch",
            hide_index=True,
        )


def _income_number(value: str | None) -> float:
    try:
        return float(str(value or "0").replace(",", "").replace("₹", "").strip())
    except ValueError:
        return 0.0


def _income_band(value: float) -> str:
    if value <= 0:
        return "Not provided"
    if value < 25_000:
        return "Below ₹25K"
    if value < 50_000:
        return "₹25K–₹50K"
    if value < 100_000:
        return "₹50K–₹1L"
    return "Above ₹1L"


def render_admin_page(admin_user_id: int) -> None:
    hero(
        "Restricted administration",
        "FinGuard Developer Admin portal",
        "Monitor users, demographics, banks, statement activity, income segments, finance trends, model usage, reports, and audit events. Full banking identifiers are never decrypted in this portal.",
    )
    with session_scope() as session:
        users = session.scalars(select(User).order_by(User.created_at.desc())).all()
        profiles = {item.user_id: item for item in session.scalars(select(UserProfile)).all()}
        accounts = session.scalars(select(BankAccount)).all()
        statements = session.scalars(select(StatementImport)).all()
        transactions = session.scalars(select(Transaction).options(selectinload(Transaction.category))).all()
        reports = session.scalars(select(Report)).all()
        audits = session.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(2000)).all()

    account_rows: list[dict] = []
    banks_by_user: dict[int, list[str]] = {}
    for account in accounts:
        bank = decrypt_text(account.bank_name_encrypted) or "Unknown bank"
        account_type = decrypt_text(account.account_type_encrypted) or "Unknown"
        banks_by_user.setdefault(account.user_id, []).append(bank)
        account_rows.append(
            {
                "user_id": account.user_id,
                "bank": bank,
                "account_type": account_type,
                "masked_account": f"••••{account.account_last4}",
                "primary": account.is_primary,
                "created": account.created_at,
            }
        )

    user_rows: list[dict] = []
    for user in users:
        profile = profiles.get(user.id)
        city = decrypt_text(profile.city_encrypted) if profile else ""
        occupation = decrypt_text(profile.occupation_encrypted) if profile else ""
        income_value = _income_number(decrypt_text(profile.monthly_income_encrypted) if profile else "")
        gender = decrypt_text(profile.gender_encrypted) if profile else ""
        user_rows.append(
            {
                "user_id": user.id,
                "public_id": user.public_id,
                "name": user.full_name,
                "email": mask_email(user.email),
                "role": user.role.value,
                "status": user.status.value,
                "city": city or "Not provided",
                "occupation": occupation or "Not provided",
                "gender": gender or "Not provided",
                "monthly_income": income_value,
                "income_band": _income_band(income_value),
                "banks": ", ".join(sorted(set(banks_by_user.get(user.id, ["No bank"])))),
                "created": user.created_at,
                "last_login": user.last_login_at,
            }
        )

    udf = pd.DataFrame(user_rows, columns=[
        "user_id", "public_id", "name", "email", "role", "status", "city",
        "occupation", "gender", "monthly_income", "income_band", "banks",
        "created", "last_login",
    ])
    adf = pd.DataFrame(account_rows, columns=[
        "user_id", "bank", "account_type", "masked_account", "primary", "created",
    ])
    tdf = pd.DataFrame(
        [
            {
                "user_id": item.user_id,
                "type": item.transaction_type.value,
                "amount": float(item.amount),
                "date": item.transaction_date,
                "risk": item.risk_level,
                "account_id": item.bank_account_id,
                "statement_id": item.statement_import_id,
                "category": item.category.name if item.category else "Uncategorized",
                "payment_mode": item.payment_mode or "Unknown",
                "source": item.source,
            }
            for item in transactions
        ],
        columns=["user_id", "type", "amount", "date", "risk", "account_id",
                 "statement_id", "category", "payment_mode", "source"],
    )
    sdf = pd.DataFrame(
        [
            {
                "user_id": item.user_id,
                "account_id": item.bank_account_id,
                "label": item.label,
                "file_type": item.file_type,
                "raw_rows": item.raw_rows,
                "imported_rows": item.imported_rows,
                "duplicates": item.duplicate_rows,
                "errors": item.error_rows,
                "status": item.status,
                "created": item.created_at,
            }
            for item in statements
        ],
        columns=["user_id", "account_id", "label", "file_type", "raw_rows",
                 "imported_rows", "duplicates", "errors", "status", "created"],
    )

    total_income = float(tdf.loc[tdf["type"] == "INCOME", "amount"].sum()) if not tdf.empty else 0.0
    total_expense = float(tdf.loc[tdf["type"] == "EXPENSE", "amount"].sum()) if not tdf.empty else 0.0
    metrics = st.columns(8)
    values = [
        ("Users", len(users)),
        ("Active users", int((udf["status"] == "ACTIVE").sum()) if not udf.empty else 0),
        ("Bank accounts", len(accounts)),
        ("Statements", len(statements)),
        ("Transactions", len(transactions)),
        ("Total income", f"₹{total_income:,.0f}"),
        ("Total expense", f"₹{total_expense:,.0f}"),
        ("Reports", len(reports)),
    ]
    for column, (label, value) in zip(metrics, values):
        column.metric(label, value)

    view = st.radio(
        "Admin analytics view",
        ["Executive overview", "Users & demographics", "Banks & statements", "Financial analytics", "Audit activity", "Complete user drilldown"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if view == "Executive overview":
        if udf.empty:
            st.info("No user data.")
            return
        c1, c2 = st.columns(2)
        location = udf.groupby("city", as_index=False).size().sort_values("size", ascending=False).head(15)
        show_chart(_style(px.bar(location, x="city", y="size", title="Users by location")), container=c1)
        bank_counts = adf.groupby("bank", as_index=False).size() if not adf.empty else pd.DataFrame(columns=["bank", "size"])
        if bank_counts.empty:
            c2.info("No bank accounts linked yet.")
        else:
            show_chart(_style(px.pie(bank_counts, names="bank", values="size", hole=0.5, title="Bank preference")), container=c2)
        c3, c4 = st.columns(2)
        show_chart(_style(px.histogram(udf, x="monthly_income", nbins=12, title="Monthly income distribution")), container=c3)
        status_df = udf.groupby(["role", "status"], as_index=False).size()
        show_chart(_style(px.bar(status_df, x="role", y="size", color="status", barmode="group", title="Roles and account status")), container=c4)
        return

    if view == "Users & demographics":
        search = st.text_input("Search users", placeholder="Name, masked email, city, occupation or bank")
        table = udf.copy()
        if search:
            mask = table.astype(str).apply(lambda column: column.str.contains(search, case=False, na=False, regex=False)).any(axis=1)
            table = table[mask]
        st.dataframe(table.drop(columns=["user_id"], errors="ignore"), width="stretch", hide_index=True)
        if not udf.empty:
            c1, c2 = st.columns(2)
            occupation = udf.groupby("occupation", as_index=False).size().nlargest(15, "size")
            show_chart(_style(px.bar(occupation, x="occupation", y="size", title="Occupation profile")), container=c1)
            income_bands = udf.groupby("income_band", as_index=False).size()
            show_chart(_style(px.pie(income_bands, names="income_band", values="size", hole=0.45, title="Income bands")), container=c2)
            c3, c4 = st.columns(2)
            registrations = udf.assign(month=pd.to_datetime(udf["created"]).dt.to_period("M").astype(str)).groupby("month", as_index=False).size()
            show_chart(_style(px.line(registrations, x="month", y="size", markers=True, title="User registration trend")), container=c3)
            gender = udf.groupby("gender", as_index=False).size()
            show_chart(_style(px.bar(gender, x="gender", y="size", title="Gender preference summary")), container=c4)
        return

    if view == "Banks & statements":
        c1, c2 = st.columns(2)
        if not adf.empty:
            account_types = adf.groupby("account_type", as_index=False).size()
            show_chart(_style(px.bar(account_types, x="account_type", y="size", title="Account types")), container=c1)
            primary = adf.groupby("primary", as_index=False).size()
            show_chart(_style(px.pie(primary, names="primary", values="size", hole=0.48, title="Primary-account selection")), container=c2)
            st.dataframe(adf.drop(columns=["user_id"], errors="ignore"), width="stretch", hide_index=True)
        else:
            st.info("No bank accounts.")
        if not sdf.empty:
            c3, c4 = st.columns(2)
            types = sdf.groupby("file_type", as_index=False).size()
            show_chart(_style(px.pie(types, names="file_type", values="size", hole=0.48, title="Statement file types")), container=c3)
            import_month = sdf.assign(month=pd.to_datetime(sdf["created"]).dt.to_period("M").astype(str)).groupby("month", as_index=False).agg(statements=("label", "size"), rows=("imported_rows", "sum"))
            show_chart(_style(px.bar(import_month, x="month", y=["statements", "rows"], barmode="group", title="Statement import activity")), container=c4)
            st.dataframe(sdf.drop(columns=["user_id"], errors="ignore"), width="stretch", hide_index=True)
        return

    if view == "Financial analytics":
        if tdf.empty:
            st.info("No transaction data.")
            return
        tdf["month"] = pd.to_datetime(tdf["date"]).dt.to_period("M").astype(str)
        c1, c2 = st.columns(2)
        totals = tdf.groupby("type", as_index=False)["amount"].sum()
        show_chart(_style(px.bar(totals, x="type", y="amount", title="Platform income vs expense")), container=c1)
        monthly = tdf.groupby(["month", "type"], as_index=False)["amount"].sum()
        show_chart(_style(px.line(monthly, x="month", y="amount", color="type", markers=True, title="Monthly platform cash flow")), container=c2)
        c3, c4 = st.columns(2)
        per_user = tdf.groupby(["user_id", "type"], as_index=False)["amount"].sum().merge(udf[["user_id", "name"]], on="user_id", how="left")
        show_chart(_style(px.bar(per_user, x="name", y="amount", color="type", barmode="group", title="Finance by user"), 420), container=c3)
        risk = tdf.groupby("risk", as_index=False).size()
        show_chart(_style(px.pie(risk, names="risk", values="size", hole=0.45, title="Risk distribution"), 420), container=c4)
        c5, c6 = st.columns(2)
        categories = tdf[tdf["type"] == "EXPENSE"].groupby("category", as_index=False)["amount"].sum().nlargest(15, "amount")
        show_chart(_style(px.treemap(categories, path=["category"], values="amount", title="Platform expense categories")), container=c5)
        modes = tdf[tdf["type"] == "EXPENSE"].groupby("payment_mode", as_index=False)["amount"].sum()
        show_chart(_style(px.bar(modes, x="payment_mode", y="amount", title="Platform payment modes")), container=c6)
        return

    if view == "Audit activity":
        audit_df = pd.DataFrame(
            [
                {"time": item.created_at, "user_id": item.user_id, "action": item.action, "entity": item.entity_type, "entity_id": item.entity_id, "ip": item.ip_address, "details": item.details_json}
                for item in audits
            ]
        )
        if audit_df.empty:
            st.info("No audit events recorded yet.")
            return
        st.dataframe(audit_df, width="stretch", hide_index=True)
        c1, c2 = st.columns(2)
        counts = audit_df.groupby("action", as_index=False).size().sort_values("size", ascending=False)
        show_chart(_style(px.bar(counts, x="action", y="size", title="Audit events by action")), container=c1)
        daily = audit_df.assign(day=pd.to_datetime(audit_df["time"]).dt.date).groupby("day", as_index=False).size()
        show_chart(_style(px.line(daily, x="day", y="size", markers=True, title="Audit activity over time")), container=c2)
        return

    st.warning("Authorized administrator view. This section can display complete user details for review and support operations.")
    if udf.empty:
        st.info("No users available.")
        return
    selected = st.selectbox(
        "Select user",
        udf["user_id"].tolist(),
        format_func=lambda user_id: f"{udf.loc[udf.user_id == user_id, 'name'].iloc[0]} · {udf.loc[udf.user_id == user_id, 'email'].iloc[0]}",
    )
    user_row = udf[udf["user_id"] == selected].iloc[0].to_dict()
    profile = profiles.get(selected)
    full_profile = {
        "Name": user_row["name"],
        "Masked email": user_row["email"],
        "Role": user_row["role"],
        "Status": user_row["status"],
        "City": decrypt_text(profile.city_encrypted) if profile and profile.city_encrypted else user_row["city"],
        "Occupation": decrypt_text(profile.occupation_encrypted) if profile and profile.occupation_encrypted else user_row["occupation"],
        "Monthly income": decrypt_text(profile.monthly_income_encrypted) if profile and profile.monthly_income_encrypted else "",
        "Phone": decrypt_text(profile.phone_encrypted) if profile and profile.phone_encrypted else "",
        "PAN": decrypt_text(profile.pan_encrypted) if profile and profile.pan_encrypted else "",
        "Date of birth": decrypt_text(profile.dob_encrypted) if profile and profile.dob_encrypted else "",
        "Gender": decrypt_text(profile.gender_encrypted) if profile and profile.gender_encrypted else "",
        "Address": decrypt_text(profile.address_encrypted) if profile and profile.address_encrypted else "",
    }
    st.subheader("User details")
    st.json(full_profile)

    account_details = []
    for item in accounts:
        if item.user_id != selected:
            continue
        account_details.append({
            "Nickname": item.nickname,
            "Bank": decrypt_text(item.bank_name_encrypted),
            "Account holder": decrypt_text(item.holder_name_encrypted),
            "Account number": decrypt_text(item.account_number_encrypted),
            "IFSC": decrypt_text(item.ifsc_encrypted),
            "Account type": decrypt_text(item.account_type_encrypted),
            "Branch": decrypt_text(item.branch_encrypted),
            "Primary": item.is_primary,
            "Created": item.created_at,
        })
    st.subheader("Linked bank accounts")
    if account_details:
        st.dataframe(pd.DataFrame(account_details), width="stretch", hide_index=True)
    else:
        st.info("No bank accounts linked for this user.")

    user_transactions = tdf[tdf["user_id"] == selected].sort_values("date", ascending=False) if not tdf.empty else pd.DataFrame()
    if not user_transactions.empty:
        aggregates = user_transactions.groupby("type", as_index=False)["amount"].agg(["sum", "count"]).reset_index()
        st.subheader("User finance aggregates")
        st.dataframe(aggregates, width="stretch", hide_index=True)
        st.dataframe(user_transactions.drop(columns=["user_id"], errors="ignore").head(300), width="stretch", hide_index=True)
    else:
        st.info("No transactions found for this user.")
    if st.button("Record authorized drilldown access", type="primary"):
        with session_scope() as session:
            log_audit(session, "ADMIN_USER_DRILLDOWN", admin_user_id, "USER", str(selected), {"privacy_safe": False, "full_details": True})
        st.success("Authorized access recorded in the audit log.")


def render_settings_page(user_id: int) -> None:
    hero(
        "Preferences and data ownership",
        "Settings",
        "Choose your dashboard defaults, create a private backup, or permanently remove the records owned by your account.",
    )
    with session_scope() as session:
        preferences = get_user_preferences(session, user_id)

    view = st.radio(
        "Settings view",
        ["Preferences", "Data backup", "Delete account"],
        horizontal=True,
        label_visibility="collapsed",
        key="settings_view",
    )

    if view == "Preferences":
        with st.form("user_preferences_form"):
            c1, c2 = st.columns(2)
            currency_options = ["INR", "USD", "EUR", "GBP", "AED"]
            currency = c1.selectbox(
                "Preferred currency",
                currency_options,
                index=currency_options.index(preferences.get("preferred_currency", "INR")) if preferences.get("preferred_currency", "INR") in currency_options else 0,
            )
            scope_options = ["ALL_ACCOUNTS", "PRIMARY_ACCOUNT", "LAST_STATEMENT"]
            scope_labels = {"ALL_ACCOUNTS": "All accounts", "PRIMARY_ACCOUNT": "Primary account", "LAST_STATEMENT": "Latest statement"}
            scope = c2.selectbox(
                "Default dashboard view",
                scope_options,
                format_func=lambda value: scope_labels[value],
                index=scope_options.index(preferences.get("default_dashboard_scope", "ALL_ACCOUNTS")) if preferences.get("default_dashboard_scope") in scope_options else 0,
            )
            risk_options = ["CONSERVATIVE", "MODERATE", "AGGRESSIVE"]
            risk = c1.selectbox(
                "Investment risk preference",
                risk_options,
                format_func=str.title,
                index=risk_options.index(preferences.get("risk_preference", "MODERATE")) if preferences.get("risk_preference") in risk_options else 1,
            )
            horizon_options = ["0-1 YEAR", "1-3 YEARS", "3-5 YEARS", "5-10 YEARS", "10+ YEARS"]
            horizon = c2.selectbox(
                "Investment horizon",
                horizon_options,
                index=horizon_options.index(preferences.get("investment_horizon", "3-5 YEARS")) if preferences.get("investment_horizon") in horizon_options else 2,
            )
            target = c1.number_input(
                "Monthly investment target",
                min_value=0.0,
                value=float(preferences.get("monthly_investment_target", 0.0)),
                step=500.0,
            )
            alerts = c2.checkbox("Enable financial alerts", value=bool(preferences.get("alerts_enabled", True)))
            compact = c2.checkbox("Use compact data tables", value=bool(preferences.get("compact_tables", True)))
            submitted = st.form_submit_button("Save preferences", type="primary", width="stretch")
        if submitted:
            with session_scope() as session:
                save_user_preferences(
                    session,
                    user_id,
                    {
                        "preferred_currency": currency,
                        "default_dashboard_scope": scope,
                        "risk_preference": risk,
                        "investment_horizon": horizon,
                        "monthly_investment_target": target,
                        "alerts_enabled": alerts,
                        "compact_tables": compact,
                    },
                )
            st.success("Preferences saved.")
            st.cache_data.clear()
            st.rerun()
        return

    if view == "Data backup":
        if settings.is_turso:
            st.subheader("Cloud data backup")

            st.info(
            "Your records are stored in the shared cloud database. "
            "A local SQLite database file is not available for download."
            )

            st.success(
            "Use the Reports page to download your transactions and "
            "financial summaries in CSV, Excel, or PDF format."
            )

            st.warning(
            "Complete cloud-database backups are available only through "
            "the Turso dashboard and administrator controls."
            )

            return

        overview = database_overview()

        c1, c2, c3 = st.columns(3)
        c1.metric("Stored sections", overview["tables"])
        c2.metric("Stored rows", f"{overview['rows']:,}")
        c3.metric(
           "Local data size",
         f"{overview['size_bytes'] / 1024 / 1024:.2f} MB",
        )

        st.success("Your local data file passed its integrity check.")

        if st.button(
            "Prepare private data backup",
             width="stretch",
        ):
             with st.spinner("Preparing backup..."):
                   backup_data, backup_name = create_backup_bytes()

                   st.session_state[f"user_data_backup_{user_id}"] = {
                      "data": backup_data,
                      "name": backup_name,
                   }

        prepared_backup = st.session_state.get(
              f"user_data_backup_{user_id}"
        )

        if prepared_backup:
            st.download_button(
                "Download prepared backup",
                prepared_backup["data"],
                prepared_backup["name"],
                "application/octet-stream",
                width="stretch",
           )

        st.info(
            "Keep backup files private. They contain protected account "
            "data and sign-in records."
        )

        return

    st.warning("This action permanently removes your profile, accounts, statements, transactions, budgets, predictions, reports, preferences, and activity history.")
    confirmation = st.text_input("Type DELETE MY ACCOUNT to confirm")
    if st.button("Permanently delete my account", type="primary", disabled=confirmation != "DELETE MY ACCOUNT"):
        with session_scope() as session:
            delete_user_data(session, user_id)
        st.cache_data.clear()
        st.session_state.clear()
        st.rerun()

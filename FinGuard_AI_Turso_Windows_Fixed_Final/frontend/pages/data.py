from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from backend.config import settings
from backend.data_processing import clean_transactions_dataframe, dataframe_to_import_records, detect_columns, read_uploaded_file
from backend.database import session_scope
from backend.models import TransactionType
from backend.services import (
    add_transaction,
    bulk_import_transactions,
    delete_transaction,
    get_categories,
    list_bank_accounts,
    list_statement_imports,
)
from frontend.pages.dashboard import clear_finance_cache, load_user_dataframe
from frontend.theme import hero


@st.cache_data(ttl=120, show_spinner=False, max_entries=100)
def _account_options(user_id: int) -> dict[str, int | None]:
    with session_scope() as session:
        accounts = list_bank_accounts(session, user_id, decrypt=True)
    options: dict[str, int | None] = {"No linked account": None}
    for account in accounts:
        options[f"{account['nickname']} · {account['bank_name']} · ••••{account['last4']}"] = account["id"]
    return options


@st.cache_data(ttl=600, show_spinner=False)
def _category_options() -> dict[str, list[str]]:
    with session_scope() as session:
        return {
            "EXPENSE": [item.name for item in get_categories(session, TransactionType.EXPENSE)],
            "INCOME": [item.name for item in get_categories(session, TransactionType.INCOME)],
            "TRANSFER": [item.name for item in get_categories(session, TransactionType.TRANSFER)],
        }


def _mapping_widget(raw_df: pd.DataFrame) -> dict[str, str]:
    detected = detect_columns(raw_df.columns)
    available = ["Do not use"] + [str(column) for column in raw_df.columns]
    canonical = [
        "transaction_id",
        "transaction_date",
        "description",
        "transaction_type",
        "amount",
        "withdrawal_amount",
        "deposit_amount",
        "balance_after",
        "category",
        "payment_mode",
        "merchant",
    ]
    mapping: dict[str, str] = {}
    columns = st.columns(3)
    for index, field in enumerate(canonical):
        default = detected.get(field, "Do not use")
        selected = columns[index % 3].selectbox(
            field.replace("_", " ").title(),
            available,
            index=available.index(default) if default in available else 0,
            key=f"map_{field}",
        )
        if selected != "Do not use":
            mapping[field] = selected
    return mapping


def _render_upload(user_id: int, account_options: dict[str, int | None]) -> None:
    c1, c2, c3 = st.columns([1.2, 1.1, 0.8])
    selected_account_label = c1.selectbox("Statement belongs to", list(account_options))
    statement_label = c2.text_input("Statement label", placeholder="Salary account · June 2026")
    preview_rows = c3.slider("Preview rows", 10, 100, 25, 5)
    uploaded = st.file_uploader(
        "Upload CSV, Excel or text-based PDF",
        type=["csv", "xlsx", "xls", "pdf"],
        help="CSV and Excel usually provide the cleanest import. Scanned-image PDFs are not supported.",
    )
    if not uploaded:
        st.info("Choose a bank statement to begin. The file is reviewed before any rows are saved.")
        return

    size_mb = float(getattr(uploaded, "size", 0)) / (1024 * 1024)
    if size_mb > settings.max_upload_mb:
        st.error(f"File size is {size_mb:.1f} MB. The current limit is {settings.max_upload_mb} MB.")
        return

    try:
        cache_key = f"raw_statement_{uploaded.name}_{getattr(uploaded, 'size', 0)}"
        if cache_key not in st.session_state:
            with st.spinner("Reading statement..."):
                st.session_state[cache_key] = read_uploaded_file(uploaded)
        raw_df = st.session_state[cache_key]
        st.caption(f"{uploaded.name} · {size_mb:.2f} MB · {len(raw_df):,} rows")

        preview_mode = st.radio(
            "Statement preparation",
            ["Column mapping", "Raw preview"],
            horizontal=True,
            label_visibility="collapsed",
            key="statement_preparation_view",
        )
        if preview_mode == "Column mapping":
            st.caption("Review the detected columns. Date and description are required. Use either Amount or separate debit and credit columns.")
            manual_mapping = _mapping_widget(raw_df)
        else:
            manual_mapping = detect_columns(raw_df.columns)
            st.dataframe(raw_df.head(preview_rows), width="stretch", hide_index=True)

        if st.button("Validate and prepare statement", type="primary", width="stretch"):
            with st.spinner("Checking dates, amounts, categories, and duplicate rows..."):
                cleaned = clean_transactions_dataframe(raw_df, manual_mapping)
            st.session_state.statement_preview = cleaned
            st.session_state.statement_preview_name = uploaded.name
            st.session_state.statement_raw_rows = len(raw_df)
            st.session_state.statement_file_type = uploaded.name.rsplit(".", 1)[-1].upper()
            st.success("Statement prepared. Review the result before importing.")

        cleaned = st.session_state.get("statement_preview")
        same_file = st.session_state.get("statement_preview_name") == uploaded.name
        if not same_file or not isinstance(cleaned, pd.DataFrame):
            return

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Raw rows", st.session_state.get("statement_raw_rows", len(raw_df)))
        m2.metric("Valid rows", len(cleaned))
        m3.metric("Income", int((cleaned["transaction_type"] == "INCOME").sum()))
        m4.metric("Expenses", int((cleaned["transaction_type"] == "EXPENSE").sum()))
        m5.metric("Needs review", int(cleaned.get("is_unusual", pd.Series(dtype=bool)).sum()))
        st.dataframe(cleaned.head(preview_rows), width="stretch", hide_index=True)
        confirm = st.checkbox("I reviewed the prepared statement and want to import it", key="confirm_statement_import")
        if st.button("Import statement", type="primary", width="stretch", disabled=not confirm):
            records = dataframe_to_import_records(cleaned, st.session_state.get("statement_file_type", "FILE"), uploaded.name)
            try:
                with st.spinner("Saving transactions..."):
                    with session_scope() as session:
                        result = bulk_import_transactions(
                            session,
                            user_id,
                            records,
                            bank_account_id=account_options[selected_account_label],
                            file_name=uploaded.name,
                            file_type=st.session_state.get("statement_file_type", "FILE"),
                            raw_rows=int(st.session_state.get("statement_raw_rows", len(raw_df))),
                            statement_label=statement_label or uploaded.name.rsplit(".", 1)[0],
                        )
                clear_finance_cache()
                _account_options.clear()
                st.success(f"Imported {result['imported']:,} transactions and skipped {result['duplicates']:,} duplicates.")
                if result["errors"]:
                    st.warning(f"{len(result['errors'])} row(s) could not be imported. First issue: {result['errors'][0]}")
                for key in ["statement_preview", "statement_preview_name", "statement_raw_rows", "statement_file_type", cache_key]:
                    st.session_state.pop(key, None)
            except (ValueError, PermissionError) as error:
                st.error(str(error))
    except Exception as error:
        st.error(str(error))
        st.info("For a complex PDF, export the statement as CSV or Excel and try again.")


def _render_manual(user_id: int, account_options: dict[str, int | None]) -> None:
    categories = _category_options()
    with st.form("manual_transaction", clear_on_submit=True):
        a, b, c = st.columns(3)
        tx_type = a.selectbox("Type", ["EXPENSE", "INCOME", "TRANSFER"])
        tx_date = b.date_input("Date")
        tx_time = c.time_input("Time")
        transaction_id = st.text_input("Transaction ID / UTR", type="password")
        description = st.text_input("Description")
        amount = st.number_input("Amount", min_value=0.0, step=100.0)
        category = st.selectbox("Category", categories[tx_type])
        d, e = st.columns(2)
        payment_mode = d.selectbox("Payment method", ["UPI", "Card", "Net Banking", "Cash", "ATM", "NEFT/IMPS/RTGS", "Other"])
        merchant = e.text_input("Merchant / payee")
        account_label = st.selectbox("Bank account", list(account_options))
        recurring = st.checkbox("Recurring transaction")
        submitted = st.form_submit_button("Save transaction", type="primary", width="stretch")
    if submitted:
        try:
            with session_scope() as session:
                add_transaction(
                    session,
                    user_id,
                    {
                        "transaction_id": transaction_id,
                        "transaction_date": datetime.combine(tx_date, tx_time),
                        "description": description,
                        "transaction_type": tx_type,
                        "amount": amount,
                        "category": category,
                        "payment_mode": payment_mode,
                        "merchant": merchant,
                        "bank_account_id": account_options[account_label],
                        "is_recurring": recurring,
                        "source": "MANUAL",
                    },
                )
            clear_finance_cache()
            st.success("Transaction saved.")
        except (ValueError, PermissionError) as error:
            st.error(str(error))


def _render_manage(user_id: int) -> None:
    statements_col, transactions_col = st.columns([0.9, 1.1], gap="large")
    with statements_col:
        st.subheader("Imported statements")
        with session_scope() as session:
            statement_rows = list_statement_imports(session, user_id)
        if not statement_rows:
            st.info("No statement imports yet.")
        else:
            statement_df = pd.DataFrame(
                [
                    {
                        "ID": item.id,
                        "Label": item.label,
                        "File": item.file_name,
                        "Period": f"{item.period_start or '—'} to {item.period_end or '—'}",
                        "Imported": item.imported_rows,
                        "Duplicates": item.duplicate_rows,
                        "Status": item.status,
                        "Created": item.created_at,
                    }
                    for item in statement_rows
                ]
            )
            st.dataframe(statement_df, width="stretch", hide_index=True)

    with transactions_col:
        st.subheader("Delete one transaction")
        df = load_user_dataframe(user_id)
        if df.empty:
            st.info("No transactions available.")
            return
        search = st.text_input("Search before deletion", key="delete_tx_search")
        view = df.copy()
        if search:
            pattern = search.lower().strip()
            view = view[
                view["description"].str.lower().str.contains(pattern, na=False)
                | view["merchant"].str.lower().str.contains(pattern, na=False)
                | view["transaction_id_masked"].str.lower().str.contains(pattern, na=False)
            ]
        options = view.head(200)["id"].tolist()
        if not options:
            st.info("No matching transactions.")
            return
        selected_id = st.selectbox(
            "Select transaction",
            options,
            format_func=lambda tx_id: (
                f"{view.loc[view.id == tx_id, 'date'].iloc[0]:%d-%m-%Y} · "
                f"{view.loc[view.id == tx_id, 'description'].iloc[0][:40]} · "
                f"₹{view.loc[view.id == tx_id, 'amount'].iloc[0]:,.2f}"
            ),
        )
        confirm_delete = st.checkbox("I confirm this permanent deletion", key="confirm_delete_transaction")
        if st.button("Delete selected transaction", disabled=not confirm_delete):
            with session_scope() as session:
                deleted = delete_transaction(session, user_id, int(selected_id))
            if deleted:
                clear_finance_cache()
                st.success("Transaction deleted.")
                st.rerun()
            st.error("The transaction was not found or did not belong to your account.")


def _render_template() -> None:
    template = pd.DataFrame(
        [
            {
                "transaction_id": "DEMO-001",
                "transaction_date": "2026-07-01",
                "description": "Salary credit",
                "transaction_type": "INCOME",
                "amount": 45000,
                "balance_after": 62000,
                "category": "Salary",
                "payment_mode": "NEFT/IMPS/RTGS",
                "merchant": "Employer",
            },
            {
                "transaction_id": "DEMO-002",
                "transaction_date": "2026-07-02",
                "description": "Grocery purchase",
                "transaction_type": "EXPENSE",
                "amount": 1850,
                "balance_after": 60150,
                "category": "Groceries",
                "payment_mode": "UPI",
                "merchant": "Supermarket",
            },
        ]
    )
    st.dataframe(template, width="stretch", hide_index=True)
    st.download_button(
        "Download CSV template",
        template.to_csv(index=False).encode("utf-8-sig"),
        "finguard_transaction_template.csv",
        "text/csv",
    )


def render_data_page(user_id: int) -> None:
    hero(
        "Transactions workspace",
        "Bank statements & transactions",
        "Upload a statement, add a transaction, manage saved records, or download a ready-to-use template. Only the selected workspace is loaded.",
    )
    account_options = _account_options(user_id)
    if len(account_options) == 1:
        st.warning("Add a bank account first so statements can be linked and viewed separately.")

    view = st.radio(
        "Transaction workspace",
        ["Upload statement", "Manual entry", "Manage records", "CSV template"],
        horizontal=True,
        label_visibility="collapsed",
        key="transaction_workspace",
    )
    if view == "Upload statement":
        _render_upload(user_id, account_options)
    elif view == "Manual entry":
        _render_manual(user_id, account_options)
    elif view == "Manage records":
        _render_manage(user_id)
    else:
        _render_template()

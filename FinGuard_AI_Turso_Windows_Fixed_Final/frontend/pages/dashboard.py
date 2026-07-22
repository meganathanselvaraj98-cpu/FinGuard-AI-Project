"""Cached, statement-aware user dashboards and interactive analytics."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from backend.analytics import (
    calculate_health_score,
    calculate_kpis,
    category_summary,
    monthly_summary,
    transactions_to_dataframe,
)
from backend.database import session_scope
from backend.eda import (
    category_boxplot_figure,
    correlation_heatmap_figure,
    monthly_expense_figure,
    weekday_amount_figure,
)
from backend.ml_service import detect_anomalies
from backend.services import (
    get_user_preferences,
    list_bank_accounts,
    list_transactions,
)
from frontend.charting import show_chart, show_matplotlib
from frontend.components import metric_card
from frontend.theme import hero


@st.cache_data(ttl=60, show_spinner=False, max_entries=100)
def load_user_dataframe(user_id: int) -> pd.DataFrame:
    with session_scope() as session:
        return transactions_to_dataframe(
            list_transactions(session, user_id)
        )


@st.cache_data(ttl=120, show_spinner=False, max_entries=100)
def load_account_options(user_id: int) -> dict[str, int | None]:
    with session_scope() as session:
        accounts = list_bank_accounts(session, user_id, decrypt=True)

    options: dict[str, int | None] = {"All bank accounts": None}

    for account in accounts:
        label = (
            f"{account['nickname']} · "
            f"{account.get('bank_name', 'Bank')} · "
            f"••••{account['last4']}"
        )
        options[label] = account["id"]

    return options


@st.cache_data(ttl=120, show_spinner=False, max_entries=100)
def load_dashboard_preference(user_id: int) -> str:
    with session_scope() as session:
        return get_user_preferences(session, user_id).get(
            "default_dashboard_scope",
            "ALL_ACCOUNTS",
        )


def clear_finance_cache() -> None:
    load_user_dataframe.clear()
    load_account_options.clear()
    load_dashboard_preference.clear()


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


def _empty_state() -> None:
    st.info(
        "No transactions yet. Add an account and upload a CSV, "
        "Excel, or text-based PDF bank statement."
    )


def scope_switcher(
    user_id: int,
    df: pd.DataFrame,
    key: str,
) -> tuple[pd.DataFrame, str]:
    """Switch between consolidated, per-account, and statement views."""
    choices: dict[str, tuple[str, int | None]] = {
        "Consolidated · All accounts & statements": ("all", None)
    }

    for label, account_id in load_account_options(user_id).items():
        if account_id is not None:
            choices[f"Account · {label}"] = ("account", account_id)

    if not df.empty and "statement_id" in df.columns:
        required = [
            "statement_id",
            "statement_label",
            "account_last4",
        ]
        if all(column in df.columns for column in required):
            statement_rows = (
                df[df["statement_id"].notna()][required]
                .drop_duplicates("statement_id")
                .sort_values("statement_id", ascending=False)
            )

            for _, row in statement_rows.iterrows():
                label = (
                    f"Statement · {row['statement_label']} · "
                    f"••••{row['account_last4']}"
                )
                choices[label] = (
                    "statement",
                    int(row["statement_id"]),
                )

    if (
        not df.empty
        and "source_file_name" in df.columns
        and (df["source_file_name"] == "Manual entries").any()
    ):
        choices["Manual transactions"] = ("manual", None)

    choice_labels = list(choices)
    preference = load_dashboard_preference(user_id)
    default_index = 0

    if preference == "PRIMARY_ACCOUNT":
        default_index = next(
            (
                index
                for index, label in enumerate(choice_labels)
                if label.startswith("Account ·")
            ),
            0,
        )
    elif preference == "LAST_STATEMENT":
        default_index = next(
            (
                index
                for index, label in enumerate(choice_labels)
                if label.startswith("Statement ·")
            ),
            0,
        )

    selected = st.selectbox(
        "Financial view",
        choice_labels,
        index=default_index,
        key=key,
        help=(
            "Switch between all finances, one bank account, "
            "or one uploaded statement."
        ),
    )

    scope, identifier = choices[selected]

    if scope == "account":
        return df[df["account_id"] == identifier].copy(), selected
    if scope == "statement":
        return df[df["statement_id"] == identifier].copy(), selected
    if scope == "manual":
        return (
            df[df["source_file_name"] == "Manual entries"].copy(),
            selected,
        )

    return df.copy(), selected


def filter_dataframe(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    if df.empty:
        return df

    min_date = df["date"].min().date()
    max_date = df["date"].max().date()

    c1, c2, c3, c4 = st.columns([1.05, 1.05, 1.55, 1.75])

    start = c1.date_input(
        "From",
        min_date,
        min_value=min_date,
        max_value=max_date,
        key=f"{prefix}_start",
    )
    end = c2.date_input(
        "To",
        max_date,
        min_value=min_date,
        max_value=max_date,
        key=f"{prefix}_end",
    )

    categories = sorted(df["category"].dropna().unique())
    selected_categories = c3.multiselect(
        "Categories",
        categories,
        default=categories,
        key=f"{prefix}_categories",
    )
    search = c4.text_input(
        "Search merchant / description",
        key=f"{prefix}_search",
        placeholder="Amazon, salary, rent...",
    )

    if start > end:
        st.warning("From date must be before To date.")
        return df.iloc[0:0]

    output = df[
        (df["date"].dt.date >= start)
        & (df["date"].dt.date <= end)
    ]

    if selected_categories:
        output = output[
            output["category"].isin(selected_categories)
        ]

    if search.strip():
        pattern = search.strip().lower()

        description_match = (
            output["description"]
            .astype(str)
            .str.lower()
            .str.contains(pattern, na=False, regex=False)
        )
        merchant_match = (
            output["merchant"]
            .astype(str)
            .str.lower()
            .str.contains(pattern, na=False, regex=False)
        )
        transaction_match = (
            output["transaction_id_masked"]
            .astype(str)
            .str.lower()
            .str.contains(pattern, na=False, regex=False)
        )

        output = output[
            description_match | merchant_match | transaction_match
        ]

    return output


def render_dashboard_page(user_id: int, user_name: str) -> None:
    hero(
        "Financial overview",
        f"Welcome back, {user_name.split()[0]}.",
        (
            "Choose an account or statement, review your key numbers, "
            "and open only the chart section you need for a faster "
            "experience."
        ),
    )

    df = load_user_dataframe(user_id)
    if df.empty:
        _empty_state()
        return

    scoped, scope_label = scope_switcher(
        user_id,
        df,
        "dashboard_scope",
    )
    st.caption(f"Showing: {scope_label}")

    filtered = filter_dataframe(scoped, "dashboard")
    if filtered.empty:
        st.warning("No transactions match the selected filters.")
        return

    kpis = calculate_kpis(filtered)
    score, _ = calculate_health_score(filtered)
    cards = st.columns(6)

    values = [
        ("Income", f"₹{kpis['income']:,.0f}", "Credits in selected view"),
        ("Expenses", f"₹{kpis['expense']:,.0f}", "Debits in selected view"),
        (
            "Net savings",
            f"₹{kpis['savings']:,.0f}",
            f"{kpis['savings_rate']:.1f}% savings rate",
        ),
        (
            "Current balance",
            f"₹{kpis['balance']:,.0f}",
            "Latest available balance",
        ),
        ("Health score", f"{score}/100", "Overall financial position"),
        (
            "Transactions",
            f"{int(kpis['transactions']):,}",
            "Filtered records",
        ),
    ]

    for column, item in zip(cards, values):
        with column:
            metric_card(*item)

    section = st.radio(
        "Dashboard section",
        ["Overview", "Spending", "Cash flow", "Recent transactions"],
        horizontal=True,
        label_visibility="collapsed",
        key="dashboard_section",
    )

    monthly = monthly_summary(filtered)
    expenses = filtered[filtered["type"] == "EXPENSE"].copy()

    if section == "Overview":
        left, right = st.columns([1.45, 1], gap="large")
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=monthly["month"],
                y=monthly["income"],
                mode="lines+markers",
                name="Income",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=monthly["month"],
                y=monthly["expense"],
                mode="lines+markers",
                name="Expense",
            )
        )
        fig.add_trace(
            go.Bar(
                x=monthly["month"],
                y=monthly["savings"],
                name="Savings",
                opacity=0.45,
            )
        )
        fig.update_layout(
            title="Monthly income, expense and savings",
            hovermode="x unified",
        )
        show_chart(_style(fig, 410), container=left)

        category = category_summary(filtered).head(10)
        if category.empty:
            right.info("No expense categories in this view.")
        else:
            category_chart = px.pie(
                category,
                names="category",
                values="total",
                hole=0.52,
                title="Expense distribution",
            )
            show_chart(_style(category_chart, 410), container=right)

    elif section == "Spending":
        c1, c2, c3 = st.columns(3)

        weekday = (
            expenses.groupby("weekday", as_index=False)["amount"]
            .sum()
        )
        order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        weekday["weekday"] = pd.Categorical(
            weekday["weekday"],
            order,
            ordered=True,
        )
        weekday_chart = px.bar(
            weekday.sort_values("weekday"),
            x="weekday",
            y="amount",
            title="Spending by weekday",
        )
        show_chart(_style(weekday_chart, 350), container=c1)

        modes = (
            expenses.groupby("payment_mode", as_index=False)["amount"]
            .sum()
            .sort_values("amount")
        )
        payment_chart = px.bar(
            modes,
            x="amount",
            y="payment_mode",
            orientation="h",
            title="Payment method mix",
        )
        show_chart(_style(payment_chart, 350), container=c2)

        merchants = (
            expenses.groupby("merchant", as_index=False)["amount"]
            .sum()
            .nlargest(10, "amount")
            .sort_values("amount")
        )
        merchant_chart = px.bar(
            merchants,
            x="amount",
            y="merchant",
            orientation="h",
            title="Top merchants",
        )
        show_chart(_style(merchant_chart, 350), container=c3)

    elif section == "Cash flow":
        c1, c2 = st.columns(2)

        cash_flow_chart = px.area(
            monthly,
            x="month",
            y="cash_flow",
            title="Cumulative cash flow",
        )
        show_chart(_style(cash_flow_chart, 390), container=c1)

        savings_rate_chart = px.bar(
            monthly,
            x="month",
            y="savings_rate",
            title="Monthly savings rate",
        )
        show_chart(_style(savings_rate_chart, 390), container=c2)

        balance = (
            filtered.dropna(subset=["balance_after"])
            .sort_values("date")
        )
        if not balance.empty:
            balance_chart = px.area(
                balance,
                x="date",
                y="balance_after",
                title="Reported balance trend",
            )
            show_chart(_style(balance_chart, 360))

    else:
        recent_columns = [
            "date",
            "transaction_id_masked",
            "description",
            "category",
            "type",
            "amount",
            "payment_mode",
            "merchant",
            "statement_label",
        ]
        available_columns = [
            column
            for column in recent_columns
            if column in filtered.columns
        ]

        st.dataframe(
            filtered.sort_values("date", ascending=False)[available_columns]
            .head(100),
            width="stretch",
            hide_index=True,
        )

    high_risk = filtered[
        filtered["risk_level"].isin(["HIGH", "CRITICAL"])
        | filtered["is_unusual"]
    ]
    if not high_risk.empty:
        st.warning(
            f"{len(high_risk)} transaction(s) need attention. "
            "Open Insights → Predictions → Unusual activity for details."
        )


def render_analytics_page(user_id: int) -> None:
    hero(
        "Deep analytics",
        "Explore your financial behaviour",
        (
            "Open one focused view at a time for faster trends, "
            "categories, behaviour, risk, and statistical analysis."
        ),
    )

    df = load_user_dataframe(user_id)
    if df.empty:
        _empty_state()
        return

    scoped, scope_label = scope_switcher(
        user_id,
        df,
        "analytics_scope",
    )
    st.caption(f"Showing: {scope_label}")

    filtered = filter_dataframe(scoped, "analytics")
    if filtered.empty:
        st.warning("No transactions match the selected filters.")
        return

    view = st.radio(
        "Analytics view",
        [
            "Trends",
            "Categories",
            "Behaviour",
            "Risk & anomaly",
            "Statistical views",
        ],
        horizontal=True,
        label_visibility="collapsed",
        key="analytics_view",
    )

    expense = filtered[filtered["type"] == "EXPENSE"].copy()
    monthly = monthly_summary(filtered)

    if view == "Trends":
        c1, c2 = st.columns(2)

        trend = px.line(
            monthly,
            x="month",
            y=["income", "expense", "savings"],
            markers=True,
            title="Monthly financial trend",
        )
        trend.update_layout(hovermode="x unified")
        show_chart(_style(trend, 390), container=c1)

        cash_flow_chart = px.bar(
            monthly,
            x="month",
            y="cash_flow",
            title="Cash-flow progression",
        )
        show_chart(_style(cash_flow_chart, 390), container=c2)

        c3, c4 = st.columns(2)

        balance = (
            filtered.dropna(subset=["balance_after"])
            .sort_values("date")
        )
        if not balance.empty:
            balance_chart = px.area(
                balance,
                x="date",
                y="balance_after",
                title="Reported bank balance trend",
            )
            show_chart(_style(balance_chart, 360), container=c3)

        savings_chart = px.bar(
            monthly,
            x="month",
            y="savings_rate",
            title="Monthly savings rate",
        )
        show_chart(_style(savings_chart, 360), container=c4)

    elif view == "Categories":
        categories = category_summary(filtered)
        if categories.empty:
            st.info(
                "No expense categories are available for the selected filters."
            )
            return

        c1, c2 = st.columns(2)

        treemap_chart = px.treemap(
            categories,
            path=["category"],
            values="total",
            color="average",
            title="Category treemap",
        )
        show_chart(_style(treemap_chart, 420), container=c1)

        category_scatter = px.scatter(
            categories,
            x="count",
            y="total",
            size="average",
            color="share_percent",
            hover_name="category",
            title="Frequency vs total spend",
        )
        show_chart(_style(category_scatter, 420), container=c2)

        pareto = categories.copy()
        pareto["cumulative_share"] = pareto["share_percent"].cumsum()

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=pareto["category"],
                y=pareto["total"],
                name="Expense",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=pareto["category"],
                y=pareto["cumulative_share"],
                name="Cumulative %",
                yaxis="y2",
                mode="lines+markers",
            )
        )
        fig.update_layout(
            title="Category Pareto analysis",
            yaxis2=dict(
                overlaying="y",
                side="right",
                range=[0, 110],
                title="Cumulative %",
            ),
        )
        show_chart(_style(fig, 400))

    elif view == "Behaviour":
        c1, c2 = st.columns(2)

        histogram = px.histogram(
            expense,
            x="amount",
            nbins=30,
            marginal="box",
            title="Expense amount distribution",
        )
        show_chart(_style(histogram, 390), container=c1)

        merchants = (
            expense.groupby("merchant", as_index=False)["amount"]
            .sum()
            .nlargest(15, "amount")
        )
        merchant_chart = px.bar(
            merchants.sort_values("amount"),
            x="amount",
            y="merchant",
            orientation="h",
            title="Top merchants",
        )
        show_chart(_style(merchant_chart, 390), container=c2)

        c3, c4 = st.columns(2)

        hour_weekday = expense.pivot_table(
            index="weekday",
            columns="hour",
            values="amount",
            aggfunc="sum",
            fill_value=0,
        )
        order = [
            day
            for day in [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            if day in hour_weekday.index
        ]
        hour_weekday = hour_weekday.reindex(order)

        heatmap = px.imshow(
            hour_weekday,
            aspect="auto",
            title="Spending time heatmap",
        )
        show_chart(_style(heatmap, 390), container=c3)

        source = (
            filtered.groupby("source_file_name", as_index=False)
            .agg(
                transactions=("id", "size"),
                amount=("amount", "sum"),
            )
            .nlargest(15, "transactions")
        )
        source_chart = px.bar(
            source,
            x="source_file_name",
            y="transactions",
            hover_data=["amount"],
            title="Statement activity",
        )
        show_chart(_style(source_chart, 390), container=c4)

    elif view == "Risk & anomaly":
        try:
            anomalies = detect_anomalies(filtered, user_id)
        except Exception as error:
            st.error(f"Unable to analyse risk and anomalies: {error}")
            return

        if anomalies is None or anomalies.empty:
            st.info("No anomaly-analysis results are available.")
            return

        numeric_columns = [
            column
            for column in ["amount", "balance_after", "day", "hour"]
            if column in filtered.columns
        ]

        c1, c2 = st.columns(2)

        if len(numeric_columns) >= 2:
            numeric = (
                filtered[numeric_columns]
                .apply(pd.to_numeric, errors="coerce")
                .corr(numeric_only=True)
            )
            correlation_chart = px.imshow(
                numeric,
                text_auto=True,
                title="Correlation matrix",
            )
            show_chart(_style(correlation_chart, 390), container=c1)
        else:
            c1.info("Not enough numeric columns for the correlation matrix.")

        anomaly_plot = anomalies.copy()

        if "anomaly_score" not in anomaly_plot.columns:
            anomaly_plot["anomaly_score"] = 0.0

        anomaly_plot["anomaly_score"] = pd.to_numeric(
            anomaly_plot["anomaly_score"],
            errors="coerce",
        ).fillna(0.0)

        score_strength = anomaly_plot["anomaly_score"].abs()
        maximum_score = (
            float(score_strength.max())
            if not score_strength.empty
            else 0.0
        )

        if pd.isna(maximum_score) or maximum_score <= 0:
            anomaly_plot["marker_size"] = 12.0
        else:
            anomaly_plot["marker_size"] = (
                8.0 + (score_strength / maximum_score) * 24.0
            ).clip(lower=8.0, upper=32.0)

        anomaly_plot["anomaly_strength"] = score_strength

        if "risk_level" not in anomaly_plot.columns:
            anomaly_plot["risk_level"] = "UNKNOWN"
        if "ml_anomaly" not in anomaly_plot.columns:
            anomaly_plot["ml_anomaly"] = False

        anomaly_plot["ml_anomaly"] = (
            anomaly_plot["ml_anomaly"]
            .fillna(False)
            .astype(bool)
        )

        hover_information = {
            "anomaly_score": ":.4f",
            "anomaly_strength": ":.4f",
            "marker_size": False,
        }

        for column in [
            "description",
            "merchant",
            "statement_label",
            "category",
        ]:
            if column in anomaly_plot.columns:
                hover_information[column] = True

        risk_chart = px.scatter(
            anomaly_plot,
            x="date",
            y="amount",
            color="risk_level",
            symbol="ml_anomaly",
            size="marker_size",
            size_max=32,
            hover_data=hover_information,
            title="Transaction risk and unusual activity",
            labels={
                "date": "Transaction date",
                "amount": "Transaction amount",
                "risk_level": "Risk level",
                "ml_anomaly": "Unusual transaction",
            },
        )

        risk_chart.update_traces(
            marker=dict(
                opacity=0.82,
                line=dict(width=1),
            )
        )

        show_chart(_style(risk_chart, 390), container=c2)

        risk = (
            anomaly_plot.groupby(
                ["risk_level", "ml_anomaly"],
                as_index=False,
            )
            .size()
        )
        risk_distribution = px.bar(
            risk,
            x="risk_level",
            y="size",
            color="ml_anomaly",
            barmode="group",
            title="Risk distribution and unusual activity",
        )
        show_chart(_style(risk_distribution, 360))

        flagged = anomaly_plot[
            anomaly_plot["ml_anomaly"]
            | anomaly_plot["risk_level"].isin(["HIGH", "CRITICAL"])
        ].copy()

        if flagged.empty:
            st.success("No high-risk or unusual transactions were detected.")
        else:
            preferred_columns = [
                "date",
                "transaction_id_masked",
                "description",
                "category",
                "amount",
                "risk_level",
                "anomaly_score",
            ]
            display_columns = [
                column
                for column in preferred_columns
                if column in flagged.columns
            ]

            flagged = flagged.sort_values(
                "anomaly_strength",
                ascending=False,
            )

            st.dataframe(
                flagged[display_columns],
                width="stretch",
                hide_index=True,
            )
            st.warning(
                "An unusual transaction is a statistical outlier, "
                "not proof of fraud."
            )

    else:
        c1, c2 = st.columns(2)

        show_matplotlib(
            monthly_expense_figure(filtered),
            "Monthly expense analysis",
            container=c1,
            key="download_monthly_expense",
        )
        show_matplotlib(
            weekday_amount_figure(filtered),
            "Weekday spending analysis",
            container=c2,
            key="download_weekday_spending",
        )

        c3, c4 = st.columns(2)

        show_matplotlib(
            category_boxplot_figure(filtered),
            "Category amount comparison",
            container=c3,
            key="download_category_boxplot",
        )
        show_matplotlib(
            correlation_heatmap_figure(filtered),
            "Financial correlation heatmap",
            container=c4,
            key="download_correlation_heatmap",
        )
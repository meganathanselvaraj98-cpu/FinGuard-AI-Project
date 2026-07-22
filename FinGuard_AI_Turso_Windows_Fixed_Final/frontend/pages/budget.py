"""Interactive budget creation, recommendations, variance analysis, and alerts."""
from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frontend.charting import show_chart

from backend.database import session_scope
from backend.services import list_budgets, upsert_budget
from frontend.pages.dashboard import load_user_dataframe
from frontend.theme import hero


def _style(fig, height: int = 390):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin=dict(l=20, r=20, t=55, b=25),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(5,11,20,.35)",
        legend_title_text="",
    )
    return fig


def _recommended_budgets(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["category", "average_spend", "recommended_budget"])
    expenses = df[df["type"] == "EXPENSE"].copy()
    if expenses.empty:
        return pd.DataFrame(columns=["category", "average_spend", "recommended_budget"])
    monthly = expenses.groupby(["month", "category"], as_index=False)["amount"].sum()
    last_months = sorted(monthly["month"].unique())[-3:]
    summary = monthly[monthly["month"].isin(last_months)].groupby("category", as_index=False)["amount"].mean()
    summary = summary.rename(columns={"amount": "average_spend"})
    summary["recommended_budget"] = (summary["average_spend"] * 0.95).round(-1).clip(lower=100)
    return summary.sort_values("recommended_budget", ascending=False)


def render_budget_page(user_id: int) -> None:
    hero(
        "Planning & control",
        "Smart monthly budget planner",
        "Create category limits, compare actual spending, receive threshold alerts, and use recent history to generate practical budget targets.",
    )
    df = load_user_dataframe(user_id)
    recommendations = _recommended_budgets(df)
    expense_categories = sorted(df.loc[df["type"] == "EXPENSE", "category"].dropna().unique().tolist()) if not df.empty else []
    if not expense_categories:
        expense_categories = ["Food & Dining", "Groceries", "Transport", "Housing", "Utilities", "Entertainment", "Shopping", "Subscriptions", "Healthcare", "Other Expense"]

    with st.expander("AI-assisted budget suggestions", expanded=not recommendations.empty):
        if recommendations.empty:
            st.info("Upload at least one month of expenses to receive history-based budget suggestions.")
        else:
            st.caption("Suggested target is approximately 5% below the recent three-month average. Adjust it to match your real commitments.")
            st.dataframe(recommendations.head(12), width="stretch", hide_index=True)

    left, right = st.columns([0.85, 1.35], gap="large")
    with left:
        st.subheader("Create or update a budget")
        with st.form("budget_form"):
            category = st.selectbox("Expense category", expense_categories)
            month = st.date_input("Budget month", date.today().replace(day=1))
            suggested = 0.0
            if not recommendations.empty and category in recommendations["category"].values:
                suggested = float(recommendations.loc[recommendations["category"] == category, "recommended_budget"].iloc[0])
            amount = st.number_input("Allocated amount", min_value=100.0, value=max(100.0, suggested), step=500.0)
            threshold = st.slider("Alert threshold", 50, 100, 80, help="Show a warning when this percentage of the budget is used.")
            submitted = st.form_submit_button("Save budget", type="primary", width="stretch")
        if submitted:
            with session_scope() as session:
                upsert_budget(session, user_id, category, month, amount, threshold)
            st.cache_data.clear()
            st.success("Budget saved successfully.")
            st.rerun()

    with right:
        with session_scope() as session:
            budgets = list_budgets(session, user_id)
        if not budgets:
            st.info("No budgets created yet. Save the first category budget from the form.")
            return
        budget_df = pd.DataFrame([
            {
                "category": item.category_name,
                "month": pd.Timestamp(item.budget_month).strftime("%Y-%m"),
                "budget": float(item.allocated_amount),
                "threshold": float(item.alert_threshold_percent),
            }
            for item in budgets
        ])
        selected_month = st.selectbox("View month", sorted(budget_df["month"].unique(), reverse=True))
        current = budget_df[budget_df["month"] == selected_month].copy()
        actual = pd.DataFrame(columns=["category", "spent"])
        if not df.empty:
            actual = (
                df[(df["type"] == "EXPENSE") & (df["month"] == selected_month)]
                .groupby("category", as_index=False)["amount"]
                .sum()
                .rename(columns={"amount": "spent"})
            )
        current = current.merge(actual, on="category", how="left")
        current["spent"] = current["spent"].fillna(0.0)
        current["utilization_percent"] = (current["spent"] / current["budget"] * 100).round(1)
        current["remaining"] = (current["budget"] - current["spent"]).round(2)
        current["status"] = current.apply(
            lambda row: "Over budget" if row["utilization_percent"] > 100 else ("Warning" if row["utilization_percent"] >= row["threshold"] else "Healthy"),
            axis=1,
        )

        total_budget = float(current["budget"].sum())
        total_spent = float(current["spent"].sum())
        utilization = total_spent / total_budget * 100 if total_budget else 0.0
        m1, m2, m3 = st.columns(3)
        m1.metric("Total budget", f"₹{total_budget:,.0f}")
        m2.metric("Spent", f"₹{total_spent:,.0f}")
        m3.metric("Remaining", f"₹{total_budget-total_spent:,.0f}", f"{utilization:.1f}% used")

        fig = px.bar(current, x="category", y=["budget", "spent"], barmode="group", title=f"Budget vs actual · {selected_month}")
        show_chart(_style(fig))

        g1, g2 = st.columns([0.7, 1.3])
        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=utilization,
            number={"suffix": "%"},
            title={"text": "Overall utilization"},
            gauge={"axis": {"range": [0, 120]}, "bar": {"color": "#36D399"}, "steps": [{"range": [80, 100], "color": "#3a2e0d"}, {"range": [100, 120], "color": "#421717"}]},
        ))
        show_chart(_style(gauge, 330), container=g1)
        status_count = current.groupby("status", as_index=False).size()
        show_chart(_style(px.pie(status_count, names="status", values="size", hole=0.5, title="Budget health"), 330), container=g2)

        st.dataframe(current.round(2), width="stretch", hide_index=True)
        for _, row in current[current["status"].isin(["Warning", "Over budget"])].iterrows():
            if row["status"] == "Over budget":
                st.error(f"{row['category']} is over budget by ₹{abs(row['remaining']):,.0f}.")
            else:
                st.warning(f"{row['category']} reached {row['utilization_percent']:.1f}% of its budget.")

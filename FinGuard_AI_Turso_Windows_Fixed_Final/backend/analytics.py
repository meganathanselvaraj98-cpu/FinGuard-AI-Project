"""Financial analytics, scoring, recurring-payment detection, and advisor rules."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from backend.security import decrypt_text, mask_transaction_id


TRANSACTION_COLUMNS = [
    "id",
    "transaction_id",
    "transaction_id_masked",
    "date",
    "description",
    "type",
    "amount",
    "balance_after",
    "category",
    "payment_mode",
    "merchant",
    "is_recurring",
    "is_unusual",
    "risk_level",
    "source",
    "source_file_name",
    "statement_id",
    "statement_label",
    "account_id",
    "account_last4",
]


def transactions_to_dataframe(transactions) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for tx in transactions:
        transaction_id = decrypt_text(tx.transaction_id_encrypted) or ""
        rows.append(
            {
                "id": tx.id,
                "transaction_id": transaction_id,
                "transaction_id_masked": mask_transaction_id(transaction_id),
                "date": pd.Timestamp(tx.transaction_date),
                "description": tx.description,
                "type": tx.transaction_type.value,
                "amount": float(tx.amount),
                "balance_after": float(tx.balance_after) if tx.balance_after is not None else np.nan,
                "category": tx.category.name if tx.category else "Uncategorized",
                "payment_mode": tx.payment_mode or "Unknown",
                "merchant": tx.merchant or "Unknown",
                "is_recurring": bool(tx.is_recurring),
                "is_unusual": bool(tx.is_unusual),
                "risk_level": tx.risk_level or "LOW",
                "source": tx.source or "MANUAL",
                "source_file_name": tx.source_file_name or "Manual entries",
                "statement_id": tx.statement_import_id,
                "statement_label": tx.statement.label if tx.statement else (tx.source_file_name or "Manual entries"),
                "account_id": tx.bank_account_id,
                "account_last4": tx.account.account_last4 if tx.account else "Unlinked",
            }
        )
    if not rows:
        return pd.DataFrame(columns=TRANSACTION_COLUMNS + ["month", "weekday", "day", "hour", "signed_amount"])

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values(["date", "id"], ascending=[False, False]).reset_index(drop=True)
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["weekday"] = df["date"].dt.day_name()
    df["day"] = df["date"].dt.day
    df["hour"] = df["date"].dt.hour
    df["signed_amount"] = np.select(
        [df["type"].eq("INCOME"), df["type"].eq("EXPENSE")],
        [df["amount"], -df["amount"]],
        default=0.0,
    )
    return df


def calculate_kpis(df: pd.DataFrame) -> dict[str, float]:
    if df.empty:
        return {
            "income": 0.0,
            "expense": 0.0,
            "savings": 0.0,
            "savings_rate": 0.0,
            "balance": 0.0,
            "transactions": 0.0,
            "average_expense": 0.0,
            "largest_expense": 0.0,
        }
    income = float(df.loc[df["type"] == "INCOME", "amount"].sum())
    expense_rows = df.loc[df["type"] == "EXPENSE", "amount"]
    expense = float(expense_rows.sum())
    savings = income - expense
    savings_rate = (savings / income * 100) if income > 0 else 0.0
    chronological = df.sort_values("date", ascending=False)
    non_null_balance = chronological["balance_after"].dropna()
    balance = float(non_null_balance.iloc[0]) if not non_null_balance.empty else savings
    return {
        "income": income,
        "expense": expense,
        "savings": savings,
        "savings_rate": savings_rate,
        "balance": balance,
        "transactions": float(len(df)),
        "average_expense": float(expense_rows.mean()) if not expense_rows.empty else 0.0,
        "largest_expense": float(expense_rows.max()) if not expense_rows.empty else 0.0,
    }


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["month", "income", "expense", "transfer", "savings", "cash_flow", "savings_rate"])
    work = df.copy()
    if "month" not in work:
        work["month"] = pd.to_datetime(work["date"]).dt.to_period("M").astype(str)
    pivot = (
        work.pivot_table(index="month", columns="type", values="amount", aggfunc="sum", fill_value=0)
        .reset_index()
        .sort_values("month")
    )
    pivot["income"] = pivot["INCOME"] if "INCOME" in pivot else 0.0
    pivot["expense"] = pivot["EXPENSE"] if "EXPENSE" in pivot else 0.0
    pivot["transfer"] = pivot["TRANSFER"] if "TRANSFER" in pivot else 0.0
    pivot["savings"] = pivot["income"] - pivot["expense"]
    pivot["cash_flow"] = pivot["savings"].cumsum()
    pivot["savings_rate"] = np.where(pivot["income"] > 0, pivot["savings"] / pivot["income"] * 100, 0.0)
    return pivot[["month", "income", "expense", "transfer", "savings", "cash_flow", "savings_rate"]]


def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    expenses = df[df["type"] == "EXPENSE"] if not df.empty else df
    if expenses.empty:
        return pd.DataFrame(columns=["category", "total", "average", "count", "share_percent"])
    result = expenses.groupby("category", as_index=False).agg(
        total=("amount", "sum"),
        average=("amount", "mean"),
        count=("amount", "size"),
    )
    total = max(float(result["total"].sum()), 1.0)
    result["share_percent"] = result["total"] / total * 100
    return result.sort_values("total", ascending=False)


def calculate_health_score(df: pd.DataFrame, budgets_df: pd.DataFrame | None = None) -> tuple[int, dict[str, float]]:
    if df.empty:
        return 0, {"savings": 0, "stability": 0, "budget": 0, "risk": 0, "diversification": 0}
    kpis = calculate_kpis(df)
    savings_component = float(np.clip((kpis["savings_rate"] + 5) / 25 * 30, 0, 30))
    monthly = monthly_summary(df)
    if len(monthly) >= 2 and monthly["expense"].mean() > 0:
        cv = float(monthly["expense"].std(ddof=0) / monthly["expense"].mean())
        stability_component = float(np.clip(20 * (1 - cv), 0, 20))
    else:
        stability_component = 10.0
    budget_component = 15.0
    if budgets_df is not None and not budgets_df.empty:
        budget_component = float((budgets_df["spent"] <= budgets_df["budget"]).mean()) * 20
    risky = int(df["risk_level"].isin(["HIGH", "CRITICAL"]).sum()) + int(df["is_unusual"].sum())
    risk_component = float(np.clip(20 * (1 - (risky / max(len(df), 1)) * 4), 0, 20))
    diversification_component = float(np.clip(df.loc[df["type"] == "EXPENSE", "category"].nunique() / 8 * 10, 0, 10))
    score = int(round(savings_component + stability_component + budget_component + risk_component + diversification_component))
    return int(np.clip(score, 0, 100)), {
        "savings": round(savings_component, 1),
        "stability": round(stability_component, 1),
        "budget": round(budget_component, 1),
        "risk": round(risk_component, 1),
        "diversification": round(diversification_component, 1),
    }


def detect_subscription_candidates(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["merchant", "months", "transactions", "average_amount", "amount_variation", "estimated_annual_cost"])
    expenses = df[df["type"] == "EXPENSE"].copy()
    if expenses.empty:
        return pd.DataFrame(columns=["merchant", "months", "transactions", "average_amount", "amount_variation", "estimated_annual_cost"])
    expenses["merchant_key"] = expenses["merchant"].replace("Unknown", "").fillna("").str.strip()
    expenses.loc[expenses["merchant_key"].eq(""), "merchant_key"] = expenses["description"].str.slice(0, 40)
    grouped = expenses.groupby("merchant_key").agg(
        months=("month", "nunique"),
        transactions=("amount", "size"),
        average_amount=("amount", "mean"),
        amount_variation=("amount", "std"),
    ).reset_index().rename(columns={"merchant_key": "merchant"})
    grouped["amount_variation"] = grouped["amount_variation"].fillna(0)
    grouped = grouped[(grouped["months"] >= 3) & (grouped["transactions"] >= 3)]
    grouped["estimated_annual_cost"] = grouped["average_amount"] * 12
    return grouped.sort_values("estimated_annual_cost", ascending=False)


def generate_advice(df: pd.DataFrame, health_score: int) -> list[dict[str, str]]:
    if df.empty:
        return [{"level": "info", "title": "Upload transaction history", "message": "Add at least three months of transactions to unlock meaningful insights and forecasts."}]
    advice: list[dict[str, str]] = []
    kpis = calculate_kpis(df)
    expense_df = df[df["type"] == "EXPENSE"]
    if kpis["savings_rate"] < 0:
        advice.append({"level": "error", "title": "Negative cash flow", "message": f"Expenses exceed income by ₹{abs(kpis['savings']):,.0f}. Pause discretionary spending and review high-cost categories first."})
    elif kpis["savings_rate"] < 10:
        advice.append({"level": "warning", "title": "Low savings rate", "message": f"Your savings rate is {kpis['savings_rate']:.1f}%. Start with a 10% automatic transfer immediately after income is received."})
    elif kpis["savings_rate"] >= 20:
        advice.append({"level": "success", "title": "Healthy savings momentum", "message": "Your savings rate is above 20%. Maintain an emergency reserve before increasing long-term investments."})
    if not expense_df.empty:
        category_spend = expense_df.groupby("category")["amount"].sum().sort_values(ascending=False)
        share = category_spend.iloc[0] / max(category_spend.sum(), 1) * 100
        advice.append({"level": "info", "title": f"Review {category_spend.index[0]}", "message": f"This category represents {share:.1f}% of expenses. A 5–10% reduction could improve monthly cash flow."})
    subscriptions = detect_subscription_candidates(df)
    if not subscriptions.empty:
        advice.append({"level": "warning", "title": "Recurring payment review", "message": f"Potential recurring payments total approximately ₹{subscriptions['estimated_annual_cost'].sum():,.0f} per year. Cancel services that are no longer used."})
    risky = int(df["risk_level"].isin(["HIGH", "CRITICAL"]).sum()) + int(df["is_unusual"].sum())
    if risky:
        advice.append({"level": "error", "title": "Risk alert", "message": f"{risky} unusual or high-risk transaction(s) require verification. Contact the bank if any transaction is unrecognized."})
    if health_score < 50:
        advice.append({"level": "warning", "title": "Build the foundation first", "message": "Prioritize expense control, high-interest debt repayment, and a 3–6 month emergency fund before market-linked investing."})
    else:
        advice.append({"level": "info", "title": "Investment readiness checkpoint", "message": "After emergency savings and insurance are adequate, consider diversified, low-cost investments aligned with your time horizon and risk tolerance. This is educational guidance, not individualized financial advice."})
    return advice

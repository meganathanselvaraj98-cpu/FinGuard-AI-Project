"""Matplotlib and Seaborn exploratory-data-analysis figures."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def _base_figure(figsize=(10, 5)):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("#07111f")
    ax.set_facecolor("#0b1726")
    ax.tick_params(colors="#dbe8f5")
    ax.xaxis.label.set_color("#dbe8f5")
    ax.yaxis.label.set_color("#dbe8f5")
    ax.title.set_color("#ffffff")
    for spine in ax.spines.values():
        spine.set_color("#2b4a69")
    return fig, ax


def monthly_expense_figure(df: pd.DataFrame):
    fig, ax = _base_figure()
    expenses = df[df["type"] == "EXPENSE"].copy()
    if not expenses.empty:
        monthly = expenses.groupby("month", as_index=False)["amount"].sum()
        sns.lineplot(data=monthly, x="month", y="amount", marker="o", ax=ax)
        ax.tick_params(axis="x", rotation=35)
    ax.set_title("Monthly Expense Trend — Seaborn")
    ax.set_xlabel("Month")
    ax.set_ylabel("Expense (INR)")
    fig.tight_layout()
    return fig


def category_boxplot_figure(df: pd.DataFrame):
    fig, ax = _base_figure((11, 5.5))
    expenses = df[df["type"] == "EXPENSE"].copy()
    top = expenses.groupby("category")["amount"].sum().nlargest(10).index if not expenses.empty else []
    plot_df = expenses[expenses["category"].isin(top)]
    if not plot_df.empty:
        sns.boxplot(data=plot_df, x="category", y="amount", ax=ax)
        ax.tick_params(axis="x", rotation=35)
    ax.set_title("Expense Distribution by Category — Seaborn")
    ax.set_xlabel("Category")
    ax.set_ylabel("Transaction amount (INR)")
    fig.tight_layout()
    return fig


def correlation_heatmap_figure(df: pd.DataFrame):
    fig, ax = _base_figure((7.5, 5.5))
    work = df.copy()
    work["is_expense"] = (work["type"] == "EXPENSE").astype(int)
    work["is_income"] = (work["type"] == "INCOME").astype(int)
    numeric = work[["amount", "balance_after", "day", "hour", "is_expense", "is_income"]].corr(numeric_only=True)
    if not numeric.empty:
        sns.heatmap(numeric, annot=True, fmt=".2f", cmap="viridis", ax=ax, cbar=True)
    ax.set_title("Correlation Matrix — Seaborn")
    fig.tight_layout()
    return fig


def weekday_amount_figure(df: pd.DataFrame):
    fig, ax = _base_figure((9, 4.8))
    expenses = df[df["type"] == "EXPENSE"].copy()
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if not expenses.empty:
        sns.barplot(data=expenses, x="weekday", y="amount", estimator="sum", errorbar=None, order=order, ax=ax)
        ax.tick_params(axis="x", rotation=25)
    ax.set_title("Total Spending by Weekday — Matplotlib/Seaborn")
    ax.set_xlabel("Weekday")
    ax.set_ylabel("Expense (INR)")
    fig.tight_layout()
    return fig

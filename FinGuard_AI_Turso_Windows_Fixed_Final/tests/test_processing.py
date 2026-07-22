import pandas as pd

from backend.analytics import calculate_health_score, calculate_kpis
from backend.data_processing import clean_transactions_dataframe


def test_cleaning_and_kpis():
    raw = pd.DataFrame({
        "Date": ["01-07-2026", "02-07-2026", "02-07-2026"],
        "Description": ["Salary", "Food", "Food"],
        "Type": ["Credit", "Debit", "Debit"],
        "Amount": ["₹50,000.00", "1,000.00", "1,000.00"],
        "Category": ["Salary", "Food & Dining", "Food & Dining"],
    })
    cleaned = clean_transactions_dataframe(raw)
    assert len(cleaned) == 2
    df = pd.DataFrame({
        "type": cleaned["transaction_type"], "amount": cleaned["amount"],
        "balance_after": [50000, 49000], "risk_level": ["LOW", "LOW"],
        "is_unusual": [False, False], "category": cleaned["category"],
        "date": cleaned["transaction_date"],
    })
    df["month"] = df["date"].dt.to_period("M").astype(str)
    kpis = calculate_kpis(df)
    assert kpis["income"] == 50000
    assert kpis["expense"] == 1000
    score, _ = calculate_health_score(df)
    assert 0 <= score <= 100

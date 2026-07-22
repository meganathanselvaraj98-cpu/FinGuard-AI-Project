from __future__ import annotations

import io

import joblib
import numpy as np
import openpyxl
import pandas as pd

from backend.config import settings
from backend.ml_service import load_model_registry
from backend.reporting import csv_bytes, excel_dashboard_bytes, pdf_report_bytes


def test_five_model_artifacts_load_and_predict():
    model_dir = settings.model_dir
    category = joblib.load(model_dir / "expense_category_classifier.joblib")
    expense = joblib.load(model_dir / "monthly_expense_predictor.joblib")
    savings = joblib.load(model_dir / "savings_predictor.joblib")
    risk = joblib.load(model_dir / "financial_risk_classifier.joblib")
    anomaly = joblib.load(model_dir / "anomaly_detector.joblib")

    assert category.predict(["monthly salary credited"])[0]
    assert np.isfinite(expense.predict([[61, 70000, 35000]])[0])
    assert np.isfinite(savings.predict([[70000, 35000, 5000]])[0])
    assert risk.predict([[25000, 1, 1, 2]])[0] in {0, 1}
    assert anomaly.predict([[2500]])[0] in {-1, 1}
    assert all(row["Status"] == "Ready" for row in load_model_registry())


def _report_frame() -> pd.DataFrame:
    rows = []
    for month in range(1, 5):
        rows.extend([
            {"id": month * 10, "date": pd.Timestamp(2026, month, 1), "description": "Salary", "type": "INCOME", "amount": 50000.0, "balance_after": 50000.0, "category": "Salary", "payment_mode": "NEFT", "merchant": "Employer", "statement_label": f"Statement {month}", "account_last4": "1234"},
            {"id": month * 10 + 1, "date": pd.Timestamp(2026, month, 5), "description": "Rent", "type": "EXPENSE", "amount": 9000.0, "balance_after": 41000.0, "category": "Rent", "payment_mode": "UPI", "merchant": "Owner", "statement_label": f"Statement {month}", "account_last4": "1234"},
            {"id": month * 10 + 2, "date": pd.Timestamp(2026, month, 12), "description": "Groceries", "type": "EXPENSE", "amount": 2400.0, "balance_after": 38600.0, "category": "Groceries", "payment_mode": "Card", "merchant": "Market", "statement_label": f"Statement {month}", "account_last4": "1234"},
        ])
    frame = pd.DataFrame(rows)
    frame["month"] = frame["date"].dt.to_period("M").astype(str)
    return frame


def test_csv_excel_pdf_exports_are_valid_and_privacy_safe():
    frame = _report_frame()
    frame["account_number"] = "123456789012"
    frame["ifsc"] = "DEMO0001234"
    frame["pan"] = "ABCDE1234F"
    csv_data = csv_bytes(frame)
    assert b"123456789012" not in csv_data
    assert b"DEMO0001234" not in csv_data

    excel_data = excel_dashboard_bytes(frame)
    workbook = openpyxl.load_workbook(io.BytesIO(excel_data), read_only=True)
    assert {"Dashboard", "Transactions", "Monthly Summary", "Category Summary", "Statement Summary"}.issubset(workbook.sheetnames)

    pdf_data = pdf_report_bytes(frame, "Demo User")
    assert pdf_data.startswith(b"%PDF")
    assert len(pdf_data) > 1500

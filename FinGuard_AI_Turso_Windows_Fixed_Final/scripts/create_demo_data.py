"""Generate a realistic transaction CSV for the FinGuard demo."""

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

random.seed(42)
start = date.today().replace(day=1) - timedelta(days=365)
rows = []
balance = 25000.0
expense_options = [
    ("Groceries", "FreshMart", 400, 2600, "UPI"),
    ("Food & Dining", "Cafe / Restaurant", 120, 1400, "UPI"),
    ("Transport", "Ride / Fuel", 80, 1600, "UPI"),
    ("Utilities", "Electricity / Mobile", 300, 2200, "Net Banking"),
    ("Shopping", "Retail Store", 500, 4500, "Card"),
    ("Entertainment", "Movies / Events", 200, 1800, "Card"),
    ("Healthcare", "Pharmacy / Clinic", 250, 2500, "UPI"),
    ("Education", "Course / Books", 300, 3000, "Net Banking"),
]
transaction_counter = 1
for month_offset in range(13):
    month_start = (pd.Timestamp(start) + pd.DateOffset(months=month_offset)).date().replace(day=1)
    salary_date = month_start + timedelta(days=1)
    salary = random.randint(38000, 52000)
    balance += salary
    rows.append({"transaction_id": f"SAL{transaction_counter:05d}", "transaction_date": salary_date.isoformat(), "description": "Monthly salary credit", "transaction_type": "INCOME", "amount": salary, "balance_after": round(balance, 2), "category": "Salary", "payment_mode": "NEFT/IMPS/RTGS", "merchant": "Employer"})
    transaction_counter += 1
    for _ in range(random.randint(18, 28)):
        category, merchant, low, high, mode = random.choice(expense_options)
        amount = random.randint(low, high)
        tx_date = month_start + timedelta(days=random.randint(2, 27))
        balance -= amount
        rows.append({"transaction_id": f"TXN{transaction_counter:05d}", "transaction_date": tx_date.isoformat(), "description": f"{category} payment at {merchant}", "transaction_type": "EXPENSE", "amount": amount, "balance_after": round(balance, 2), "category": category, "payment_mode": mode, "merchant": merchant})
        transaction_counter += 1
    balance -= 499
    rows.append({"transaction_id": f"SUB{transaction_counter:05d}", "transaction_date": (month_start + timedelta(days=8)).isoformat(), "description": "Streaming subscription", "transaction_type": "EXPENSE", "amount": 499, "balance_after": round(balance, 2), "category": "Subscriptions", "payment_mode": "Card", "merchant": "StreamPlus"})
    transaction_counter += 1

output = Path(__file__).resolve().parents[1] / "datasets" / "sample_transactions.csv"
pd.DataFrame(rows).sort_values("transaction_date").to_csv(output, index=False)
print(f"Created {output} with {len(rows)} rows")

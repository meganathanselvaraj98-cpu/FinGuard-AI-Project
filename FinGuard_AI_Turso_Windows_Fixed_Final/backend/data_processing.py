"""CSV, Excel, and text-PDF transaction parsing, cleaning, and validation."""

from __future__ import annotations

import io
import re
from pathlib import Path

import fitz
import numpy as np
import pandas as pd

COLUMN_ALIASES = {
    "transaction_id": ["transaction_id", "txn_id", "transaction id", "reference", "reference_no", "ref_no", "utr", "chq_ref_no"],
    "transaction_date": ["transaction_date", "date", "txn_date", "transaction date", "value_date", "posting_date", "timestamp"],
    "description": ["description", "narration", "details", "remarks", "transaction_description", "particulars"],
    "transaction_type": ["transaction_type", "type", "credit_debit", "dr_cr", "cr_dr", "debit_credit"],
    "amount": ["amount", "transaction_amount", "value", "txn_amount"],
    "withdrawal_amount": ["withdrawal", "debit", "withdrawal_amount", "debit_amount", "dr_amount"],
    "deposit_amount": ["deposit", "credit", "deposit_amount", "credit_amount", "cr_amount"],
    "balance_after": ["balance", "closing_balance", "balance_after", "available_balance", "running_balance"],
    "category": ["category", "expense_category", "classification"],
    "payment_mode": ["payment_mode", "mode", "channel", "transaction_mode"],
    "merchant": ["merchant", "payee", "vendor", "beneficiary"],
}

CATEGORY_RULES = {
    "Salary": ["salary", "payroll", "wages"],
    "Freelance": ["freelance", "upwork", "fiverr", "client payment"],
    "Rent": ["rent", "house owner", "landlord"],
    "Groceries": ["grocery", "supermarket", "mart", "bigbasket", "dmart"],
    "Food & Dining": ["restaurant", "cafe", "swiggy", "zomato", "food"],
    "Transport": ["fuel", "petrol", "diesel", "uber", "ola", "metro", "bus"],
    "Utilities": ["electricity", "tneb", "water bill", "mobile recharge", "broadband", "jio", "airtel"],
    "Shopping": ["amazon", "flipkart", "myntra", "shopping"],
    "Healthcare": ["pharmacy", "hospital", "clinic", "medicine", "apollo"],
    "Education": ["course", "tuition", "udemy", "book", "college", "school"],
    "Entertainment": ["movie", "pvr", "netflix", "spotify", "hotstar", "ott"],
    "Subscriptions": ["subscription", "membership", "recurring"],
    "Investment": ["sip", "mutual fund", "investment", "demat"],
    "Insurance": ["insurance", "premium"],
    "EMI & Debt": ["emi", "loan", "credit card payment"],
}

PAYMENT_MODE_RULES = {
    "UPI": ["upi", "gpay", "phonepe", "paytm"],
    "Card": ["card", "pos", "visa", "mastercard"],
    "NEFT/IMPS/RTGS": ["neft", "imps", "rtgs"],
    "Net Banking": ["net banking", "netbanking"],
    "ATM": ["atm", "cash withdrawal"],
    "Cash": ["cash"],
}


def _normalize_column(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def detect_columns(columns) -> dict[str, str]:
    normalized = {_normalize_column(column): str(column) for column in columns}
    mapping: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = _normalize_column(alias)
            if key in normalized:
                mapping[canonical] = normalized[key]
                break
    return mapping


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    name = getattr(uploaded_file, "name", str(uploaded_file))
    suffix = Path(name).suffix.lower()
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    if suffix == ".csv":
        raw = uploaded_file.read() if hasattr(uploaded_file, "read") else Path(uploaded_file).read_bytes()
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
            try:
                return pd.read_csv(io.BytesIO(raw), encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("The CSV encoding could not be read.")
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(uploaded_file, sheet_name=0)
    if suffix == ".pdf":
        content = uploaded_file.read() if hasattr(uploaded_file, "read") else Path(uploaded_file).read_bytes()
        return parse_generic_pdf(content)
    raise ValueError("Unsupported file. Upload CSV, XLSX, XLS, or PDF.")


def parse_generic_pdf(content: bytes) -> pd.DataFrame:
    """Best-effort parser for text PDFs; scanned PDFs intentionally require export/OCR."""
    document = fitz.open(stream=content, filetype="pdf")
    text = "\n".join(page.get_text("text") for page in document)
    rows: list[dict[str, object]] = []
    date_pattern = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})\b")
    amount_pattern = re.compile(r"(?:₹|INR\s*)?(-?[\d,]+\.\d{2})")
    reference_pattern = re.compile(r"\b(?:UTR|REF|TXN)[:\s-]*([A-Z0-9-]{6,})\b", re.I)
    for line in text.splitlines():
        date_match = date_pattern.search(line)
        amounts = amount_pattern.findall(line)
        if not date_match or not amounts:
            continue
        amount_value = float(amounts[-1].replace(",", ""))
        lowered = line.lower()
        tx_type = "INCOME" if any(word in lowered for word in ["credit", " cr ", "salary", "deposit", "received"]) else "EXPENSE"
        ref_match = reference_pattern.search(line)
        rows.append(
            {
                "transaction_id": ref_match.group(1) if ref_match else "",
                "transaction_date": date_match.group(1),
                "description": line[:450],
                "transaction_type": tx_type,
                "amount": abs(amount_value),
            }
        )
    if not rows:
        raise ValueError("No structured transactions were detected. Scanned PDFs are not processed; export the statement as CSV/XLSX.")
    return pd.DataFrame(rows)


def _infer_by_rules(text: str, rules: dict[str, list[str]], default: str) -> str:
    lowered = text.lower()
    for label, keywords in rules.items():
        if any(keyword in lowered for keyword in keywords):
            return label
    return default


def clean_transactions_dataframe(df: pd.DataFrame, manual_mapping: dict[str, str] | None = None) -> pd.DataFrame:
    if df.empty:
        raise ValueError("The uploaded file contains no rows.")
    mapping = manual_mapping or detect_columns(df.columns)
    cleaned = df.rename(columns={source: canonical for canonical, source in mapping.items() if source in df.columns}).copy()
    missing = sorted({"transaction_date", "description"} - set(cleaned.columns))
    if missing:
        raise ValueError(f"Required columns not found: {', '.join(missing)}. Use manual column mapping.")

    for column in ["amount", "withdrawal_amount", "deposit_amount", "balance_after"]:
        if column in cleaned.columns:
            cleaned[column] = (
                cleaned[column]
                .astype(str)
                .str.replace(r"[^0-9.\-]", "", regex=True)
                .replace("", np.nan)
            )
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    withdrawals = cleaned.get("withdrawal_amount", pd.Series(0.0, index=cleaned.index)).fillna(0)
    deposits = cleaned.get("deposit_amount", pd.Series(0.0, index=cleaned.index)).fillna(0)

    if "amount" not in cleaned.columns:
        cleaned["amount"] = np.where(deposits > 0, deposits, withdrawals)

    if "transaction_type" not in cleaned.columns:
        if "deposit_amount" in cleaned.columns or "withdrawal_amount" in cleaned.columns:
            cleaned["transaction_type"] = np.where(deposits > withdrawals, "INCOME", "EXPENSE")
        else:
            signed = pd.to_numeric(cleaned["amount"], errors="coerce")
            cleaned["transaction_type"] = np.where(signed < 0, "EXPENSE", "INCOME")
    else:
        normalized_type = cleaned["transaction_type"].astype(str).str.upper().str.strip().replace(
            {
                "CREDIT": "INCOME",
                "CR": "INCOME",
                "DEPOSIT": "INCOME",
                "RECEIVED": "INCOME",
                "DEBIT": "EXPENSE",
                "DR": "EXPENSE",
                "WITHDRAWAL": "EXPENSE",
                "PAID": "EXPENSE",
            }
        )
        cleaned["transaction_type"] = normalized_type.where(
            normalized_type.isin(["INCOME", "EXPENSE", "TRANSFER"]),
            "EXPENSE",
        )

    date_text = cleaned["transaction_date"].astype(str).str.strip()
    iso_mask = date_text.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
    parsed_dates = pd.Series(pd.NaT, index=cleaned.index, dtype="datetime64[ns]")
    parsed_dates.loc[iso_mask] = pd.to_datetime(date_text.loc[iso_mask], errors="coerce", yearfirst=True)
    parsed_dates.loc[~iso_mask] = pd.to_datetime(date_text.loc[~iso_mask], errors="coerce", dayfirst=True)
    cleaned["transaction_date"] = parsed_dates
    cleaned["description"] = cleaned["description"].fillna("Transaction").astype(str).str.strip().str.slice(0, 500)
    cleaned["amount"] = pd.to_numeric(cleaned["amount"], errors="coerce").abs()
    cleaned = cleaned.dropna(subset=["transaction_date", "amount"])
    cleaned = cleaned[cleaned["amount"] > 0]

    defaults = {
        "transaction_id": "",
        "category": "",
        "payment_mode": "",
        "merchant": "",
        "balance_after": np.nan,
    }
    for column, default in defaults.items():
        if column not in cleaned.columns:
            cleaned[column] = default

    text_source = (cleaned["description"].fillna("") + " " + cleaned["merchant"].fillna("")).astype(str)
    missing_category = cleaned["category"].fillna("").astype(str).str.strip().eq("")
    inferred_categories = text_source.map(lambda text: _infer_by_rules(text, CATEGORY_RULES, "Other Expense"))
    cleaned.loc[missing_category, "category"] = inferred_categories[missing_category]
    income_mask = cleaned["transaction_type"] == "INCOME"
    cleaned.loc[income_mask & cleaned["category"].isin(["", "Other Expense"]), "category"] = "Other Income"

    missing_mode = cleaned["payment_mode"].fillna("").astype(str).str.strip().eq("")
    inferred_modes = text_source.map(lambda text: _infer_by_rules(text, PAYMENT_MODE_RULES, "Other"))
    cleaned.loc[missing_mode, "payment_mode"] = inferred_modes[missing_mode]

    cleaned["transaction_id"] = cleaned["transaction_id"].fillna("").astype(str).str.strip().str.slice(0, 160)
    cleaned["merchant"] = cleaned["merchant"].fillna("").astype(str).str.strip().str.slice(0, 160)
    cleaned["year"] = cleaned["transaction_date"].dt.year
    cleaned["month"] = cleaned["transaction_date"].dt.to_period("M").astype(str)
    cleaned["weekday"] = cleaned["transaction_date"].dt.day_name()
    cleaned["day"] = cleaned["transaction_date"].dt.day
    cleaned["hour"] = cleaned["transaction_date"].dt.hour

    expense_amounts = cleaned.loc[cleaned["transaction_type"] == "EXPENSE", "amount"]
    unusual_threshold = float(expense_amounts.quantile(0.98)) if len(expense_amounts) >= 10 else float("inf")
    cleaned["is_unusual"] = (cleaned["transaction_type"] == "EXPENSE") & (cleaned["amount"] >= unusual_threshold)
    q90 = float(expense_amounts.quantile(0.90)) if len(expense_amounts) >= 5 else float("inf")
    cleaned["risk_level"] = np.where(cleaned["amount"] >= unusual_threshold, "HIGH", np.where(cleaned["amount"] >= q90, "MEDIUM", "LOW"))

    cleaned = cleaned.drop_duplicates(
        subset=["transaction_date", "description", "amount", "transaction_type", "transaction_id"],
        keep="first",
    )
    columns = [
        "transaction_id",
        "transaction_date",
        "description",
        "transaction_type",
        "amount",
        "balance_after",
        "category",
        "payment_mode",
        "merchant",
        "is_unusual",
        "risk_level",
        "year",
        "month",
        "weekday",
        "day",
        "hour",
    ]
    return cleaned[[column for column in columns if column in cleaned.columns]].reset_index(drop=True)


def dataframe_to_import_records(df: pd.DataFrame, source: str, file_name: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for row in df.to_dict(orient="records"):
        records.append(
            {
                "transaction_id": row.get("transaction_id", ""),
                "transaction_date": row["transaction_date"],
                "description": row.get("description", "Transaction"),
                "transaction_type": row.get("transaction_type", "EXPENSE"),
                "amount": row.get("amount", 0),
                "balance_after": row.get("balance_after"),
                "category": row.get("category", "Other Expense"),
                "payment_mode": row.get("payment_mode", ""),
                "merchant": row.get("merchant", ""),
                "is_unusual": bool(row.get("is_unusual", False)),
                "risk_level": row.get("risk_level", "LOW"),
                "source": source,
                "source_file_name": file_name,
            }
        )
    return records

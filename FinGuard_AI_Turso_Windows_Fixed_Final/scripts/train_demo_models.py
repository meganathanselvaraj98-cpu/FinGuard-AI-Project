"""Rebuild and evaluate the five bundled academic demo models deterministically."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier, RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models"
MODEL_DIR.mkdir(exist_ok=True)
rng = np.random.default_rng(42)
now = datetime.now(timezone.utc).isoformat()
metadata: dict[str, dict] = {}
evaluation: dict[str, dict] = {}

# 1) Expense category classifier
samples = {
    "Salary": ["salary credited", "monthly payroll", "employer salary deposit"],
    "Food & Dining": ["restaurant dinner", "cafe coffee", "food delivery order"],
    "Groceries": ["supermarket groceries", "vegetable market", "grocery store purchase"],
    "Transport": ["petrol fuel", "cab ride", "bus ticket"],
    "Utilities": ["electricity bill", "mobile recharge", "internet bill"],
    "Shopping": ["online shopping", "clothing store", "electronics purchase"],
    "Healthcare": ["hospital bill", "pharmacy medicine", "doctor consultation"],
    "Subscriptions": ["netflix subscription", "spotify subscription", "software renewal"],
}
texts, labels = [], []
for label, phrases in samples.items():
    for _ in range(30):
        phrase = phrases[int(rng.integers(0, len(phrases)))]
        texts.append(f"{phrase} ref {int(rng.integers(100, 999))}")
        labels.append(label)
x_train, x_test, y_train, y_test = train_test_split(texts, labels, test_size=0.25, random_state=42, stratify=labels)
category_model = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2))), ("model", LogisticRegression(max_iter=1200, random_state=42))])
category_model.fit(x_train, y_train)
category_prediction = category_model.predict(x_test)
evaluation["expense_category_classifier.joblib"] = {
    "accuracy": round(float(accuracy_score(y_test, category_prediction)), 4),
    "precision_weighted": round(float(precision_score(y_test, category_prediction, average="weighted", zero_division=0)), 4),
    "recall_weighted": round(float(recall_score(y_test, category_prediction, average="weighted", zero_division=0)), 4),
    "f1_weighted": round(float(f1_score(y_test, category_prediction, average="weighted", zero_division=0)), 4),
}
category_model.fit(texts, labels)
joblib.dump(category_model, MODEL_DIR / "expense_category_classifier.joblib")
metadata["expense_category_classifier.joblib"] = {"training_data": "240 synthetic labelled transaction descriptions", "generated_at": now, "features": ["description"], "estimator": "TF-IDF + Logistic Regression"}

# 2) Monthly expense predictor
month_index = np.arange(1, 61)
income = 45000 + month_index * 280 + rng.normal(0, 2500, 60)
prior_expense = 26000 + month_index * 120 + rng.normal(0, 1700, 60)
expense = 0.48 * income + 0.38 * prior_expense + rng.normal(0, 900, 60)
X_expense = np.column_stack([month_index, income, prior_expense])
xe_train, xe_test, ye_train, ye_test = train_test_split(X_expense, expense, test_size=0.25, random_state=42)
expense_model = RandomForestRegressor(n_estimators=180, random_state=42).fit(xe_train, ye_train)
expense_prediction = expense_model.predict(xe_test)
evaluation["monthly_expense_predictor.joblib"] = {"mae": round(float(mean_absolute_error(ye_test, expense_prediction)), 2), "rmse": round(float(np.sqrt(mean_squared_error(ye_test, expense_prediction))), 2)}
expense_model.fit(X_expense, expense)
joblib.dump(expense_model, MODEL_DIR / "monthly_expense_predictor.joblib")
metadata["monthly_expense_predictor.joblib"] = {"training_data": "60 synthetic monthly observations", "generated_at": now, "features": ["month_index", "income", "previous_expense"], "estimator": "Random Forest Regressor"}

# 3) Savings predictor
recurring = rng.uniform(2500, 9000, 80)
income_s = rng.uniform(25000, 125000, 80)
expense_s = rng.uniform(12000, 85000, 80)
savings = np.maximum(0, income_s - expense_s - recurring * 0.15 + rng.normal(0, 800, 80))
X_savings = np.column_stack([income_s, expense_s, recurring])
xs_train, xs_test, ys_train, ys_test = train_test_split(X_savings, savings, test_size=0.25, random_state=42)
savings_model = RandomForestRegressor(n_estimators=180, random_state=42).fit(xs_train, ys_train)
savings_prediction = savings_model.predict(xs_test)
evaluation["savings_predictor.joblib"] = {"mae": round(float(mean_absolute_error(ys_test, savings_prediction)), 2), "rmse": round(float(np.sqrt(mean_squared_error(ys_test, savings_prediction))), 2)}
savings_model.fit(X_savings, savings)
joblib.dump(savings_model, MODEL_DIR / "savings_predictor.joblib")
metadata["savings_predictor.joblib"] = {"training_data": "80 synthetic monthly observations", "generated_at": now, "features": ["income", "expense", "recurring_expense"], "estimator": "Random Forest Regressor"}

# 4) Financial risk classifier
amount = rng.lognormal(mean=7.5, sigma=0.85, size=300)
is_expense = rng.integers(0, 2, size=300)
is_unusual = rng.binomial(1, 0.12, size=300)
hour = rng.integers(0, 24, size=300)
risk = ((amount > np.quantile(amount, 0.88)) | (is_unusual == 1) | ((hour < 5) & (amount > 5000))).astype(int)
X_risk = np.column_stack([amount, is_expense, is_unusual, hour])
xr_train, xr_test, yr_train, yr_test = train_test_split(X_risk, risk, test_size=0.25, random_state=42, stratify=risk)
risk_model = RandomForestClassifier(n_estimators=180, random_state=42, class_weight="balanced").fit(xr_train, yr_train)
risk_prediction = risk_model.predict(xr_test)
evaluation["financial_risk_classifier.joblib"] = {
    "accuracy": round(float(accuracy_score(yr_test, risk_prediction)), 4),
    "precision_weighted": round(float(precision_score(yr_test, risk_prediction, average="weighted", zero_division=0)), 4),
    "recall_weighted": round(float(recall_score(yr_test, risk_prediction, average="weighted", zero_division=0)), 4),
    "f1_weighted": round(float(f1_score(yr_test, risk_prediction, average="weighted", zero_division=0)), 4),
}
risk_model.fit(X_risk, risk)
joblib.dump(risk_model, MODEL_DIR / "financial_risk_classifier.joblib")
metadata["financial_risk_classifier.joblib"] = {"training_data": "300 synthetic transaction-risk observations", "generated_at": now, "features": ["amount", "is_expense", "is_unusual", "hour"], "estimator": "Random Forest Classifier", "label_note": "Rule-assisted synthetic labels for academic demonstration"}

# 5) Isolation Forest anomaly detector
normal_amounts = rng.lognormal(mean=7.1, sigma=0.55, size=260).reshape(-1, 1)
known_outliers = np.array([[40000.0], [55000.0], [70000.0], [90000.0]])
anomaly_model = IsolationForest(contamination=0.05, random_state=42).fit(normal_amounts)
normal_predictions = anomaly_model.predict(normal_amounts)
outlier_predictions = anomaly_model.predict(known_outliers)
evaluation["anomaly_detector.joblib"] = {
    "normal_acceptance_rate": round(float((normal_predictions == 1).mean()), 4),
    "known_outlier_detection_rate": round(float((outlier_predictions == -1).mean()), 4),
}
joblib.dump(anomaly_model, MODEL_DIR / "anomaly_detector.joblib")
metadata["anomaly_detector.joblib"] = {"training_data": "260 synthetic normal-expense observations", "generated_at": now, "features": ["amount"], "estimator": "Isolation Forest"}

(MODEL_DIR / "model_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
(MODEL_DIR / "model_evaluation_results.json").write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
lines = ["# Bundled Model Evaluation", "", "These results use deterministic synthetic demo data and are not production benchmarks.", ""]
for filename, metrics in evaluation.items():
    lines.append(f"## {filename}")
    for key, value in metrics.items():
        lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    lines.append("")
(MODEL_DIR / "MODEL_EVALUATION.md").write_text("\n".join(lines), encoding="utf-8")
print("Five bundled ML artifacts rebuilt; metadata and evaluation results written.")

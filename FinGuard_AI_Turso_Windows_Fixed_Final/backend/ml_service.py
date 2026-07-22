"""Machine-learning comparison, forecasting, classification, and anomaly detection."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import IsolationForest, RandomForestClassifier, RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from backend.analytics import monthly_summary
from backend.config import settings

MODEL_FILES = {
    "Expense Category Classifier": "expense_category_classifier.joblib",
    "Monthly Expense Predictor": "monthly_expense_predictor.joblib",
    "Savings Predictor": "savings_predictor.joblib",
    "Financial Risk Classifier": "financial_risk_classifier.joblib",
    "Isolation Forest Anomaly Detector": "anomaly_detector.joblib",
}


def _rmse(y_true, y_pred) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def _safe_split_size(length: int) -> int:
    return max(1, min(int(round(length * 0.25)), length - 2))


def forecast_monthly_expense(df: pd.DataFrame, user_id: int) -> dict[str, Any]:
    monthly = monthly_summary(df)
    if len(monthly) < 3:
        fallback = float(monthly["expense"].tail(3).mean()) if not monthly.empty else 0.0
        return {
            "prediction": fallback,
            "best_model": "Moving Average (fallback)",
            "metrics": [],
            "message": "At least three months are required for model comparison.",
        }

    x_values = np.arange(len(monthly), dtype=float).reshape(-1, 1)
    y_values = monthly["expense"].to_numpy(dtype=float)
    test_size = _safe_split_size(len(monthly))
    split_at = len(monthly) - test_size
    x_train, x_test = x_values[:split_at], x_values[split_at:]
    y_train, y_test = y_values[:split_at], y_values[split_at:]

    neighbors = max(1, min(3, len(x_train)))
    models = {
        "Linear Regression": LinearRegression(),
        "Decision Tree Regressor": DecisionTreeRegressor(max_depth=5, random_state=42),
        "Random Forest Regressor": RandomForestRegressor(n_estimators=200, random_state=42),
        "KNN Regressor": Pipeline([("scale", StandardScaler()), ("model", KNeighborsRegressor(n_neighbors=neighbors))]),
        "Support Vector Regressor": Pipeline([("scale", StandardScaler()), ("model", SVR(kernel="rbf", C=100, gamma="scale"))]),
    }
    results: list[dict[str, float | str]] = []
    best_name = ""
    best_model = None
    best_rmse = float("inf")
    for name, model in models.items():
        try:
            model.fit(x_train, y_train)
            predictions = model.predict(x_test)
            mae = float(mean_absolute_error(y_test, predictions))
            rmse = _rmse(y_test, predictions)
            results.append({"Algorithm": name, "MAE": round(mae, 2), "RMSE": round(rmse, 2)})
            if rmse < best_rmse:
                best_rmse, best_name, best_model = rmse, name, model
        except (ValueError, TypeError):
            continue

    if best_model is None:
        return {
            "prediction": float(y_values.mean()),
            "best_model": "Moving Average (fallback)",
            "metrics": results,
            "message": "Model fitting was not possible; average expense was used.",
        }

    best_model.fit(x_values, y_values)
    next_value = max(0.0, float(best_model.predict([[len(monthly)]])[0]))
    model_path = settings.user_model_dir / f"expense_forecast_user_{user_id}.joblib"
    joblib.dump(best_model, model_path)
    return {
        "prediction": next_value,
        "best_model": best_name,
        "metrics": sorted(results, key=lambda item: float(item["RMSE"])),
        "message": f"Best model saved to {model_path.name}.",
    }


def _classification_metrics(y_true, prediction, algorithm: str) -> dict[str, float | str]:
    return {
        "Algorithm": algorithm,
        "Accuracy": round(float(accuracy_score(y_true, prediction)), 4),
        "Precision": round(float(precision_score(y_true, prediction, average="weighted", zero_division=0)), 4),
        "Recall": round(float(recall_score(y_true, prediction, average="weighted", zero_division=0)), 4),
        "F1 Score": round(float(f1_score(y_true, prediction, average="weighted", zero_division=0)), 4),
    }


def compare_category_classifiers(df: pd.DataFrame, user_id: int) -> dict[str, Any]:
    labelled = df[(df["description"].astype(str).str.len() > 2) & (df["category"].notna())].copy()
    if len(labelled) < 30 or labelled["category"].nunique() < 2:
        return {
            "best_model": None,
            "metrics": [],
            "message": "At least 30 labelled transactions across two categories are required.",
            "confusion_matrix": [],
            "labels": [],
        }
    min_class_count = int(labelled["category"].value_counts().min())
    stratify = labelled["category"] if min_class_count >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        labelled["description"].astype(str),
        labelled["category"],
        test_size=0.25,
        random_state=42,
        stratify=stratify,
    )
    algorithms = {
        "Logistic Regression": LogisticRegression(max_iter=1800),
        "Decision Tree": DecisionTreeClassifier(max_depth=12, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=220, random_state=42),
        "KNN": KNeighborsClassifier(n_neighbors=max(1, min(5, len(x_train) - 1))),
        "Support Vector Machine": SVC(kernel="linear", probability=True),
        "Naive Bayes": MultinomialNB(),
    }
    results: list[dict[str, float | str]] = []
    best_score = -1.0
    best_name: str | None = None
    best_pipeline = None
    best_prediction = None
    for name, classifier in algorithms.items():
        pipeline = Pipeline(
            [
                ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2), stop_words="english")),
                ("model", classifier),
            ]
        )
        try:
            pipeline.fit(x_train, y_train)
            prediction = pipeline.predict(x_test)
            metrics = _classification_metrics(y_test, prediction, name)
            results.append(metrics)
            if float(metrics["F1 Score"]) > best_score:
                best_score = float(metrics["F1 Score"])
                best_name = name
                best_pipeline = pipeline
                best_prediction = prediction
        except (ValueError, TypeError):
            continue

    labels = sorted(y_test.astype(str).unique().tolist())
    matrix = confusion_matrix(y_test, best_prediction, labels=labels).tolist() if best_prediction is not None else []
    if best_pipeline is not None:
        best_pipeline.fit(labelled["description"].astype(str), labelled["category"])
        path = settings.user_model_dir / f"category_classifier_user_{user_id}.joblib"
        joblib.dump(best_pipeline, path)
        message = f"Best classifier saved to {path.name}."
    else:
        message = "No classifier could be trained with the available distribution."
    return {
        "best_model": best_name,
        "metrics": sorted(results, key=lambda item: float(item["F1 Score"]), reverse=True),
        "message": message,
        "confusion_matrix": matrix,
        "labels": labels,
    }


def detect_anomalies(df: pd.DataFrame, user_id: int | None = None) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    output = df.copy()
    output["anomaly_score"] = 0.0
    output["ml_anomaly"] = False
    expenses = output[output["type"] == "EXPENSE"]
    if len(expenses) < 10:
        threshold = expenses["amount"].mean() + 2.5 * expenses["amount"].std(ddof=0) if len(expenses) else float("inf")
        output.loc[expenses.index, "ml_anomaly"] = expenses["amount"] > threshold
        return output

    features = expenses[["amount"]].fillna(0)
    contamination = min(0.08, max(0.01, 5 / len(expenses)))
    model = IsolationForest(contamination=contamination, random_state=42)
    labels = model.fit_predict(features)
    scores = -model.decision_function(features)
    output.loc[expenses.index, "ml_anomaly"] = labels == -1
    output.loc[expenses.index, "anomaly_score"] = scores
    if user_id is not None:
        joblib.dump(model, settings.user_model_dir / f"anomaly_detector_user_{user_id}.joblib")
    return output


def predict_monthly_savings(df: pd.DataFrame, user_id: int) -> dict[str, Any]:
    monthly = monthly_summary(df).copy()
    if monthly.empty:
        return {"prediction": 0.0, "model": "Fallback", "mae": None}
    monthly["savings_target"] = monthly["income"] - monthly["expense"]
    if len(monthly) < 4:
        prediction = float(monthly["savings_target"].tail(3).mean())
        return {"prediction": prediction, "model": "3-month average", "mae": None}

    x = monthly[["income", "expense"]].to_numpy(dtype=float)
    y = monthly["savings_target"].to_numpy(dtype=float)
    split = max(2, len(monthly) - 1)
    model = RandomForestRegressor(n_estimators=180, random_state=42)
    model.fit(x[:split], y[:split])
    pred = model.predict(x[split:])
    mae = float(mean_absolute_error(y[split:], pred)) if len(pred) else 0.0
    model.fit(x, y)
    next_income = float(monthly["income"].tail(3).mean())
    next_expense = float(monthly["expense"].tail(3).mean())
    prediction = float(model.predict([[next_income, next_expense]])[0])
    path = settings.user_model_dir / f"savings_predictor_user_{user_id}.joblib"
    joblib.dump(model, path)
    return {"prediction": prediction, "model": "Random Forest Regressor", "mae": mae, "path": path.name}


def train_financial_risk_classifier(df: pd.DataFrame, user_id: int) -> dict[str, Any]:
    """Train a rule-assisted transaction-risk classifier for academic demonstration."""
    if df.empty or len(df) < 20:
        return {
            "best_model": None,
            "metrics": [],
            "message": "At least 20 transactions are required.",
            "confusion_matrix": [],
            "labels": ["Normal", "Risk"],
        }
    work = df.copy()
    work["amount"] = pd.to_numeric(work["amount"], errors="coerce").fillna(0)
    work["is_expense"] = (work["type"] == "EXPENSE").astype(int)
    unusual_series = work["is_unusual"] if "is_unusual" in work else pd.Series(False, index=work.index)
    work["is_unusual_num"] = unusual_series.astype(int)
    work["hour"] = pd.to_datetime(work["date"], errors="coerce").dt.hour.fillna(12)
    q90 = work["amount"].quantile(0.90)
    risk_series = work["risk_level"] if "risk_level" in work else pd.Series("LOW", index=work.index)
    y = ((work["amount"] >= q90) | (work["is_unusual_num"] == 1) | risk_series.isin(["HIGH", "CRITICAL"])).astype(int)
    if y.nunique() < 2:
        y.iloc[:: max(2, len(y) // 5)] = 1
    x = work[["amount", "is_expense", "is_unusual_num", "hour"]]
    stratify = y if y.value_counts().min() >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.25, random_state=42, stratify=stratify)
    neighbors = max(1, min(5, len(x_train) - 1))
    algorithms = {
        "Logistic Regression": Pipeline([("scale", StandardScaler()), ("model", LogisticRegression(max_iter=1000))]),
        "Decision Tree": DecisionTreeClassifier(max_depth=5, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=180, random_state=42),
        "KNN": Pipeline([("scale", StandardScaler()), ("model", KNeighborsClassifier(n_neighbors=neighbors))]),
        "Support Vector Machine": Pipeline([("scale", StandardScaler()), ("model", SVC(probability=True))]),
    }
    rows: list[dict[str, float | str]] = []
    best = None
    best_name = None
    best_f1 = -1.0
    best_prediction = None
    for name, model in algorithms.items():
        try:
            model.fit(x_train, y_train)
            prediction = model.predict(x_test)
            row = _classification_metrics(y_test, prediction, name)
            rows.append(row)
            if float(row["F1 Score"]) > best_f1:
                best_f1 = float(row["F1 Score"])
                best = model
                best_name = name
                best_prediction = prediction
        except (ValueError, TypeError):
            continue
    matrix = confusion_matrix(y_test, best_prediction, labels=[0, 1]).tolist() if best_prediction is not None else []
    if best is not None:
        best.fit(x, y)
        path = settings.user_model_dir / f"financial_risk_classifier_user_{user_id}.joblib"
        joblib.dump(best, path)
        return {
            "best_model": best_name,
            "metrics": sorted(rows, key=lambda row: float(row["F1 Score"]), reverse=True),
            "message": f"Saved to {path.name}. Labels are rule-assisted for an academic demonstration.",
            "confusion_matrix": matrix,
            "labels": ["Normal", "Risk"],
        }
    return {
        "best_model": None,
        "metrics": rows,
        "message": "Training failed.",
        "confusion_matrix": [],
        "labels": ["Normal", "Risk"],
    }


def load_model_registry() -> list[dict[str, Any]]:
    """Validate the five bundled demo model artifacts."""
    metadata_path = settings.model_dir / "model_metadata.json"
    evaluation_path = settings.model_dir / "model_evaluation_results.json"
    metadata: dict[str, Any] = {}
    evaluation: dict[str, Any] = {}
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            metadata = {}
    if evaluation_path.exists():
        try:
            evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            evaluation = {}

    rows: list[dict[str, Any]] = []
    for display_name, filename in MODEL_FILES.items():
        path = settings.model_dir / filename
        status = "Missing"
        model_type = "—"
        if path.exists():
            try:
                model = joblib.load(path)
                status = "Ready"
                model_type = type(model).__name__
            except Exception as error:  # artifact validation should report, not crash UI
                status = f"Invalid: {type(error).__name__}"
        item_meta = metadata.get(filename, {}) if isinstance(metadata, dict) else {}
        item_metrics = evaluation.get(filename, {}) if isinstance(evaluation, dict) else {}
        metric_summary = " · ".join(
            f"{key.replace('_', ' ').title()}: {value}" for key, value in item_metrics.items()
        ) or "Not recorded"
        rows.append(
            {
                "Model": display_name,
                "Artifact": filename,
                "Status": status,
                "Estimator": item_meta.get("estimator", model_type),
                "Training data": item_meta.get("training_data", "Bundled synthetic demo data"),
                "Evaluation": metric_summary,
                "Generated": item_meta.get("generated_at", "Not recorded"),
            }
        )
    return rows

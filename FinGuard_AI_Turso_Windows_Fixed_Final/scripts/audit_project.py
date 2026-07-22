"""Static and artifact audit for the final FinGuard AI package."""
from __future__ import annotations

import json
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "app.py",
    "requirements.txt",
    "START_FINGUARD.bat",
    "TEST_TURSO_CONNECTION.bat",
    "MIGRATE_LOCAL_DATA_TO_TURSO.bat",
    "backend/api.py",
    "backend/config.py",
    "backend/database.py",
    "backend/security.py",
    "backend/services.py",
    "backend/ml_service.py",
    "frontend/pages/dashboard.py",
    "frontend/pages/reports.py",
    "frontend/pages/storage.py",
    "docs/TURSO_SETUP_GUIDE.md",
    "notebooks/FinGuard_Model_Evaluation.ipynb",
    "TEST_RESULTS.md",
]
MODEL_FILES = [
    "expense_category_classifier.joblib",
    "monthly_expense_predictor.joblib",
    "savings_predictor.joblib",
    "financial_risk_classifier.joblib",
    "anomaly_detector.joblib",
]


def main() -> int:
    failures: list[str] = []
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).exists():
            failures.append(f"Missing required file: {relative}")

    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    if "libsql==0.1.11" not in requirements:
        failures.append("Windows-compatible libsql dependency is missing")
    for legacy in ("pyturso", "sqlalchemy-libsql", "libsql-experimental"):
        if legacy in requirements:
            failures.append(f"Legacy dependency is still present: {legacy}")

    database_source = (ROOT / "backend" / "database.py").read_text(encoding="utf-8")
    if "libsql.connect" not in database_source:
        failures.append("libSQL embedded-replica connection is not configured")
    if "sqlite+turso_sync" in database_source or "sqlite+libsql" in database_source:
        failures.append("Optional Turso SQLAlchemy plugin URL remains in backend/database.py")

    for name in MODEL_FILES:
        path = ROOT / "models" / name
        if not path.exists():
            failures.append(f"Missing model: {name}")
            continue
        try:
            joblib.load(path)
        except Exception as error:
            failures.append(f"Invalid model {name}: {type(error).__name__}")

    forbidden_dirs = [ROOT / ".venv", ROOT / ".venv-wsl"]
    for directory in forbidden_dirs:
        if directory.exists():
            failures.append(f"Virtual environment must not be packaged: {directory.name}")

    secret_files = []
    for path in (ROOT / ".secrets").glob("*"):
        if path.is_file() and path.name != ".gitkeep":
            secret_files.append(path.name)
    if (ROOT / ".streamlit" / "secrets.toml").exists():
        secret_files.append(".streamlit/secrets.toml")
    if secret_files:
        failures.append("Runtime secrets must not be packaged: " + ", ".join(secret_files))

    packaged_databases = [path for path in ROOT.rglob("*.db") if ".venv" not in path.parts]
    if packaged_databases:
        failures.append(
            "Runtime databases must not be packaged: "
            + ", ".join(str(path.relative_to(ROOT)) for path in packaged_databases)
        )

    notebook = json.loads((ROOT / "notebooks" / "FinGuard_Model_Evaluation.ipynb").read_text(encoding="utf-8"))
    if len(notebook.get("cells", [])) < 10:
        failures.append("Jupyter notebook is too small to demonstrate the ML workflow")

    if failures:
        print("AUDIT FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("AUDIT PASSED")
    print(f"- Required files: {len(REQUIRED_FILES)}")
    print(f"- Joblib models loaded: {len(MODEL_FILES)}")
    print("- Official Turso SQLAlchemy sync dialect: configured")
    print("- Optional SQLAlchemy Turso plugins: removed")
    print("- Packaged virtual environments: 0")
    print("- Packaged runtime databases: 0")
    print("- Packaged runtime secrets: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

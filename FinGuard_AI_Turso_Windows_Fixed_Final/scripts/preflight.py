"""Startup validation for local SQLite and Turso Cloud modes."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import get_field_encryption_key, settings
from backend.database import initialize_database
from backend.ml_service import load_model_registry
from backend.sqlite_manager import database_overview


def main() -> int:
    if sys.version_info < (3, 10):
        print("ERROR: Python 3.10 or newer is required.")
        return 2
    for directory in (
        settings.data_dir,
        settings.backup_dir,
        settings.secret_dir,
        settings.log_dir,
        settings.model_dir,
        settings.user_model_dir,
        settings.report_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    get_field_encryption_key()
    try:
        initialize_database()
        overview = database_overview()
    except Exception as error:
        print(f"ERROR: {error}")
        if settings.is_turso:
            print("Check .streamlit/secrets.toml, your Turso token, and internet connection.")
        return 3
    invalid = [row for row in load_model_registry() if row["Status"] != "Ready"]
    if invalid:
        print("WARNING: Some ML model files are missing or invalid:")
        for row in invalid:
            print(f" - {row['Artifact']}: {row['Status']}")
    print(f"Database mode: {overview['mode']}")
    print(f"Tables: {overview['tables']} | Rows: {overview['rows']} | Integrity: {overview['integrity']}")
    print("Preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

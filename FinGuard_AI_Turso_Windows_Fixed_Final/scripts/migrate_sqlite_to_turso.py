from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import settings
from backend.database import engine, initialize_database, sync_from_turso, sync_to_turso

TABLE_ORDER = [
    "users",
    "categories",
    "user_profiles",
    "user_preferences",
    "bank_accounts",
    "statement_imports",
    "transactions",
    "budgets",
    "predictions",
    "reports",
    "audit_logs",
]


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def migrate(source_path: Path) -> dict[str, int]:
    if not settings.is_turso:
        raise RuntimeError("Turso is not configured in .streamlit/secrets.toml.")
    if not source_path.exists():
        raise FileNotFoundError(f"Local database not found: {source_path}")
    if source_path.resolve() == settings.turso_replica_path.resolve():
        raise ValueError("Choose the original local finguard_ai.db, not the Turso replica file.")

    initialize_database()
    sync_from_turso(force=True)
    counts: dict[str, int] = {}

    with sqlite3.connect(source_path) as source:
        source.row_factory = sqlite3.Row
        available = {
            row[0]
            for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        with engine.begin() as target:
            for table in TABLE_ORDER:
                if table not in available:
                    counts[table] = 0
                    continue
                rows = [dict(row) for row in source.execute(f"SELECT * FROM {_quote(table)}")]
                if not rows:
                    counts[table] = 0
                    continue
                columns = list(rows[0])
                column_sql = ", ".join(_quote(column) for column in columns)
                value_sql = ", ".join(f":{column}" for column in columns)
                statement = text(
                    f"INSERT OR IGNORE INTO {_quote(table)} ({column_sql}) VALUES ({value_sql})"
                )
                target.execute(statement, rows)
                counts[table] = len(rows)

    sync_to_turso()
    sync_from_turso(force=True)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy an existing FinGuard SQLite database into Turso Cloud.")
    parser.add_argument(
        "source",
        nargs="?",
        default=str(ROOT / "data" / "finguard_ai.db"),
        help="Path to the existing local finguard_ai.db file.",
    )
    args = parser.parse_args()
    try:
        counts = migrate(Path(args.source))
    except Exception as error:
        print(f"Migration failed: {error}")
        return 1
    print("Migration completed and synchronized to Turso.")
    for table, count in counts.items():
        print(f" - {table}: {count} source rows processed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

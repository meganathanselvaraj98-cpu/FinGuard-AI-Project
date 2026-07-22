from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect, text

from backend.config import settings


def main() -> int:
    if not settings.is_turso:
        print("Turso is not configured. Add TURSO_DATABASE_URL and TURSO_AUTH_TOKEN to .streamlit/secrets.toml.")
        return 2
    try:
        from backend.database import engine, initialize_database
        initialize_database()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
        tables = inspect(engine).get_table_names()
    except Exception as error:
        print(f"Turso connection failed: {error}")
        return 3
    print("Turso connection successful.")
    print(f"Application tables: {len(tables)}")
    print(", ".join(sorted(tables)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

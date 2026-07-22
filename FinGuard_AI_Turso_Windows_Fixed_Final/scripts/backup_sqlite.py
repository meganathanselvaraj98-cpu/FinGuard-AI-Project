"""Create a timestamped local backup of the FinGuard SQLite database."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import initialize_database
from backend.sqlite_manager import create_persistent_backup, integrity_check


def main() -> int:
    initialize_database()
    result = integrity_check()
    if result.lower() != "ok":
        print(f"ERROR: SQLite integrity check failed: {result}")
        return 1
    path = create_persistent_backup()
    print(f"Backup created: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

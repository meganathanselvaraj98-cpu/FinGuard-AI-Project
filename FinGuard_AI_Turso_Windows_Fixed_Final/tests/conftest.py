"""Isolated test configuration: never touch a user's local FinGuard database."""
from __future__ import annotations

import base64
import gc
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB = Path("/tmp/finguard_ai_pytest.db")
for suffix in ("", "-shm", "-wal"):
    Path(str(TEST_DB) + suffix).unlink(missing_ok=True)

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["SECRET_KEY"] = "pytest-jwt-secret-that-is-long-and-independent"
os.environ["HASH_PEPPER"] = "pytest-hash-pepper-that-is-different-and-long"
os.environ["FIELD_ENCRYPTION_KEY"] = base64.urlsafe_b64encode(b"T" * 32).decode("ascii")
os.environ["ADMIN_EMAIL"] = ""
os.environ["ADMIN_PASSWORD"] = ""


def pytest_sessionfinish(session, exitstatus):
    """Clean up test database files after session completes."""
    # Force garbage collection to close any remaining connections
    gc.collect()
    time.sleep(0.1)  # Give OS time to release file handles
    
    for suffix in ("", "-shm", "-wal"):
        db_file = Path(str(TEST_DB) + suffix)
        if db_file.exists():
            try:
                db_file.unlink()
            except (PermissionError, OSError):
                # File might be locked on Windows, ignore cleanup failure
                pass

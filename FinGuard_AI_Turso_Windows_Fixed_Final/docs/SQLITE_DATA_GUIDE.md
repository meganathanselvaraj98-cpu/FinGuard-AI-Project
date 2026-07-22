# SQLite Data and Viewer Guide

## Where data is stored

The application automatically creates:

```text
data/finguard_ai.db
```

The file remains after the website is closed and reopened. `RESET_AND_RUN.bat` removes only the Python environment and does not delete this database.

## User view

Open **My Stored Data** from the sidebar. The page contains separate tabs for:

- identity and profile
- bank accounts
- imported statements
- transactions
- budgets
- predictions
- report history
- preferences and audit activity
- privacy-safe data export

Users are filtered by their authenticated `user_id` and cannot view another user's records.

## Administrator view

Open **Database Console** from an Administrator account. The page provides:

- database health and file path
- table and row counts
- privacy-safe storage previews
- raw ciphertext previews
- table CSV downloads
- complete `.db` backup download
- integrity check
- WAL checkpoint
- optimization and compaction

## Restore a backup

1. Stop Streamlit and FastAPI.
2. Rename the current `data/finguard_ai.db` as a safety copy.
3. Copy the downloaded backup into `data/`.
4. Rename it to `finguard_ai.db`.
5. Start `START_FINGUARD.bat`.

The `.secrets/field_key.key` file must match the database that contains encrypted fields. Back up `.secrets/` privately together with the database. Never upload either to a public repository.

# Feature Verification — Turso Cloud Ready Edition

| Requirement | Verified implementation |
|---|---|
| Shared cloud database | Official `libsql` embedded replica with Windows wheels |
| Local fallback | Automatic SQLite database when Turso secrets are absent |
| Automatic table creation | SQLAlchemy metadata initialization |
| User-owned storage | Profiles, preferences, accounts, statements, transactions, budgets, predictions, reports, and audits linked to `user_id` |
| User isolation | Normal service and API queries filter by authenticated `user_id` |
| Admin-only global visibility | Role-protected Admin Portal and Database Console |
| Secure sensitive fields | AES-256-GCM field encryption |
| Password security | Argon2id hashing |
| Multi-bank statement support | Account and statement-linked transaction records |
| Dashboard switching | Consolidated, account, and statement views |
| Interactive charts | Zoom, pan, hover, reset, and titled PNG exports |
| Machine learning | Five Joblib artifacts and model comparisons |
| Reports | CSV, Excel dashboard, and PDF |
| FastAPI | JWT bearer and HttpOnly-cookie authentication |
| Windows launch | `START_FINGUARD.bat` |
| Cloud connection test | `TEST_TURSO_CONNECTION.bat` |
| Local-to-cloud migration | `MIGRATE_LOCAL_DATA_TO_TURSO.bat` |

The final package contains no runtime database, private token, encryption key, or virtual environment.

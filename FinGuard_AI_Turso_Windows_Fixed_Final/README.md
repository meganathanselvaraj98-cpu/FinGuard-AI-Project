# FinGuard AI — Turso Cloud Ready Edition

FinGuard AI is a multi-user personal-finance intelligence application with secure account separation, interactive dashboards, machine-learning insights, reports, and a restricted administrator portal.

## Important database behaviour

- **Local run without Turso credentials:** data is stored in `data/finguard_ai.db`.
- **Turso credentials configured:** all deployed users share one Turso cloud database.
- Every profile, account, statement, transaction, budget, prediction, report, preference, and audit record is linked to a unique `user_id`.
- Normal users retrieve only their own `user_id` records.
- The `ADMIN` role can inspect all users and related records through the Admin Portal.

GitHub stores the source code only. Live user records are written to Turso, not pushed into GitHub.

## Main fix in this edition

The previous `sqlite+libsql` SQLAlchemy plugin path was removed. This project now uses the official `libsql` package through SQLAlchemy’s built-in SQLite dialect and a DB-API connection creator. It works directly on supported Windows, Linux, Streamlit Cloud, and Python 3.12 on Windows and supported Linux runtimes environments without the old `sqlalchemy-libsql` plugin error.

## Windows one-click run

1. Extract the ZIP completely.
2. Open the inner project folder containing `app.py`.
3. Create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example`.
4. Paste your Turso URL, Read & Write token, encryption keys, and Admin credentials.
5. Double-click `START_FINGUARD.bat`.

The launcher creates `.venv`, installs packages, checks the database, and opens:

```text
http://127.0.0.1:8501
```

WSL or Ubuntu is no longer required for normal project execution.

## VS Code manual run

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python scripts\test_turso_connection.py
python -m streamlit run app.py
```

## Turso secrets

Create `.streamlit/secrets.toml`:

```toml
TURSO_DATABASE_URL = "libsql://your-database-name-your-org.turso.io"
TURSO_AUTH_TOKEN = "your-read-write-database-token"

SECRET_KEY = "a-long-random-secret"
HASH_PEPPER = "a-different-long-random-secret"
FIELD_ENCRYPTION_KEY = "your-generated-field-encryption-key"

ADMIN_EMAIL = "your-admin-email@example.com"
ADMIN_PASSWORD = "YourStrongPassword@123"
COOKIE_SECURE = false
```

Generate an encryption key:

```powershell
python scripts\generate_key.py
```

For Streamlit Cloud, paste the same values into **App settings → Secrets** and set:

```toml
COOKIE_SECURE = true
```

Never commit `.streamlit/secrets.toml`, `.env`, database files, or encryption keys to GitHub.

## Test the cloud connection

```powershell
.\TEST_TURSO_CONNECTION.bat
```

or:

```powershell
python scripts\test_turso_connection.py
```

The application creates its tables automatically after a successful connection.

## Migrate previous local data

To copy an existing `data/finguard_ai.db` into a fresh Turso database:

```powershell
.\MIGRATE_LOCAL_DATA_TO_TURSO.bat
```

The same encryption key used by the old local database must be configured, otherwise previously encrypted values cannot be read.

## User access model

```text
Signed-in user
    └── queries filtered by user_id
        ├── own profile
        ├── own bank accounts
        ├── own statements
        ├── own transactions
        ├── own budgets
        ├── own predictions
        └── own reports

Administrator
    └── restricted Admin Portal
        ├── all users and profiles
        ├── all linked accounts and statements
        ├── all transaction analytics
        ├── demographic and financial charts
        ├── reports and predictions
        └── audit history
```

## Features

- Login, registration, roles, and login-attempt protection
- Encrypted profiles and bank accounts
- CSV, Excel, and text-based PDF statement upload
- Duplicate prevention and data cleaning
- Consolidated, bank-account, and statement switching
- Interactive charts with titled PNG downloads
- Budgets, financial-health scoring, predictions, anomaly detection, and AI guidance
- Educational investment ideas
- CSV, Excel, and PDF reports
- Admin analytics and database console
- FastAPI authentication endpoints
- Local SQLite fallback and shared Turso cloud mode

## Verification

```powershell
python -m pytest -q
```

The final audited package passes 24 automated tests, including SQLAlchemy dialect loading, user isolation, Admin authorization, security, models, reports, and Streamlit page rendering.

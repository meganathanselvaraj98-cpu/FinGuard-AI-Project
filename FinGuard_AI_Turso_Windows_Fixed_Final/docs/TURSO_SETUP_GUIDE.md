# Turso Setup Guide

## 1. Create the database

In the Turso dashboard, create a database named `finguard-ai` and choose the nearest region.

Keep these options:

- Block Reads: Off
- Block Writes: Off
- Delete Protection: On

## 2. Copy credentials

From the database Overview page:

1. Copy the `libsql://...` Database URL.
2. Select **Create Token**.
3. Choose **Read & Write**.
4. Choose the required expiry period.
5. Copy the generated token immediately.

## 3. Configure the project

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and insert the credentials.

```toml
TURSO_DATABASE_URL = "libsql://..."
TURSO_AUTH_TOKEN = "..."
```

Add strong values for `SECRET_KEY`, `HASH_PEPPER`, `FIELD_ENCRYPTION_KEY`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD`.

## 4. Run on Windows

```powershell
.\START_FINGUARD.bat
```

The project uses the official `libsql` driver through SQLAlchemy’s built-in SQLite dialect. WSL is not required.

## 5. Verify

```powershell
.\TEST_TURSO_CONNECTION.bat
```

A successful test creates and lists the application tables.

## 6. Deploy to Streamlit Cloud

1. Push the project code to GitHub.
2. Do not push `.streamlit/secrets.toml`.
3. Create the Streamlit app with `app.py` as the entry file.
4. Paste the secrets into Streamlit App settings.
5. Set `COOKIE_SECURE = true`.

All deployed users will write to the same Turso database. Normal users remain restricted to their own `user_id`; the Admin Portal can inspect all user records.

## 7. Existing local data

Place the old database at `data/finguard_ai.db` and run:

```powershell
.\MIGRATE_LOCAL_DATA_TO_TURSO.bat
```

Use a fresh cloud database when possible and retain the original encryption key.

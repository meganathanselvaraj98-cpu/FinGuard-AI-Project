# Deployment Guide

## Local deployment

Use `START_FINGUARD.bat`. The service binds to `127.0.0.1`, keeping the application visible only on the local computer.

## Docker deployment

```bash
docker compose up --build
```

Docker Compose starts:

- secret/database initializer
- FastAPI on port 8000
- Streamlit on port 8501
- persistent named volumes for SQLite, secrets, reports, logs, models and backups

The `sqlite_data` volume stores `/app/data/finguard_ai.db` across container restarts.

## Backup

Administrators can download a transactionally consistent `.db` backup from **Database Console**. Users can also download a complete local backup from **Settings → Data backup**.

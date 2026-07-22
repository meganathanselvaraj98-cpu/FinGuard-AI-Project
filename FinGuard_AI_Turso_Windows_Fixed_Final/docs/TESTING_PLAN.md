# Testing Plan

- Unit tests: validation, encryption, hashing, finance calculations and data cleaning
- Database tests: table creation, foreign keys, WAL mode, integrity, ownership isolation and preference persistence
- Backup tests: create a consistent SQLite backup and reopen it successfully
- UI smoke tests: login and every user/admin page
- API tests: registration, login, JWT bearer, HttpOnly cookie and admin summary
- ML tests: load and predict with five Joblib artifacts
- Reporting tests: privacy-safe CSV, Excel and PDF generation
- Static audit: SQLite schema, no database driver/service dependency, models, notebook and zero packaged secrets/databases

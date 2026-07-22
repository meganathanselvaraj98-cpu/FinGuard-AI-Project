# Turso Windows Compatibility Report

## Root cause fixed

`pyturso` was removed because its published wheels do not include Windows builds. Pip therefore attempted a Rust/Maturin source build and failed.

## Current database driver

- Package: `libsql==0.1.11`
- Windows runtime: CPython 3.12 x64
- SQLAlchemy integration: built-in `sqlite://` dialect with a DB-API `creator`
- Turso mode: embedded local replica connected with `sync_url` and `auth_token`
- Local fallback: standard SQLite

The project no longer requires these optional plugin paths:

- `pyturso`
- `sqlalchemy-libsql`
- `libsql-experimental`
- `sqlite+libsql`
- `sqlite+turso_sync`

## Verification

- Python source compilation: passed
- Project audit: passed
- Security, processing, model, database isolation and driver tests: 8 passed
- Full UI test suite was not run in the packaging environment because Streamlit was not installed there.

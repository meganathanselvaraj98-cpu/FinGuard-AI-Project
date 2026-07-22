# Upgrade Notes

- Fixed `sqlalchemy.dialects:sqlite.libsql` plugin errors.
- Replaced the legacy driver with the official `libsql` package.
- Added a shared Turso cloud database with a responsive local replica.
- Added direct Windows Python 3.14 support; WSL is not required.
- Added automatic cloud pull/push synchronization.
- Added a generic Admin Database Console for local and cloud modes.
- Added migration of previous local SQLite data into Turso.
- Restored sidebar navigation and retained performance caching.
- Removed packaged credentials, local databases, and virtual environments.

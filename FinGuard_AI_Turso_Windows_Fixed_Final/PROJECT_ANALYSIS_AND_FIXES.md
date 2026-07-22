# Project Analysis and Fixes

## Root cause of the previous error

The application generated:

```text
sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:sqlite.libsql
```

The source code requested the legacy `sqlite+libsql` SQLAlchemy dialect, while its plugin was missing or could not be built in the active Windows/Python environment.

## Final correction

- Removed the legacy `sqlite+libsql` engine construction.
- Removed the `sqlalchemy-libsql` and `libsql-experimental` dependency path.
- Added the official `libsql` package.
- Added the built-in `libSQL embedded replica` SQLAlchemy dialect.
- Added cloud pull before reads and cloud push after commits.
- Added a local Turso replica for responsive queries.
- Added Windows Python 3.14 compatibility.
- Added direct loading of `.streamlit/secrets.toml` for test scripts and local execution.
- Added a clear local SQLite fallback when Turso credentials are not configured.
- Added a migration utility for previous SQLite records.
- Removed packaged virtual environments, local databases, and secret files.

## Access control

Every user-owned table is linked to `user_id`. Normal services enforce ownership filters. The Admin Portal is guarded by the `ADMIN` role and can inspect cross-user analytics and authorized detailed views.

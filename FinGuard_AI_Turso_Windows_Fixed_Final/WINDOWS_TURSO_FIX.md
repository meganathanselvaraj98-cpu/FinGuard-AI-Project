# Windows Turso Installation Fix

Use **Python 3.12 x64** on Windows.

The project uses `libsql==0.1.11`, which provides a prebuilt Windows wheel for CPython 3.12. It does not use `pyturso`, `sqlalchemy-libsql`, `libsql-experimental`, `sqlite+libsql`, or `sqlite+turso_sync`.

## Clean installation

```powershell
Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install --only-binary=:all: -r requirements.txt
python scripts\test_turso_connection.py
python -m streamlit run app.py
```

Or double-click `START_FINGUARD.bat`; it verifies Python 3.12 and recreates an incompatible environment automatically.

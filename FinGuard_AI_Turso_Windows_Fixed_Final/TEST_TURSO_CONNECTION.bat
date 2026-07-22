@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run START_FINGUARD.bat once before testing Turso.
  pause
  exit /b 1
)
.venv\Scripts\python.exe scripts\test_turso_connection.py
pause

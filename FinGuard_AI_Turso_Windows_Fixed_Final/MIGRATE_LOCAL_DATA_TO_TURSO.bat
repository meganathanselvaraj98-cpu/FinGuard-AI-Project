@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run START_FINGUARD.bat once before migration.
  pause
  exit /b 1
)
echo This copies data\finguard_ai.db into the configured Turso database.
echo Use a fresh Turso database for the cleanest migration.
set /p CONFIRM=Type MIGRATE to continue: 
if /I not "%CONFIRM%"=="MIGRATE" exit /b 0
.venv\Scripts\python.exe scripts\migrate_sqlite_to_turso.py
pause

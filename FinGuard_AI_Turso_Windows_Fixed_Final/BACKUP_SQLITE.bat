@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run START_FINGUARD.bat once first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe scripts\backup_sqlite.py
if errorlevel 1 (
  echo Backup failed.
  pause
  exit /b 1
)
start "" "%~dp0backups"
pause

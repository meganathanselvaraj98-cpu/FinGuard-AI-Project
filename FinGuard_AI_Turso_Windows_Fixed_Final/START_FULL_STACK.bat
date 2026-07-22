@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run START_FINGUARD.bat once to create the Python environment.
  pause
  exit /b 1
)
start "FinGuard API" cmd /k ".venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8000 --reload"
start "" http://127.0.0.1:8000/docs
call START_FINGUARD.bat

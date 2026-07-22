@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run START_FINGUARD.bat once first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pytest -q
if errorlevel 1 goto :failed
.venv\Scripts\python.exe scripts\audit_project.py
if errorlevel 1 goto :failed
echo All FinGuard tests and audits passed.
pause
exit /b 0
:failed
echo Tests or audit failed. Review the error above.
pause
exit /b 1

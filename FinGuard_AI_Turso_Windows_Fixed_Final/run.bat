@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FinGuard AI - Windows Launcher
color 0A
echo =====================================================
echo   FinGuard AI - Local SQLite / Turso Cloud
echo   Required Windows runtime: Python 3.12 x64
echo =====================================================

where py >nul 2>nul
if errorlevel 1 goto :no_launcher
py -3.12 -c "import sys; assert sys.maxsize > 2**32" >nul 2>nul
if errorlevel 1 goto :no_python312

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)" >nul 2>nul
  if errorlevel 1 (
    echo Existing .venv uses a different Python version. Recreating it with Python 3.12...
    rmdir /s /q .venv
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Creating Python 3.12 environment...
  py -3.12 -m venv .venv || goto :failed
) else (
  echo [1/5] Python 3.12 environment ready.
)

set "VPY=.venv\Scripts\python.exe"
set "PIP=.venv\Scripts\python.exe -m pip"
set "NEED_INSTALL=0"
if not exist ".venv\requirements.lock" set "NEED_INSTALL=1"
if exist ".venv\requirements.lock" fc /b requirements.txt .venv\requirements.lock >nul 2>nul || set "NEED_INSTALL=1"
if "%NEED_INSTALL%"=="1" (
  echo [2/5] Installing Windows-compatible packages...
  %PIP% install --disable-pip-version-check --upgrade pip setuptools wheel || goto :failed
  %PIP% install --disable-pip-version-check --only-binary=:all: -r requirements.txt || goto :failed
  copy /y requirements.txt .venv\requirements.lock >nul
) else (
  echo [2/5] Packages already installed.
)

echo [3/5] Checking database and configuration...
%VPY% scripts\preflight.py || goto :failed

echo [4/5] Opening browser...
start "" http://127.0.0.1:8501

echo [5/5] FinGuard AI is running. Press Ctrl+C to stop.
%VPY% -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
exit /b 0

:no_launcher
echo ERROR: Python Launcher was not found.
echo Install Python 3.12 x64 from python.org and enable the Python Launcher.
pause
exit /b 2

:no_python312
echo ERROR: Python 3.12 x64 is not installed.
echo Run: py install 3.12
pause
exit /b 3

:failed
echo.
echo ERROR: Setup did not complete. Read the error above.
pause
exit /b 1

@echo off
cd /d "%~dp0"
echo This removes only the Python virtual environment. User database and encrypted data are kept.
if exist .venv rmdir /s /q .venv
call run.bat

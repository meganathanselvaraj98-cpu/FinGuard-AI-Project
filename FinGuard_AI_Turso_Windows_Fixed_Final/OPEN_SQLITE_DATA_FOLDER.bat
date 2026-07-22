@echo off
cd /d "%~dp0"
if not exist "data" mkdir data
start "" "%~dp0data"

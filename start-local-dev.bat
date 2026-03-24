@echo off
cd /d "%~dp0" || exit /b 1
powershell -ExecutionPolicy Bypass -File ".\dev-local.ps1"

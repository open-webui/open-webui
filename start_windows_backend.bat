@echo off
SETLOCAL
cd /d "%~dp0" || exit /b 1
IF "%WEBUI_SECRET_KEY%"=="" SET "WEBUI_SECRET_KEY=openwebui-local-dev-key"
call backend\start_windows.bat

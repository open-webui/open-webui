@echo off
REM Windows batch script to start the backend server

REM Activate Python virtual environment if exists
if exist venv (
    call venv\Scripts\activate
)

REM Run uvicorn server
python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8080 --forwarded-allow-ips "*"

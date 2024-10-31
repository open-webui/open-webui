@echo off
IF "%1"=="" (
    SET PORT=8080
) ELSE (
    SET PORT=%1
)

ECHO Starting the Open WebUI server on port %PORT%...
uvicorn open_webui.main:app --host 0.0.0.0 --port %PORT% --forwarded-allow-ips '*' --reload

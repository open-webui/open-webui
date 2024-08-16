:: This method is not recommended, and we recommend you use the `start.sh` file with WSL instead.
@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

:: Get the directory of the current script
SET "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%" || exit /b

SET "KEY_FILE=.Falcor_secret_key"
IF "%PORT%"=="" SET PORT=8080
IF "%HOST%"=="" SET HOST=0.0.0.0
SET "Falcor_SECRET_KEY=%Falcor_SECRET_KEY%"
SET "Falcor_JWT_SECRET_KEY=%Falcor_JWT_SECRET_KEY%"

:: Check if Falcor_SECRET_KEY and Falcor_JWT_SECRET_KEY are not set
IF "%Falcor_SECRET_KEY%%Falcor_JWT_SECRET_KEY%" == " " (
    echo Loading Falcor_SECRET_KEY from file, not provided as an environment variable.

    IF NOT EXIST "%KEY_FILE%" (
        echo Generating Falcor_SECRET_KEY
        :: Generate a random value to use as a Falcor_SECRET_KEY in case the user didn't provide one
        SET /p Falcor_SECRET_KEY=<nul
        FOR /L %%i IN (1,1,12) DO SET /p Falcor_SECRET_KEY=<!random!>>%KEY_FILE%
        echo Falcor_SECRET_KEY generated
    )

    echo Loading Falcor_SECRET_KEY from %KEY_FILE%
    SET /p Falcor_SECRET_KEY=<%KEY_FILE%
)

:: Execute uvicorn
SET "Falcor_SECRET_KEY=%Falcor_SECRET_KEY%"
uvicorn main:app --host "%HOST%" --port "%PORT%" --forwarded-allow-ips '*'

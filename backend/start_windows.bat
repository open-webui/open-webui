:: This method is not recommended, and we recommend you use the `start.sh` file with WSL instead.
@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

:: Get the directory of the current script
SET "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%" || exit /b

:: Add conditional Playwright browser installation
IF /I "%WEB_LOADER_ENGINE%" == "playwright" (
    IF "%PLAYWRIGHT_WS_URL%" == "" (
        echo Installing Playwright browsers...
        playwright install chromium
        playwright install-deps chromium
    )

    python -c "import nltk; nltk.download('punkt_tab')"
)

SET "KEY_FILE=.webui_secret_key"
IF NOT "%WEBUI_SECRET_KEY_FILE%" == "" (
    SET "KEY_FILE=%WEBUI_SECRET_KEY_FILE%"
)

IF "%PORT%"=="" SET PORT=8080
IF "%HOST%"=="" SET HOST=0.0.0.0
SET "WEBUI_SECRET_KEY=%WEBUI_SECRET_KEY%"
SET "WEBUI_JWT_SECRET_KEY=%WEBUI_JWT_SECRET_KEY%"

:: Check if WEBUI_SECRET_KEY and WEBUI_JWT_SECRET_KEY are not set
IF "%WEBUI_SECRET_KEY% %WEBUI_JWT_SECRET_KEY%" == " " (
    echo Loading WEBUI_SECRET_KEY from file, not provided as an environment variable.

    IF NOT EXIST "%KEY_FILE%" (
        echo Generating WEBUI_SECRET_KEY
        :: Generate a random value to use as a WEBUI_SECRET_KEY in case the user didn't provide one
        SET /p WEBUI_SECRET_KEY=<nul
        FOR /L %%i IN (1,1,12) DO SET /p WEBUI_SECRET_KEY=<!random!>>%KEY_FILE%
        echo WEBUI_SECRET_KEY generated
    )

    echo Loading WEBUI_SECRET_KEY from %KEY_FILE%
    SET /p WEBUI_SECRET_KEY=<%KEY_FILE%
)

:: Logic to get oauth client secret from file (if OAuth is enabled)
IF /I "%ENABLE_OAUTH_SIGNUP%" == "true" (
    IF "%OAUTH_CLIENT_SECRET%" == "" (
        echo Loading OAUTH_CLIENT_SECRET from file, not provided as an environment variable.

        :: Validate file path is set
        IF "%OAUTH_CLIENT_SECRET_FILE%" == "" (
            echo ERROR: Neither OAUTH_CLIENT_SECRET nor OAUTH_CLIENT_SECRET_FILE specified
            exit /b 1
        )

        :: Check file exists and is readable
        IF NOT EXIST "%OAUTH_CLIENT_SECRET_FILE%" (
            echo ERROR: OAuth secret file not found or not readable
            exit /b 1
        )

        :: Read and validate secret
        SET /p OAUTH_CLIENT_SECRET=<"%OAUTH_CLIENT_SECRET_FILE%" 2>nul
        IF ERRORLEVEL 1 (
            echo ERROR: Failed to read OAuth secret file
            exit /b 1
        )

        :: Validate content is not empty
        IF "%OAUTH_CLIENT_SECRET%" == "" (
            echo ERROR: OAuth secret file is empty
            exit /b 1
        )

        echo Successfully loaded OAUTH_CLIENT_SECRET from file
    )
)

:: Execute uvicorn
SET "WEBUI_SECRET_KEY=%WEBUI_SECRET_KEY%"
SET "OAUTH_CLIENT_SECRET=%OAUTH_CLIENT_SECRET%"
IF "%UVICORN_WORKERS%"=="" SET UVICORN_WORKERS=1
uvicorn open_webui.main:app --host "%HOST%" --port "%PORT%" --forwarded-allow-ips '*' --workers %UVICORN_WORKERS% --ws auto
:: For ssl user uvicorn open_webui.main:app --host "%HOST%" --port "%PORT%" --forwarded-allow-ips '*' --ssl-keyfile "key.pem" --ssl-certfile "cert.pem" --ws auto

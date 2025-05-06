@echo off
title RAUX Server

REM Set default version and mode, override if provided as parameters
set "version=unknown"
set "mode=GENERIC"

REM Parse command line parameters
:parse
if "%1"=="--version" (
    set "version=%2"
    shift
    shift
    goto parse
)
if "%1"=="--mode" (
    set "mode=%2"
    shift
    shift
    goto parse
)

REM Set RAUX conda environment path
set "RAUX_CONDA_ENV=%LOCALAPPDATA%\GAIA\RAUX\raux_env"

REM Check if mode is not GENERIC to determine if Lemonade should be launched
if /I NOT "%mode%"=="GENERIC" (
    set "LAUNCH_LEMONADE=true"
) else (
    set "LAUNCH_LEMONADE=false"
)

REM Set environment variables for PowerShell script
set "RAUX_VERSION=%version%"

REM Launch RAUX with appropriate environment variables
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& '%LOCALAPPDATA%\GAIA\RAUX\launch_raux.ps1'"
echo RAUX Server has stopped.

pause
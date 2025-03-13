@echo off
title RAUX Server
echo Starting RAUX Server...
powershell.exe -ExecutionPolicy Bypass -File "%~dp0launch_raux.ps1"
echo RAUX Server has stopped.
pause 
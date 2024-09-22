@echo off

:: Check if Python 3.11 is installed
where python3.11.exe >nul 2>&1
if "%ERRORLEVEL%"=="0" (
    echo "Python 3.11 is already installed."
) else (
    echo "Installing Python 3.11..."
    powershell -Command "Add-Type -AssemblyName PresentationCore; [void][System.Reflection.Assembly]::Load('PresentationCore, Version=4.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35');"
    powershell -Command "& { Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe -OutFile python311.exe; Start-Process 'python311.exe' '-quiet -install -noconsole' };"
)

:: Create and activate the virtual environment
set ENV_DIR=myenv
if not exist "%ENV_DIR%" (
    echo "Creating a virtual environment..."
    powershell -Command "& { python3.11.exe -m venv '%ENV_DIR%'; }"
)
echo "Activating the virtual environment..."
call "%ENV_DIR%\Scripts\activate"

:: Install open-webui
echo "Installing open-webui..."
powershell -Command "& { pip install open-webui; }"

:: Run open-webui
echo "Running open-webui..."
powershell -Command "& { open-webui serve; }"

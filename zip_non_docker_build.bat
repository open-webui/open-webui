@echo off

:: create virtual environment
python -m venv venv
call venv\Scripts\activate

:: install python libs
pip install -r backend/requirements.txt

deactivate

:: install npm packages and make a build
npm ci
npm run build

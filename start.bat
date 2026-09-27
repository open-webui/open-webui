@echo off
cd /d "%~dp0"
set "FRONTEND_BUILD_DIR=%~dp0build"
if "%WEBUI_SECRET_KEY%"=="" set "WEBUI_SECRET_KEY=t8k3j4n8f9d0s7g6h5j4k3l2m1n0b9v8c7x6z5a4s3d2f1g"
if "%PORT%"=="" set PORT=8088
if "%HOST%"=="" set HOST=0.0.0.0
set "ENABLE_PIP_INSTALL_FRONTMATTER_REQUIREMENTS=False"
set "RAG_EMBEDDING_ENGINE=openai"
set "RAG_EMBEDDING_MODEL=text-embedding-3-small"
call "%~dp0.venv\Scripts\activate.bat"
python -m uvicorn open_webui.main:app --host %HOST% --port %PORT%

from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse

import redis
import requests
from authlib.integrations.starlette_client import OAuth
from pydantic import BaseModel

from open_webui.env import (
    DATA_DIR,
    DATABASE_URL,
    ENABLE_DB_MIGRATIONS,
    ENV,
    FRONTEND_BUILD_DIR,
    OFFLINE_MODE,
    OPEN_WEBUI_DIR,
    REDIS_KEY_PREFIX,
    REDIS_SENTINEL_HOSTS,
    REDIS_SENTINEL_PORT,
    REDIS_URL,
    WEBUI_AUTH,
    WEBUI_FAVICON_URL,
    WEBUI_NAME,
    log,
)
from open_webui.internal.config import (
    STATE as _state,
)
from open_webui.internal.config import (
    AppConfig,
    ConfigVar,
)

# ── Persistent configuration layer ──────────────────────────────────────────
from open_webui.internal.config import (  # noqa: F401
    ConfigTable as Config,
)
from open_webui.internal.config import (
    _all_configs as PERSISTENT_CONFIG_REGISTRY,
)
from open_webui.internal.config import (
    initialize as _initialize_config,
)


def get_config():
    return _state.snapshot


def save_to_db(data):
    _state.persist(data)


async def async_save_to_db(data):
    await _state.persist_async(data)


def save_config(config):
    try:
        _state.persist(config)
        for s in PERSISTENT_CONFIG_REGISTRY:
            s.refresh()
    except Exception:
        log.exception('Failed to save config')
        return False
    return True


async def async_save_config(config):
    try:
        await _state.persist_async(config)
        for s in PERSISTENT_CONFIG_REGISTRY:
            s.refresh()
    except Exception:
        log.exception('Failed to save config')
        return False
    return True


def reset_config():
    _state.clear()


async def async_reset_config():
    await _state.clear_async()


def get_config_value(config_path: str):
    return _state.read(config_path)


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find('/health') == -1


logging.getLogger('uvicorn.access').addFilter(EndpointFilter())

####################################
# Initialization
####################################


def run_migrations():
    log.info('Running migrations')
    try:
        from alembic import command
        from alembic.config import Config as AlembicConfig

        alembic_cfg = AlembicConfig(OPEN_WEBUI_DIR / 'alembic.ini')

        migrations_path = OPEN_WEBUI_DIR / 'migrations'
        alembic_cfg.set_main_option('script_location', str(migrations_path))

        command.upgrade(alembic_cfg, 'head')
    except Exception as e:
        log.exception(f'Error running migrations: {e}')


if ENABLE_DB_MIGRATIONS:
    run_migrations()


# Migrate legacy config.json → database on first run
if os.path.exists(f'{DATA_DIR}/config.json'):
    with open(f'{DATA_DIR}/config.json', 'r') as _f:
        save_to_db(json.load(_f))
    os.rename(f'{DATA_DIR}/config.json', f'{DATA_DIR}/old_config.json')


ENABLE_PERSISTENT_CONFIG = os.getenv('ENABLE_PERSISTENT_CONFIG', 'True').lower() == 'true'
ENABLE_OAUTH_PERSISTENT_CONFIG = os.getenv('ENABLE_OAUTH_PERSISTENT_CONFIG', 'False').lower() == 'true'

# Bootstrap the persistent config subsystem
CONFIG_DATA = _initialize_config(
    enable_persistent=ENABLE_PERSISTENT_CONFIG,
    enable_oauth_persistent=ENABLE_OAUTH_PERSISTENT_CONFIG,
)

####################################
# Static DIR
####################################

STATIC_DIR = Path(os.getenv('STATIC_DIR', OPEN_WEBUI_DIR / 'static')).resolve()

try:
    if STATIC_DIR.exists():
        for item in STATIC_DIR.iterdir():
            if item.is_file() or item.is_symlink():
                try:
                    item.unlink()
                except Exception as e:
                    pass
except Exception as e:
    pass

for file_path in (FRONTEND_BUILD_DIR / 'static').glob('**/*'):
    if file_path.is_file():
        target_path = STATIC_DIR / file_path.relative_to((FRONTEND_BUILD_DIR / 'static'))
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copyfile(file_path, target_path)
        except Exception as e:
            logging.error(f'An error occurred: {e}')

frontend_favicon = FRONTEND_BUILD_DIR / 'static' / 'favicon.png'

if frontend_favicon.exists():
    try:
        shutil.copyfile(frontend_favicon, STATIC_DIR / 'favicon.png')
    except Exception as e:
        logging.error(f'An error occurred: {e}')

frontend_splash = FRONTEND_BUILD_DIR / 'static' / 'splash.png'

if frontend_splash.exists():
    try:
        shutil.copyfile(frontend_splash, STATIC_DIR / 'splash.png')
    except Exception as e:
        logging.error(f'An error occurred: {e}')

frontend_loader = FRONTEND_BUILD_DIR / 'static' / 'loader.js'

if frontend_loader.exists():
    try:
        shutil.copyfile(frontend_loader, STATIC_DIR / 'loader.js')
    except Exception as e:
        logging.error(f'An error occurred: {e}')


# --- Storage Provider ---

STORAGE_PROVIDER = os.getenv('STORAGE_PROVIDER', 'local')  # defaults to local, s3
STORAGE_LOCAL_CACHE = os.getenv('STORAGE_LOCAL_CACHE', 'true').lower() == 'true'

S3_ACCESS_KEY_ID = os.getenv('S3_ACCESS_KEY_ID', None)
S3_SECRET_ACCESS_KEY = os.getenv('S3_SECRET_ACCESS_KEY', None)
S3_REGION_NAME = os.getenv('S3_REGION_NAME', None)
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', None)
S3_KEY_PREFIX = os.getenv('S3_KEY_PREFIX', None)
S3_ENDPOINT_URL = os.getenv('S3_ENDPOINT_URL', None)
S3_USE_ACCELERATE_ENDPOINT = os.getenv('S3_USE_ACCELERATE_ENDPOINT', 'false').lower() == 'true'
S3_ADDRESSING_STYLE = os.getenv('S3_ADDRESSING_STYLE', None)
S3_ENABLE_TAGGING = os.getenv('S3_ENABLE_TAGGING', 'false').lower() == 'true'

GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', None)
GOOGLE_APPLICATION_CREDENTIALS_JSON = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON', None)

AZURE_STORAGE_ENDPOINT = os.getenv('AZURE_STORAGE_ENDPOINT', None)
AZURE_STORAGE_CONTAINER_NAME = os.getenv('AZURE_STORAGE_CONTAINER_NAME', None)
AZURE_STORAGE_KEY = os.getenv('AZURE_STORAGE_KEY', None)

####################################
# File Upload DIR
####################################

UPLOAD_DIR = DATA_DIR / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


####################################
# Cache DIR
####################################

CACHE_DIR = DATA_DIR / 'cache'
CACHE_DIR.mkdir(parents=True, exist_ok=True)


####################################
# CUSTOM_NAME (Legacy)
####################################

CUSTOM_NAME = os.getenv('CUSTOM_NAME', '')

if CUSTOM_NAME:
    try:
        r = requests.get(f'https://api.openwebui.com/api/v1/custom/{CUSTOM_NAME}')
        data = r.json()
        if r.ok:
            if 'logo' in data:
                WEBUI_FAVICON_URL = url = (
                    f'https://api.openwebui.com{data["logo"]}' if data['logo'][0] == '/' else data['logo']
                )

                r = requests.get(url, stream=True)
                if r.status_code == 200:
                    with open(f'{STATIC_DIR}/favicon.png', 'wb') as f:
                        r.raw.decode_content = True
                        shutil.copyfileobj(r.raw, f)

            if 'splash' in data:
                url = f'https://api.openwebui.com{data["splash"]}' if data['splash'][0] == '/' else data['splash']

                r = requests.get(url, stream=True)
                if r.status_code == 200:
                    with open(f'{STATIC_DIR}/splash.png', 'wb') as f:
                        r.raw.decode_content = True
                        shutil.copyfileobj(r.raw, f)

            WEBUI_NAME = data['name']
    except Exception as e:
        log.exception(e)
        pass


####################################
# DIRECT CONNECTIONS
####################################

ENABLE_DIRECT_CONNECTIONS = ConfigVar(
    'ENABLE_DIRECT_CONNECTIONS',
    'direct.enable',
    os.getenv('ENABLE_DIRECT_CONNECTIONS', 'False').lower() == 'true',
)

####################################
# OLLAMA_BASE_URL
####################################

ENABLE_OLLAMA_API = ConfigVar(
    'ENABLE_OLLAMA_API',
    'ollama.enable',
    os.getenv('ENABLE_OLLAMA_API', 'True').lower() == 'true',
)

OLLAMA_API_BASE_URL = os.getenv('OLLAMA_API_BASE_URL', 'http://localhost:11434/api')

OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', '')
if OLLAMA_BASE_URL:
    # Remove trailing slash
    OLLAMA_BASE_URL = OLLAMA_BASE_URL[:-1] if OLLAMA_BASE_URL.endswith('/') else OLLAMA_BASE_URL


K8S_FLAG = os.getenv('K8S_FLAG', '')
USE_OLLAMA_DOCKER = os.getenv('USE_OLLAMA_DOCKER', 'false')

if OLLAMA_BASE_URL == '' and OLLAMA_API_BASE_URL != '':
    OLLAMA_BASE_URL = OLLAMA_API_BASE_URL[:-4] if OLLAMA_API_BASE_URL.endswith('/api') else OLLAMA_API_BASE_URL

if ENV == 'prod':
    if OLLAMA_BASE_URL == '/ollama' and not K8S_FLAG:
        if USE_OLLAMA_DOCKER.lower() == 'true':
            # if you use all-in-one docker container (Open WebUI + Ollama)
            # with the docker build arg USE_OLLAMA=true (--build-arg="USE_OLLAMA=true") this only works with http://localhost:11434
            OLLAMA_BASE_URL = 'http://localhost:11434'
        else:
            OLLAMA_BASE_URL = 'http://host.docker.internal:11434'
    elif K8S_FLAG:
        OLLAMA_BASE_URL = 'http://ollama-service.open-webui.svc.cluster.local:11434'


def _resolve_ollama_base_url(url: str) -> str:
    """If the default Ollama port (11434) is unreachable, try the fallback port (12434)."""

    def reachable(host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except (OSError, TimeoutError):
            return False

    host = urlparse(url).hostname or 'localhost'

    with ThreadPoolExecutor(max_workers=2) as pool:
        default = pool.submit(reachable, host, 11434)
        fallback = pool.submit(reachable, host, 12434)

    if not default.result() and fallback.result():
        url = url.replace(':11434', ':12434')
        log.info(f'Ollama port 11434 unreachable on {host}, falling back to 12434')
    elif not default.result():
        log.info(f'Ollama ports 11434 and 12434 both unreachable on {host}')

    return url


# Auto-resolve Ollama port when no explicit URL was provided by the user.
# The Dockerfile default is "/ollama" which the block above rewrites to :11434.
if os.getenv('OLLAMA_BASE_URL', '') in ('', '/ollama') and not os.getenv('OLLAMA_BASE_URLS', ''):
    OLLAMA_BASE_URL = _resolve_ollama_base_url(OLLAMA_BASE_URL)


OLLAMA_BASE_URLS = os.getenv('OLLAMA_BASE_URLS', '')
OLLAMA_BASE_URLS = OLLAMA_BASE_URLS if OLLAMA_BASE_URLS != '' else OLLAMA_BASE_URL

OLLAMA_BASE_URLS = [url.strip() for url in OLLAMA_BASE_URLS.split(';')]
OLLAMA_BASE_URLS = ConfigVar('OLLAMA_BASE_URLS', 'ollama.base_urls', OLLAMA_BASE_URLS)

OLLAMA_API_CONFIGS = ConfigVar(
    'OLLAMA_API_CONFIGS',
    'ollama.api_configs',
    {},
)

####################################
# OPENAI_API
####################################


ENABLE_OPENAI_API = ConfigVar(
    'ENABLE_OPENAI_API',
    'openai.enable',
    os.getenv('ENABLE_OPENAI_API', 'True').lower() == 'true',
)


OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_API_BASE_URL = os.getenv('OPENAI_API_BASE_URL', '')

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_API_BASE_URL = os.getenv('GEMINI_API_BASE_URL', '')


if OPENAI_API_BASE_URL == '':
    OPENAI_API_BASE_URL = 'https://api.openai.com/v1'
else:
    if OPENAI_API_BASE_URL.endswith('/'):
        OPENAI_API_BASE_URL = OPENAI_API_BASE_URL[:-1]

OPENAI_API_KEYS = os.getenv('OPENAI_API_KEYS', '')
OPENAI_API_KEYS = OPENAI_API_KEYS if OPENAI_API_KEYS != '' else OPENAI_API_KEY

OPENAI_API_KEYS = [url.strip() for url in OPENAI_API_KEYS.split(';')]
OPENAI_API_KEYS = ConfigVar('OPENAI_API_KEYS', 'openai.api_keys', OPENAI_API_KEYS)

OPENAI_API_BASE_URLS = os.getenv('OPENAI_API_BASE_URLS', '')
OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS if OPENAI_API_BASE_URLS != '' else OPENAI_API_BASE_URL

OPENAI_API_BASE_URLS = [
    url.strip() if url != '' else 'https://api.openai.com/v1' for url in OPENAI_API_BASE_URLS.split(';')
]
OPENAI_API_BASE_URLS = ConfigVar('OPENAI_API_BASE_URLS', 'openai.api_base_urls', OPENAI_API_BASE_URLS)

OPENAI_API_CONFIGS = ConfigVar(
    'OPENAI_API_CONFIGS',
    'openai.api_configs',
    {},
)

# Get the actual OpenAI API key based on the base URL
OPENAI_API_KEY = ''
try:
    OPENAI_API_KEY = OPENAI_API_KEYS.value[OPENAI_API_BASE_URLS.value.index('https://api.openai.com/v1')]
except Exception:
    pass
OPENAI_API_BASE_URL = 'https://api.openai.com/v1'


####################################
# MODELS
####################################

ENABLE_BASE_MODELS_CACHE = ConfigVar(
    'ENABLE_BASE_MODELS_CACHE',
    'models.base_models_cache',
    os.getenv('ENABLE_BASE_MODELS_CACHE', 'False').lower() == 'true',
)


####################################
# TOOL_SERVERS
####################################

try:
    tool_server_connections = json.loads(os.getenv('TOOL_SERVER_CONNECTIONS', '[]'))
except Exception as e:
    log.exception(f'Error loading TOOL_SERVER_CONNECTIONS: {e}')
    tool_server_connections = []


TOOL_SERVER_CONNECTIONS = ConfigVar(
    'TOOL_SERVER_CONNECTIONS',
    'tool_server.connections',
    tool_server_connections,
)

OAUTH_CLIENT_TIMEOUT = ConfigVar(
    'OAUTH_CLIENT_TIMEOUT',
    'oauth.client.timeout',
    os.getenv('OAUTH_CLIENT_TIMEOUT', ''),
)

####################################
# TERMINAL_SERVER
####################################

terminal_server_connections = json.loads(os.getenv('TERMINAL_SERVER_CONNECTIONS', '[]'))

TERMINAL_SERVER_CONNECTIONS = ConfigVar(
    'TERMINAL_SERVER_CONNECTIONS',
    'terminal_server.connections',
    terminal_server_connections,
)

try:
    TERMINAL_PROXY_HEADERS = json.loads(os.getenv('TERMINAL_PROXY_HEADERS', '{}'))
except Exception:
    TERMINAL_PROXY_HEADERS = {}

####################################
# Code Interpreter
####################################

ENABLE_CODE_EXECUTION = ConfigVar(
    'ENABLE_CODE_EXECUTION',
    'code_execution.enable',
    os.getenv('ENABLE_CODE_EXECUTION', 'True').lower() == 'true',
)

CODE_EXECUTION_ENGINE = ConfigVar(
    'CODE_EXECUTION_ENGINE',
    'code_execution.engine',
    os.getenv('CODE_EXECUTION_ENGINE', 'pyodide'),
)

CODE_EXECUTION_JUPYTER_URL = ConfigVar(
    'CODE_EXECUTION_JUPYTER_URL',
    'code_execution.jupyter.url',
    os.getenv('CODE_EXECUTION_JUPYTER_URL', ''),
)

CODE_EXECUTION_JUPYTER_AUTH = ConfigVar(
    'CODE_EXECUTION_JUPYTER_AUTH',
    'code_execution.jupyter.auth',
    os.getenv('CODE_EXECUTION_JUPYTER_AUTH', ''),
)

CODE_EXECUTION_JUPYTER_AUTH_TOKEN = ConfigVar(
    'CODE_EXECUTION_JUPYTER_AUTH_TOKEN',
    'code_execution.jupyter.auth_token',
    os.getenv('CODE_EXECUTION_JUPYTER_AUTH_TOKEN', ''),
)


CODE_EXECUTION_JUPYTER_AUTH_PASSWORD = ConfigVar(
    'CODE_EXECUTION_JUPYTER_AUTH_PASSWORD',
    'code_execution.jupyter.auth_password',
    os.getenv('CODE_EXECUTION_JUPYTER_AUTH_PASSWORD', ''),
)

CODE_EXECUTION_JUPYTER_TIMEOUT = ConfigVar(
    'CODE_EXECUTION_JUPYTER_TIMEOUT',
    'code_execution.jupyter.timeout',
    int(os.getenv('CODE_EXECUTION_JUPYTER_TIMEOUT', '60')),
)

ENABLE_CODE_INTERPRETER = ConfigVar(
    'ENABLE_CODE_INTERPRETER',
    'code_interpreter.enable',
    os.getenv('ENABLE_CODE_INTERPRETER', 'True').lower() == 'true',
)

ENABLE_MEMORIES = ConfigVar(
    'ENABLE_MEMORIES',
    'memories.enable',
    os.getenv('ENABLE_MEMORIES', 'True').lower() == 'true',
)

CODE_INTERPRETER_ENGINE = ConfigVar(
    'CODE_INTERPRETER_ENGINE',
    'code_interpreter.engine',
    os.getenv('CODE_INTERPRETER_ENGINE', 'pyodide'),
)

CODE_INTERPRETER_PROMPT_TEMPLATE = ConfigVar(
    'CODE_INTERPRETER_PROMPT_TEMPLATE',
    'code_interpreter.prompt_template',
    os.getenv('CODE_INTERPRETER_PROMPT_TEMPLATE', ''),
)

CODE_INTERPRETER_JUPYTER_URL = ConfigVar(
    'CODE_INTERPRETER_JUPYTER_URL',
    'code_interpreter.jupyter.url',
    os.getenv('CODE_INTERPRETER_JUPYTER_URL', os.getenv('CODE_EXECUTION_JUPYTER_URL', '')),
)

CODE_INTERPRETER_JUPYTER_AUTH = ConfigVar(
    'CODE_INTERPRETER_JUPYTER_AUTH',
    'code_interpreter.jupyter.auth',
    os.getenv(
        'CODE_INTERPRETER_JUPYTER_AUTH',
        os.getenv('CODE_EXECUTION_JUPYTER_AUTH', ''),
    ),
)

CODE_INTERPRETER_JUPYTER_AUTH_TOKEN = ConfigVar(
    'CODE_INTERPRETER_JUPYTER_AUTH_TOKEN',
    'code_interpreter.jupyter.auth_token',
    os.getenv(
        'CODE_INTERPRETER_JUPYTER_AUTH_TOKEN',
        os.getenv('CODE_EXECUTION_JUPYTER_AUTH_TOKEN', ''),
    ),
)


CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD = ConfigVar(
    'CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD',
    'code_interpreter.jupyter.auth_password',
    os.getenv(
        'CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD',
        os.getenv('CODE_EXECUTION_JUPYTER_AUTH_PASSWORD', ''),
    ),
)

CODE_INTERPRETER_JUPYTER_TIMEOUT = ConfigVar(
    'CODE_INTERPRETER_JUPYTER_TIMEOUT',
    'code_interpreter.jupyter.timeout',
    int(
        os.getenv(
            'CODE_INTERPRETER_JUPYTER_TIMEOUT',
            os.getenv('CODE_EXECUTION_JUPYTER_TIMEOUT', '60'),
        )
    ),
)

CODE_INTERPRETER_BLOCKED_MODULES = [
    library.strip() for library in os.getenv('CODE_INTERPRETER_BLOCKED_MODULES', '').split(',') if library.strip()
]

DEFAULT_CODE_INTERPRETER_PROMPT = """
#### Code Interpreter

You have access to a Python code interpreter via: `<code_interpreter type="code" lang="python"></code_interpreter>`

- The Python shell runs directly in the user's browser for fast execution of analysis, calculations, or problem-solving. Use it in this response.
- You can use a wide array of libraries for data manipulation, visualization, API calls, or any computational task. Think outside the box and harness Python's full potential.
- **You must enclose your code within `<code_interpreter type="code" lang="python">` XML tags** and stop right away. If you don't, the code won't execute.
- Do NOT use triple backticks (```py ... ```) inside the XML tags — that is markdown formatting, not executable Python code.
- **Always print meaningful outputs** (results, tables, summaries, visuals). Avoid implicit outputs; use explicit print statements.
- After obtaining output, **provide a concise analysis, interpretation, or next steps** to help the user understand the findings.
- If results are unclear or unexpected, refine the code and re-execute. Iterate until you deliver meaningful insights.
- **If a link to an image, audio, or any file appears in the output, display it exactly as-is** in your response so the user can access it. Do not modify the link.
- Respond in the chat's primary language. Default to English if multilingual.

Ensure the code interpreter is effectively utilized to achieve the highest-quality analysis for the user."""

# Appended to the code interpreter prompt only when engine is pyodide (not jupyter)
CODE_INTERPRETER_PYODIDE_PROMPT = """

##### Pyodide Environment

- This Python environment runs via Pyodide in the browser. **Do not install packages** — `pip install`, `subprocess`, and `micropip.install()` are not available.
- If a required library is unavailable, use an alternative approach with available modules. Do not attempt to install anything.

##### Persistent File System

- User-uploaded files are available at `/mnt/uploads/`. When the user asks you to work with their files, read from this directory.
- You can also write output files to `/mnt/uploads/` so the user can access and download them from the file browser.
- The file system persists across code executions within the same session.
- Use `import os; os.listdir('/mnt/uploads')` to discover available files."""


####################################
# Vector Database
####################################

VECTOR_DB = os.getenv('VECTOR_DB', 'chroma')

# Chroma
CHROMA_DATA_PATH = f'{DATA_DIR}/vector_db'

if VECTOR_DB == 'chroma':
    import chromadb

    CHROMA_TENANT = os.getenv('CHROMA_TENANT', chromadb.DEFAULT_TENANT)
    CHROMA_DATABASE = os.getenv('CHROMA_DATABASE', chromadb.DEFAULT_DATABASE)
    CHROMA_HTTP_HOST = os.getenv('CHROMA_HTTP_HOST', '')
    CHROMA_HTTP_PORT = int(os.getenv('CHROMA_HTTP_PORT', '8000'))
    CHROMA_CLIENT_AUTH_PROVIDER = os.getenv('CHROMA_CLIENT_AUTH_PROVIDER', '')
    CHROMA_CLIENT_AUTH_CREDENTIALS = os.getenv('CHROMA_CLIENT_AUTH_CREDENTIALS', '')
    # Comma-separated list of header=value pairs
    CHROMA_HTTP_HEADERS = os.getenv('CHROMA_HTTP_HEADERS', '')
    if CHROMA_HTTP_HEADERS:
        CHROMA_HTTP_HEADERS = dict([pair.split('=') for pair in CHROMA_HTTP_HEADERS.split(',')])
    else:
        CHROMA_HTTP_HEADERS = None
    CHROMA_HTTP_SSL = os.getenv('CHROMA_HTTP_SSL', 'false').lower() == 'true'
# this uses the model defined in the Dockerfile ENV variable. If you dont use docker or docker based deployments such as k8s, the default embedding model will be used (sentence-transformers/all-MiniLM-L6-v2)


# MariaDB Vector (mariadb-vector)
MARIADB_VECTOR_DB_URL = os.getenv('MARIADB_VECTOR_DB_URL', '').strip()

MARIADB_VECTOR_INITIALIZE_MAX_VECTOR_LENGTH = int(
    os.getenv('MARIADB_VECTOR_INITIALIZE_MAX_VECTOR_LENGTH', '1536').strip() or '1536'
)

# Distance strategy:
#   - cosine     => vec_distance_cosine(...)
#   - euclidean  => vec_distance_euclidean(...)
MARIADB_VECTOR_DISTANCE_STRATEGY = os.getenv('MARIADB_VECTOR_DISTANCE_STRATEGY', 'cosine').strip().lower()

# HNSW M parameter (MariaDB VECTOR INDEX ... M=<int>)
MARIADB_VECTOR_INDEX_M = int(os.getenv('MARIADB_VECTOR_INDEX_M', '8').strip() or '8')

# Pooling (MariaDB-Vector)
MARIADB_VECTOR_POOL_SIZE = os.getenv('MARIADB_VECTOR_POOL_SIZE', None)

if MARIADB_VECTOR_POOL_SIZE != None:
    try:
        MARIADB_VECTOR_POOL_SIZE = int(MARIADB_VECTOR_POOL_SIZE)
    except Exception:
        MARIADB_VECTOR_POOL_SIZE = None

MARIADB_VECTOR_POOL_MAX_OVERFLOW = os.getenv('MARIADB_VECTOR_POOL_MAX_OVERFLOW', 0)

if MARIADB_VECTOR_POOL_MAX_OVERFLOW == '':
    MARIADB_VECTOR_POOL_MAX_OVERFLOW = 0
else:
    try:
        MARIADB_VECTOR_POOL_MAX_OVERFLOW = int(MARIADB_VECTOR_POOL_MAX_OVERFLOW)
    except Exception:
        MARIADB_VECTOR_POOL_MAX_OVERFLOW = 0

MARIADB_VECTOR_POOL_TIMEOUT = os.getenv('MARIADB_VECTOR_POOL_TIMEOUT', 30)

if MARIADB_VECTOR_POOL_TIMEOUT == '':
    MARIADB_VECTOR_POOL_TIMEOUT = 30
else:
    try:
        MARIADB_VECTOR_POOL_TIMEOUT = int(MARIADB_VECTOR_POOL_TIMEOUT)
    except Exception:
        MARIADB_VECTOR_POOL_TIMEOUT = 30

MARIADB_VECTOR_POOL_RECYCLE = os.getenv('MARIADB_VECTOR_POOL_RECYCLE', 3600)

if MARIADB_VECTOR_POOL_RECYCLE == '':
    MARIADB_VECTOR_POOL_RECYCLE = 3600
else:
    try:
        MARIADB_VECTOR_POOL_RECYCLE = int(MARIADB_VECTOR_POOL_RECYCLE)
    except Exception:
        MARIADB_VECTOR_POOL_RECYCLE = 3600

ENABLE_MARIADB_VECTOR = True
if VECTOR_DB == 'mariadb-vector':
    if not MARIADB_VECTOR_DB_URL:
        ENABLE_MARIADB_VECTOR = False
    else:
        try:
            parsed = urlparse(MARIADB_VECTOR_DB_URL)
            scheme = (parsed.scheme or '').lower()
            # Require official driver so VECTOR binds as float32 bytes correctly
            if scheme != 'mariadb+mariadbconnector':
                ENABLE_MARIADB_VECTOR = False
        except Exception:
            ENABLE_MARIADB_VECTOR = False


# Milvus
MILVUS_URI = os.getenv('MILVUS_URI', f'{DATA_DIR}/vector_db/milvus.db')
MILVUS_DB = os.getenv('MILVUS_DB', 'default')
MILVUS_TOKEN = os.getenv('MILVUS_TOKEN', None)
MILVUS_INDEX_TYPE = os.getenv('MILVUS_INDEX_TYPE', 'HNSW')
MILVUS_METRIC_TYPE = os.getenv('MILVUS_METRIC_TYPE', 'COSINE')
MILVUS_HNSW_M = int(os.getenv('MILVUS_HNSW_M', '16'))
MILVUS_HNSW_EFCONSTRUCTION = int(os.getenv('MILVUS_HNSW_EFCONSTRUCTION', '100'))
MILVUS_IVF_FLAT_NLIST = int(os.getenv('MILVUS_IVF_FLAT_NLIST', '128'))
MILVUS_DISKANN_MAX_DEGREE = int(os.getenv('MILVUS_DISKANN_MAX_DEGREE', '56'))
MILVUS_DISKANN_SEARCH_LIST_SIZE = int(os.getenv('MILVUS_DISKANN_SEARCH_LIST_SIZE', '100'))
ENABLE_MILVUS_MULTITENANCY_MODE = os.getenv('ENABLE_MILVUS_MULTITENANCY_MODE', 'false').lower() == 'true'
# Hyphens not allowed, need to use underscores in collection names
MILVUS_COLLECTION_PREFIX = os.getenv('MILVUS_COLLECTION_PREFIX', 'open_webui')

# Qdrant
QDRANT_URI = os.getenv('QDRANT_URI', None)
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY', None)
QDRANT_ON_DISK = os.getenv('QDRANT_ON_DISK', 'false').lower() == 'true'
QDRANT_PREFER_GRPC = os.getenv('QDRANT_PREFER_GRPC', 'false').lower() == 'true'
QDRANT_GRPC_PORT = int(os.getenv('QDRANT_GRPC_PORT', '6334'))
QDRANT_TIMEOUT = int(os.getenv('QDRANT_TIMEOUT', '5'))
QDRANT_HNSW_M = int(os.getenv('QDRANT_HNSW_M', '16'))
ENABLE_QDRANT_MULTITENANCY_MODE = os.getenv('ENABLE_QDRANT_MULTITENANCY_MODE', 'true').lower() == 'true'
QDRANT_COLLECTION_PREFIX = os.getenv('QDRANT_COLLECTION_PREFIX', 'open-webui')

WEAVIATE_HTTP_HOST = os.getenv('WEAVIATE_HTTP_HOST', '')
WEAVIATE_GRPC_HOST = os.getenv('WEAVIATE_GRPC_HOST', '')
WEAVIATE_HTTP_PORT = int(os.getenv('WEAVIATE_HTTP_PORT', '8080'))
WEAVIATE_GRPC_PORT = int(os.getenv('WEAVIATE_GRPC_PORT', '50051'))
WEAVIATE_API_KEY = os.getenv('WEAVIATE_API_KEY')
WEAVIATE_HTTP_SECURE = os.getenv('WEAVIATE_HTTP_SECURE', 'false').lower() == 'true'
WEAVIATE_GRPC_SECURE = os.getenv('WEAVIATE_GRPC_SECURE', 'false').lower() == 'true'
WEAVIATE_SKIP_INIT_CHECKS = os.getenv('WEAVIATE_SKIP_INIT_CHECKS', 'false').lower() == 'true'

# OpenSearch
OPENSEARCH_URI = os.getenv('OPENSEARCH_URI', 'https://localhost:9200')
OPENSEARCH_SSL = os.getenv('OPENSEARCH_SSL', 'true').lower() == 'true'
OPENSEARCH_CERT_VERIFY = os.getenv('OPENSEARCH_CERT_VERIFY', 'false').lower() == 'true'
OPENSEARCH_USERNAME = os.getenv('OPENSEARCH_USERNAME', None)
OPENSEARCH_PASSWORD = os.getenv('OPENSEARCH_PASSWORD', None)

# ElasticSearch
ELASTICSEARCH_URL = os.getenv('ELASTICSEARCH_URL', 'https://localhost:9200')
ELASTICSEARCH_CA_CERTS = os.getenv('ELASTICSEARCH_CA_CERTS', None)
ELASTICSEARCH_API_KEY = os.getenv('ELASTICSEARCH_API_KEY', None)
ELASTICSEARCH_USERNAME = os.getenv('ELASTICSEARCH_USERNAME', None)
ELASTICSEARCH_PASSWORD = os.getenv('ELASTICSEARCH_PASSWORD', None)
ELASTICSEARCH_CLOUD_ID = os.getenv('ELASTICSEARCH_CLOUD_ID', None)
SSL_ASSERT_FINGERPRINT = os.getenv('SSL_ASSERT_FINGERPRINT', None)
ELASTICSEARCH_INDEX_PREFIX = os.getenv('ELASTICSEARCH_INDEX_PREFIX', 'open_webui_collections')
# Pgvector
PGVECTOR_DB_URL = os.getenv('PGVECTOR_DB_URL', DATABASE_URL)
if VECTOR_DB == 'pgvector' and not PGVECTOR_DB_URL.startswith('postgres'):
    raise ValueError(
        'Pgvector requires setting PGVECTOR_DB_URL or using Postgres with vector extension as the primary database.'
    )
PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH = int(os.getenv('PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH', '1536'))

PGVECTOR_USE_HALFVEC = os.getenv('PGVECTOR_USE_HALFVEC', 'false').lower() == 'true'

if PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH > 2000 and not PGVECTOR_USE_HALFVEC:
    raise ValueError(
        'PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH is set to '
        f'{PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH}, which exceeds the 2000 dimension limit of the '
        "'vector' type. Set PGVECTOR_USE_HALFVEC=true to enable the 'halfvec' "
        'type required for high-dimensional embeddings.'
    )

PGVECTOR_CREATE_EXTENSION = os.getenv('PGVECTOR_CREATE_EXTENSION', 'true').lower() == 'true'
PGVECTOR_PGCRYPTO = os.getenv('PGVECTOR_PGCRYPTO', 'false').lower() == 'true'
PGVECTOR_PGCRYPTO_KEY = os.getenv('PGVECTOR_PGCRYPTO_KEY', None)
if PGVECTOR_PGCRYPTO and not PGVECTOR_PGCRYPTO_KEY:
    raise ValueError('PGVECTOR_PGCRYPTO is enabled but PGVECTOR_PGCRYPTO_KEY is not set. Please provide a valid key.')


PGVECTOR_POOL_SIZE = os.getenv('PGVECTOR_POOL_SIZE', None)

if PGVECTOR_POOL_SIZE != None:
    try:
        PGVECTOR_POOL_SIZE = int(PGVECTOR_POOL_SIZE)
    except Exception:
        PGVECTOR_POOL_SIZE = None

PGVECTOR_POOL_MAX_OVERFLOW = os.getenv('PGVECTOR_POOL_MAX_OVERFLOW', 0)

if PGVECTOR_POOL_MAX_OVERFLOW == '':
    PGVECTOR_POOL_MAX_OVERFLOW = 0
else:
    try:
        PGVECTOR_POOL_MAX_OVERFLOW = int(PGVECTOR_POOL_MAX_OVERFLOW)
    except Exception:
        PGVECTOR_POOL_MAX_OVERFLOW = 0

PGVECTOR_POOL_TIMEOUT = os.getenv('PGVECTOR_POOL_TIMEOUT', 30)

if PGVECTOR_POOL_TIMEOUT == '':
    PGVECTOR_POOL_TIMEOUT = 30
else:
    try:
        PGVECTOR_POOL_TIMEOUT = int(PGVECTOR_POOL_TIMEOUT)
    except Exception:
        PGVECTOR_POOL_TIMEOUT = 30

PGVECTOR_POOL_RECYCLE = os.getenv('PGVECTOR_POOL_RECYCLE', 3600)

if PGVECTOR_POOL_RECYCLE == '':
    PGVECTOR_POOL_RECYCLE = 3600
else:
    try:
        PGVECTOR_POOL_RECYCLE = int(PGVECTOR_POOL_RECYCLE)
    except Exception:
        PGVECTOR_POOL_RECYCLE = 3600

PGVECTOR_INDEX_METHOD = os.getenv('PGVECTOR_INDEX_METHOD', '').strip().lower()
if PGVECTOR_INDEX_METHOD not in ('ivfflat', 'hnsw', ''):
    PGVECTOR_INDEX_METHOD = ''

PGVECTOR_HNSW_M = os.getenv('PGVECTOR_HNSW_M', 16)

if PGVECTOR_HNSW_M == '':
    PGVECTOR_HNSW_M = 16
else:
    try:
        PGVECTOR_HNSW_M = int(PGVECTOR_HNSW_M)
    except Exception:
        PGVECTOR_HNSW_M = 16

PGVECTOR_HNSW_EF_CONSTRUCTION = os.getenv('PGVECTOR_HNSW_EF_CONSTRUCTION', 64)

if PGVECTOR_HNSW_EF_CONSTRUCTION == '':
    PGVECTOR_HNSW_EF_CONSTRUCTION = 64
else:
    try:
        PGVECTOR_HNSW_EF_CONSTRUCTION = int(PGVECTOR_HNSW_EF_CONSTRUCTION)
    except Exception:
        PGVECTOR_HNSW_EF_CONSTRUCTION = 64

PGVECTOR_IVFFLAT_LISTS = os.getenv('PGVECTOR_IVFFLAT_LISTS', 100)

if PGVECTOR_IVFFLAT_LISTS == '':
    PGVECTOR_IVFFLAT_LISTS = 100
else:
    try:
        PGVECTOR_IVFFLAT_LISTS = int(PGVECTOR_IVFFLAT_LISTS)
    except Exception:
        PGVECTOR_IVFFLAT_LISTS = 100

# openGauss
OPENGAUSS_DB_URL = os.getenv('OPENGAUSS_DB_URL', DATABASE_URL)

OPENGAUSS_INITIALIZE_MAX_VECTOR_LENGTH = int(os.getenv('OPENGAUSS_INITIALIZE_MAX_VECTOR_LENGTH', '1536'))

OPENGAUSS_POOL_SIZE = os.getenv('OPENGAUSS_POOL_SIZE', None)

if OPENGAUSS_POOL_SIZE != None:
    try:
        OPENGAUSS_POOL_SIZE = int(OPENGAUSS_POOL_SIZE)
    except Exception:
        OPENGAUSS_POOL_SIZE = None

OPENGAUSS_POOL_MAX_OVERFLOW = os.getenv('OPENGAUSS_POOL_MAX_OVERFLOW', 0)

if OPENGAUSS_POOL_MAX_OVERFLOW == '':
    OPENGAUSS_POOL_MAX_OVERFLOW = 0
else:
    try:
        OPENGAUSS_POOL_MAX_OVERFLOW = int(OPENGAUSS_POOL_MAX_OVERFLOW)
    except Exception:
        OPENGAUSS_POOL_MAX_OVERFLOW = 0

OPENGAUSS_POOL_TIMEOUT = os.getenv('OPENGAUSS_POOL_TIMEOUT', 30)

if OPENGAUSS_POOL_TIMEOUT == '':
    OPENGAUSS_POOL_TIMEOUT = 30
else:
    try:
        OPENGAUSS_POOL_TIMEOUT = int(OPENGAUSS_POOL_TIMEOUT)
    except Exception:
        OPENGAUSS_POOL_TIMEOUT = 30

OPENGAUSS_POOL_RECYCLE = os.getenv('OPENGAUSS_POOL_RECYCLE', 3600)

if OPENGAUSS_POOL_RECYCLE == '':
    OPENGAUSS_POOL_RECYCLE = 3600
else:
    try:
        OPENGAUSS_POOL_RECYCLE = int(OPENGAUSS_POOL_RECYCLE)
    except Exception:
        OPENGAUSS_POOL_RECYCLE = 3600

# Pinecone
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY', None)
PINECONE_ENVIRONMENT = os.getenv('PINECONE_ENVIRONMENT', None)
PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME', 'open-webui-index')
PINECONE_DIMENSION = int(os.getenv('PINECONE_DIMENSION', 1536))  # or 3072, 1024, 768
PINECONE_METRIC = os.getenv('PINECONE_METRIC', 'cosine')
PINECONE_CLOUD = os.getenv('PINECONE_CLOUD', 'aws')  # or "gcp" or "azure"

# ORACLE23AI (Oracle23ai Vector Search)

ORACLE_DB_USE_WALLET = os.getenv('ORACLE_DB_USE_WALLET', 'false').lower() == 'true'
ORACLE_DB_USER = os.getenv('ORACLE_DB_USER', None)  #
ORACLE_DB_PASSWORD = os.getenv('ORACLE_DB_PASSWORD', None)  #
ORACLE_DB_DSN = os.getenv('ORACLE_DB_DSN', None)  #
ORACLE_WALLET_DIR = os.getenv('ORACLE_WALLET_DIR', None)
ORACLE_WALLET_PASSWORD = os.getenv('ORACLE_WALLET_PASSWORD', None)
ORACLE_VECTOR_LENGTH = os.getenv('ORACLE_VECTOR_LENGTH', 768)

ORACLE_DB_POOL_MIN = int(os.getenv('ORACLE_DB_POOL_MIN', 2))
ORACLE_DB_POOL_MAX = int(os.getenv('ORACLE_DB_POOL_MAX', 10))
ORACLE_DB_POOL_INCREMENT = int(os.getenv('ORACLE_DB_POOL_INCREMENT', 1))


if VECTOR_DB == 'oracle23ai':
    if not ORACLE_DB_USER or not ORACLE_DB_PASSWORD or not ORACLE_DB_DSN:
        raise ValueError('Oracle23ai requires setting ORACLE_DB_USER, ORACLE_DB_PASSWORD, and ORACLE_DB_DSN.')
    if ORACLE_DB_USE_WALLET and (not ORACLE_WALLET_DIR or not ORACLE_WALLET_PASSWORD):
        raise ValueError(
            'Oracle23ai requires setting ORACLE_WALLET_DIR and ORACLE_WALLET_PASSWORD when using wallet authentication.'
        )

log.info(f'VECTOR_DB: {VECTOR_DB}')

# S3 Vector
S3_VECTOR_BUCKET_NAME = os.getenv('S3_VECTOR_BUCKET_NAME', None)
S3_VECTOR_REGION = os.getenv('S3_VECTOR_REGION', None)

####################################
# Information Retrieval (RAG)
####################################


# If configured, Google Drive will be available as an upload option.
ENABLE_GOOGLE_DRIVE_INTEGRATION = ConfigVar(
    'ENABLE_GOOGLE_DRIVE_INTEGRATION',
    'google_drive.enable',
    os.getenv('ENABLE_GOOGLE_DRIVE_INTEGRATION', 'False').lower() == 'true',
)

GOOGLE_DRIVE_CLIENT_ID = ConfigVar(
    'GOOGLE_DRIVE_CLIENT_ID',
    'google_drive.client_id',
    os.getenv('GOOGLE_DRIVE_CLIENT_ID', ''),
)

GOOGLE_DRIVE_API_KEY = ConfigVar(
    'GOOGLE_DRIVE_API_KEY',
    'google_drive.api_key',
    os.getenv('GOOGLE_DRIVE_API_KEY', ''),
)

ENABLE_ONEDRIVE_INTEGRATION = ConfigVar(
    'ENABLE_ONEDRIVE_INTEGRATION',
    'onedrive.enable',
    os.getenv('ENABLE_ONEDRIVE_INTEGRATION', 'False').lower() == 'true',
)


ONEDRIVE_CLIENT_ID = os.getenv('ONEDRIVE_CLIENT_ID', '')
ONEDRIVE_CLIENT_ID_PERSONAL = os.getenv('ONEDRIVE_CLIENT_ID_PERSONAL', ONEDRIVE_CLIENT_ID)
ONEDRIVE_CLIENT_ID_BUSINESS = os.getenv('ONEDRIVE_CLIENT_ID_BUSINESS', ONEDRIVE_CLIENT_ID)

ENABLE_ONEDRIVE_PERSONAL = os.getenv('ENABLE_ONEDRIVE_PERSONAL', 'True').lower() == 'true' and bool(
    ONEDRIVE_CLIENT_ID_PERSONAL
)
ENABLE_ONEDRIVE_BUSINESS = os.getenv('ENABLE_ONEDRIVE_BUSINESS', 'True').lower() == 'true' and bool(
    ONEDRIVE_CLIENT_ID_BUSINESS
)

ONEDRIVE_SHAREPOINT_URL = ConfigVar(
    'ONEDRIVE_SHAREPOINT_URL',
    'onedrive.sharepoint_url',
    os.getenv('ONEDRIVE_SHAREPOINT_URL', ''),
)

ONEDRIVE_SHAREPOINT_TENANT_ID = ConfigVar(
    'ONEDRIVE_SHAREPOINT_TENANT_ID',
    'onedrive.sharepoint_tenant_id',
    os.getenv('ONEDRIVE_SHAREPOINT_TENANT_ID', ''),
)

# RAG Content Extraction
CONTENT_EXTRACTION_ENGINE = ConfigVar(
    'CONTENT_EXTRACTION_ENGINE',
    'rag.CONTENT_EXTRACTION_ENGINE',
    os.getenv('CONTENT_EXTRACTION_ENGINE', '').lower(),
)

DATALAB_MARKER_API_KEY = ConfigVar(
    'DATALAB_MARKER_API_KEY',
    'rag.datalab_marker_api_key',
    os.getenv('DATALAB_MARKER_API_KEY', ''),
)

DATALAB_MARKER_API_BASE_URL = ConfigVar(
    'DATALAB_MARKER_API_BASE_URL',
    'rag.datalab_marker_api_base_url',
    os.getenv('DATALAB_MARKER_API_BASE_URL', ''),
)

DATALAB_MARKER_ADDITIONAL_CONFIG = ConfigVar(
    'DATALAB_MARKER_ADDITIONAL_CONFIG',
    'rag.datalab_marker_additional_config',
    os.getenv('DATALAB_MARKER_ADDITIONAL_CONFIG', ''),
)

DATALAB_MARKER_USE_LLM = ConfigVar(
    'DATALAB_MARKER_USE_LLM',
    'rag.DATALAB_MARKER_USE_LLM',
    os.getenv('DATALAB_MARKER_USE_LLM', 'false').lower() == 'true',
)

DATALAB_MARKER_SKIP_CACHE = ConfigVar(
    'DATALAB_MARKER_SKIP_CACHE',
    'rag.datalab_marker_skip_cache',
    os.getenv('DATALAB_MARKER_SKIP_CACHE', 'false').lower() == 'true',
)

DATALAB_MARKER_FORCE_OCR = ConfigVar(
    'DATALAB_MARKER_FORCE_OCR',
    'rag.datalab_marker_force_ocr',
    os.getenv('DATALAB_MARKER_FORCE_OCR', 'false').lower() == 'true',
)

DATALAB_MARKER_PAGINATE = ConfigVar(
    'DATALAB_MARKER_PAGINATE',
    'rag.datalab_marker_paginate',
    os.getenv('DATALAB_MARKER_PAGINATE', 'false').lower() == 'true',
)

DATALAB_MARKER_STRIP_EXISTING_OCR = ConfigVar(
    'DATALAB_MARKER_STRIP_EXISTING_OCR',
    'rag.datalab_marker_strip_existing_ocr',
    os.getenv('DATALAB_MARKER_STRIP_EXISTING_OCR', 'false').lower() == 'true',
)

DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION = ConfigVar(
    'DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION',
    'rag.datalab_marker_disable_image_extraction',
    os.getenv('DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION', 'false').lower() == 'true',
)

DATALAB_MARKER_FORMAT_LINES = ConfigVar(
    'DATALAB_MARKER_FORMAT_LINES',
    'rag.datalab_marker_format_lines',
    os.getenv('DATALAB_MARKER_FORMAT_LINES', 'false').lower() == 'true',
)

DATALAB_MARKER_OUTPUT_FORMAT = ConfigVar(
    'DATALAB_MARKER_OUTPUT_FORMAT',
    'rag.datalab_marker_output_format',
    os.getenv('DATALAB_MARKER_OUTPUT_FORMAT', 'markdown'),
)

MINERU_API_MODE = ConfigVar(
    'MINERU_API_MODE',
    'rag.mineru_api_mode',
    os.getenv('MINERU_API_MODE', 'local'),  # "local" or "cloud"
)

MINERU_API_URL = ConfigVar(
    'MINERU_API_URL',
    'rag.mineru_api_url',
    os.getenv('MINERU_API_URL', 'http://localhost:8000'),
)

MINERU_API_TIMEOUT = ConfigVar(
    'MINERU_API_TIMEOUT',
    'rag.mineru_api_timeout',
    os.getenv('MINERU_API_TIMEOUT', '300'),
)

MINERU_API_KEY = ConfigVar(
    'MINERU_API_KEY',
    'rag.mineru_api_key',
    os.getenv('MINERU_API_KEY', ''),
)

mineru_params = os.getenv('MINERU_PARAMS', '')
try:
    mineru_params = json.loads(mineru_params)
except json.JSONDecodeError:
    mineru_params = {}

MINERU_PARAMS = ConfigVar(
    'MINERU_PARAMS',
    'rag.mineru_params',
    mineru_params,
)

EXTERNAL_DOCUMENT_LOADER_URL = ConfigVar(
    'EXTERNAL_DOCUMENT_LOADER_URL',
    'rag.external_document_loader_url',
    os.getenv('EXTERNAL_DOCUMENT_LOADER_URL', ''),
)

EXTERNAL_DOCUMENT_LOADER_API_KEY = ConfigVar(
    'EXTERNAL_DOCUMENT_LOADER_API_KEY',
    'rag.external_document_loader_api_key',
    os.getenv('EXTERNAL_DOCUMENT_LOADER_API_KEY', ''),
)

TIKA_SERVER_URL = ConfigVar(
    'TIKA_SERVER_URL',
    'rag.tika_server_url',
    os.getenv('TIKA_SERVER_URL', 'http://tika:9998'),  # Default for sidecar deployment
)

DOCLING_SERVER_URL = ConfigVar(
    'DOCLING_SERVER_URL',
    'rag.docling_server_url',
    os.getenv('DOCLING_SERVER_URL', 'http://docling:5001'),
)

DOCLING_API_KEY = ConfigVar(
    'DOCLING_API_KEY',
    'rag.docling_api_key',
    os.getenv('DOCLING_API_KEY', ''),
)

docling_params = os.getenv('DOCLING_PARAMS', '')
try:
    docling_params = json.loads(docling_params)
except json.JSONDecodeError:
    docling_params = {}

DOCLING_PARAMS = ConfigVar(
    'DOCLING_PARAMS',
    'rag.docling_params',
    docling_params,
)

DOCUMENT_INTELLIGENCE_ENDPOINT = ConfigVar(
    'DOCUMENT_INTELLIGENCE_ENDPOINT',
    'rag.document_intelligence_endpoint',
    os.getenv('DOCUMENT_INTELLIGENCE_ENDPOINT', ''),
)

DOCUMENT_INTELLIGENCE_KEY = ConfigVar(
    'DOCUMENT_INTELLIGENCE_KEY',
    'rag.document_intelligence_key',
    os.getenv('DOCUMENT_INTELLIGENCE_KEY', ''),
)

DOCUMENT_INTELLIGENCE_MODEL = ConfigVar(
    'DOCUMENT_INTELLIGENCE_MODEL',
    'rag.document_intelligence_model',
    os.getenv('DOCUMENT_INTELLIGENCE_MODEL', 'prebuilt-layout'),
)

MISTRAL_OCR_API_BASE_URL = ConfigVar(
    'MISTRAL_OCR_API_BASE_URL',
    'rag.MISTRAL_OCR_API_BASE_URL',
    os.getenv('MISTRAL_OCR_API_BASE_URL', 'https://api.mistral.ai/v1'),
)

MISTRAL_OCR_API_KEY = ConfigVar(
    'MISTRAL_OCR_API_KEY',
    'rag.mistral_ocr_api_key',
    os.getenv('MISTRAL_OCR_API_KEY', ''),
)

PADDLEOCR_VL_BASE_URL = ConfigVar(
    'PADDLEOCR_VL_BASE_URL',
    'rag.paddleocr_vl_base_url',
    os.getenv('PADDLEOCR_VL_BASE_URL', 'http://localhost:8080'),
)

PADDLEOCR_VL_TOKEN = ConfigVar(
    'PADDLEOCR_VL_TOKEN',
    'rag.paddleocr_vl_token',
    os.getenv('PADDLEOCR_VL_TOKEN', ''),
)

BYPASS_EMBEDDING_AND_RETRIEVAL = ConfigVar(
    'BYPASS_EMBEDDING_AND_RETRIEVAL',
    'rag.bypass_embedding_and_retrieval',
    os.getenv('BYPASS_EMBEDDING_AND_RETRIEVAL', 'False').lower() == 'true',
)


RAG_TOP_K = ConfigVar('RAG_TOP_K', 'rag.top_k', int(os.getenv('RAG_TOP_K', '3')))
RAG_TOP_K_RERANKER = ConfigVar(
    'RAG_TOP_K_RERANKER',
    'rag.top_k_reranker',
    int(os.getenv('RAG_TOP_K_RERANKER', '3')),
)
RAG_RELEVANCE_THRESHOLD = ConfigVar(
    'RAG_RELEVANCE_THRESHOLD',
    'rag.relevance_threshold',
    float(os.getenv('RAG_RELEVANCE_THRESHOLD', '0.0')),
)
RAG_HYBRID_BM25_WEIGHT = ConfigVar(
    'RAG_HYBRID_BM25_WEIGHT',
    'rag.hybrid_bm25_weight',
    float(os.getenv('RAG_HYBRID_BM25_WEIGHT', '0.5')),
)

ENABLE_RAG_HYBRID_SEARCH = ConfigVar(
    'ENABLE_RAG_HYBRID_SEARCH',
    'rag.enable_hybrid_search',
    os.getenv('ENABLE_RAG_HYBRID_SEARCH', '').lower() == 'true',
)

ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS = ConfigVar(
    'ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS',
    'rag.enable_hybrid_search_enriched_texts',
    os.getenv('ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS', 'False').lower() == 'true',
)

RAG_FULL_CONTEXT = ConfigVar(
    'RAG_FULL_CONTEXT',
    'rag.full_context',
    os.getenv('RAG_FULL_CONTEXT', 'False').lower() == 'true',
)

RAG_FILE_MAX_COUNT = ConfigVar(
    'RAG_FILE_MAX_COUNT',
    'rag.file.max_count',
    (int(os.getenv('RAG_FILE_MAX_COUNT')) if os.getenv('RAG_FILE_MAX_COUNT') else None),
)

RAG_FILE_MAX_SIZE = ConfigVar(
    'RAG_FILE_MAX_SIZE',
    'rag.file.max_size',
    (int(os.getenv('RAG_FILE_MAX_SIZE')) if os.getenv('RAG_FILE_MAX_SIZE') else None),
)

FILE_IMAGE_COMPRESSION_WIDTH = ConfigVar(
    'FILE_IMAGE_COMPRESSION_WIDTH',
    'file.image_compression_width',
    (int(os.getenv('FILE_IMAGE_COMPRESSION_WIDTH')) if os.getenv('FILE_IMAGE_COMPRESSION_WIDTH') else None),
)

FILE_IMAGE_COMPRESSION_HEIGHT = ConfigVar(
    'FILE_IMAGE_COMPRESSION_HEIGHT',
    'file.image_compression_height',
    (int(os.getenv('FILE_IMAGE_COMPRESSION_HEIGHT')) if os.getenv('FILE_IMAGE_COMPRESSION_HEIGHT') else None),
)


RAG_ALLOWED_FILE_EXTENSIONS = ConfigVar(
    'RAG_ALLOWED_FILE_EXTENSIONS',
    'rag.file.allowed_extensions',
    [ext.strip() for ext in os.getenv('RAG_ALLOWED_FILE_EXTENSIONS', '').split(',') if ext.strip()],
)

RAG_EMBEDDING_ENGINE = ConfigVar(
    'RAG_EMBEDDING_ENGINE',
    'rag.embedding_engine',
    os.getenv('RAG_EMBEDDING_ENGINE', ''),
)

PDF_EXTRACT_IMAGES = ConfigVar(
    'PDF_EXTRACT_IMAGES',
    'rag.pdf_extract_images',
    os.getenv('PDF_EXTRACT_IMAGES', 'False').lower() == 'true',
)

PDF_LOADER_MODE = ConfigVar(
    'PDF_LOADER_MODE',
    'rag.pdf_loader_mode',
    os.getenv('PDF_LOADER_MODE', 'page'),
)

RAG_EMBEDDING_MODEL = ConfigVar(
    'RAG_EMBEDDING_MODEL',
    'rag.embedding_model',
    os.getenv('RAG_EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
)
log.info(f'Embedding model set: {RAG_EMBEDDING_MODEL.value}')

RAG_EMBEDDING_MODEL_AUTO_UPDATE = (
    not OFFLINE_MODE and os.getenv('RAG_EMBEDDING_MODEL_AUTO_UPDATE', 'True').lower() == 'true'
)

RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE = os.getenv('RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE', 'True').lower() == 'true'

RAG_EMBEDDING_BATCH_SIZE = ConfigVar(
    'RAG_EMBEDDING_BATCH_SIZE',
    'rag.embedding_batch_size',
    int(os.getenv('RAG_EMBEDDING_BATCH_SIZE') or os.getenv('RAG_EMBEDDING_OPENAI_BATCH_SIZE', '1')),
)

ENABLE_ASYNC_EMBEDDING = ConfigVar(
    'ENABLE_ASYNC_EMBEDDING',
    'rag.enable_async_embedding',
    os.getenv('ENABLE_ASYNC_EMBEDDING', 'True').lower() == 'true',
)

RAG_EMBEDDING_CONCURRENT_REQUESTS = ConfigVar(
    'RAG_EMBEDDING_CONCURRENT_REQUESTS',
    'rag.embedding_concurrent_requests',
    int(os.getenv('RAG_EMBEDDING_CONCURRENT_REQUESTS', '0')),
)

RAG_EMBEDDING_QUERY_PREFIX = os.getenv('RAG_EMBEDDING_QUERY_PREFIX', None)

RAG_EMBEDDING_CONTENT_PREFIX = os.getenv('RAG_EMBEDDING_CONTENT_PREFIX', None)

RAG_EMBEDDING_PREFIX_FIELD_NAME = os.getenv('RAG_EMBEDDING_PREFIX_FIELD_NAME', None)

RAG_RERANKING_ENGINE = ConfigVar(
    'RAG_RERANKING_ENGINE',
    'rag.reranking_engine',
    os.getenv('RAG_RERANKING_ENGINE', ''),
)

RAG_RERANKING_MODEL = ConfigVar(
    'RAG_RERANKING_MODEL',
    'rag.reranking_model',
    os.getenv('RAG_RERANKING_MODEL', ''),
)
if RAG_RERANKING_MODEL.value != '':
    log.info(f'Reranking model set: {RAG_RERANKING_MODEL.value}')


RAG_RERANKING_MODEL_AUTO_UPDATE = (
    not OFFLINE_MODE and os.getenv('RAG_RERANKING_MODEL_AUTO_UPDATE', 'True').lower() == 'true'
)

RAG_RERANKING_MODEL_TRUST_REMOTE_CODE = os.getenv('RAG_RERANKING_MODEL_TRUST_REMOTE_CODE', 'True').lower() == 'true'

RAG_RERANKING_BATCH_SIZE = ConfigVar(
    'RAG_RERANKING_BATCH_SIZE',
    'rag.reranking_batch_size',
    int(os.getenv('RAG_RERANKING_BATCH_SIZE', '32')),
)

RAG_EXTERNAL_RERANKER_URL = ConfigVar(
    'RAG_EXTERNAL_RERANKER_URL',
    'rag.external_reranker_url',
    os.getenv('RAG_EXTERNAL_RERANKER_URL', ''),
)

RAG_EXTERNAL_RERANKER_API_KEY = ConfigVar(
    'RAG_EXTERNAL_RERANKER_API_KEY',
    'rag.external_reranker_api_key',
    os.getenv('RAG_EXTERNAL_RERANKER_API_KEY', ''),
)

RAG_EXTERNAL_RERANKER_TIMEOUT = ConfigVar(
    'RAG_EXTERNAL_RERANKER_TIMEOUT',
    'rag.external_reranker_timeout',
    os.getenv('RAG_EXTERNAL_RERANKER_TIMEOUT', ''),
)


RAG_TEXT_SPLITTER = ConfigVar(
    'RAG_TEXT_SPLITTER',
    'rag.text_splitter',
    os.getenv('RAG_TEXT_SPLITTER', ''),
)

ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER = ConfigVar(
    'ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER',
    'rag.enable_markdown_header_text_splitter',
    os.getenv('ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER', 'True').lower() == 'true',
)


TIKTOKEN_CACHE_DIR = os.getenv('TIKTOKEN_CACHE_DIR', f'{CACHE_DIR}/tiktoken')
TIKTOKEN_ENCODING_NAME = ConfigVar(
    'TIKTOKEN_ENCODING_NAME',
    'rag.tiktoken_encoding_name',
    os.getenv('TIKTOKEN_ENCODING_NAME', 'cl100k_base'),
)


CHUNK_SIZE = ConfigVar('CHUNK_SIZE', 'rag.chunk_size', int(os.getenv('CHUNK_SIZE', '1000')))

CHUNK_MIN_SIZE_TARGET = ConfigVar(
    'CHUNK_MIN_SIZE_TARGET',
    'rag.chunk_min_size_target',
    int(os.getenv('CHUNK_MIN_SIZE_TARGET', '0')),
)

CHUNK_OVERLAP = ConfigVar(
    'CHUNK_OVERLAP',
    'rag.chunk_overlap',
    int(os.getenv('CHUNK_OVERLAP', '100')),
)

DEFAULT_RAG_TEMPLATE = """### Task:
Respond to the user query using the provided context, incorporating inline citations in the format [id] **only when the <source> tag includes an explicit id attribute** (e.g., <source id="1">).

### Guidelines:
- If you don't know the answer, clearly state that.
- If uncertain, ask the user for clarification.
- Respond in the same language as the user's query.
- If the context is unreadable or of poor quality, inform the user and provide the best possible answer.
- If the answer isn't present in the context but you possess the knowledge, explain this to the user and provide the answer using your own understanding.
- **Only include inline citations using [id] (e.g., [1], [2]) when the <source> tag includes an id attribute.**
- Do not cite if the <source> tag does not contain an id attribute.
- Do not use XML tags in your response.
- Ensure citations are concise and directly related to the information provided.

### Example of Citation:
If the user asks about a specific topic and the information is found in a source with a provided id attribute, the response should include the citation like in the following example:
* "According to the study, the proposed method increases efficiency by 20% [1]."

### Output:
Provide a clear and direct response to the user's query, including inline citations in the format [id] only when the <source> tag with id attribute is present in the context.

<context>
{{CONTEXT}}
</context>
"""

RAG_TEMPLATE = ConfigVar(
    'RAG_TEMPLATE',
    'rag.template',
    os.getenv('RAG_TEMPLATE', DEFAULT_RAG_TEMPLATE),
)

RAG_OPENAI_API_BASE_URL = ConfigVar(
    'RAG_OPENAI_API_BASE_URL',
    'rag.openai_api_base_url',
    os.getenv('RAG_OPENAI_API_BASE_URL', OPENAI_API_BASE_URL),
)
RAG_OPENAI_API_KEY = ConfigVar(
    'RAG_OPENAI_API_KEY',
    'rag.openai_api_key',
    os.getenv('RAG_OPENAI_API_KEY', OPENAI_API_KEY),
)

RAG_AZURE_OPENAI_BASE_URL = ConfigVar(
    'RAG_AZURE_OPENAI_BASE_URL',
    'rag.azure_openai.base_url',
    os.getenv('RAG_AZURE_OPENAI_BASE_URL', ''),
)
RAG_AZURE_OPENAI_API_KEY = ConfigVar(
    'RAG_AZURE_OPENAI_API_KEY',
    'rag.azure_openai.api_key',
    os.getenv('RAG_AZURE_OPENAI_API_KEY', ''),
)
RAG_AZURE_OPENAI_API_VERSION = ConfigVar(
    'RAG_AZURE_OPENAI_API_VERSION',
    'rag.azure_openai.api_version',
    os.getenv('RAG_AZURE_OPENAI_API_VERSION', ''),
)

RAG_OLLAMA_BASE_URL = ConfigVar(
    'RAG_OLLAMA_BASE_URL',
    'rag.ollama.url',
    os.getenv('RAG_OLLAMA_BASE_URL', OLLAMA_BASE_URL),
)

RAG_OLLAMA_API_KEY = ConfigVar(
    'RAG_OLLAMA_API_KEY',
    'rag.ollama.key',
    os.getenv('RAG_OLLAMA_API_KEY', ''),
)


ENABLE_RAG_LOCAL_WEB_FETCH = os.getenv('ENABLE_RAG_LOCAL_WEB_FETCH', 'False').lower() == 'true'


DEFAULT_WEB_FETCH_FILTER_LIST = [
    '!169.254.169.254',
    '!fd00:ec2::254',
    '!metadata.google.internal',
    '!metadata.azure.com',
    '!100.100.100.200',
]

web_fetch_filter_list = os.getenv('WEB_FETCH_FILTER_LIST', '')
if web_fetch_filter_list == '':
    web_fetch_filter_list = []
else:
    web_fetch_filter_list = [item.strip() for item in web_fetch_filter_list.split(',') if item.strip()]

WEB_FETCH_FILTER_LIST = list(set(DEFAULT_WEB_FETCH_FILTER_LIST + web_fetch_filter_list))


YOUTUBE_LOADER_LANGUAGE = ConfigVar(
    'YOUTUBE_LOADER_LANGUAGE',
    'rag.youtube_loader_language',
    os.getenv('YOUTUBE_LOADER_LANGUAGE', 'en').split(','),
)

YOUTUBE_LOADER_PROXY_URL = ConfigVar(
    'YOUTUBE_LOADER_PROXY_URL',
    'rag.youtube_loader_proxy_url',
    os.getenv('YOUTUBE_LOADER_PROXY_URL', ''),
)


####################################
# Web Search (RAG)
####################################

ENABLE_WEB_SEARCH = ConfigVar(
    'ENABLE_WEB_SEARCH',
    'rag.web.search.enable',
    os.getenv('ENABLE_WEB_SEARCH', 'False').lower() == 'true',
)

WEB_SEARCH_ENGINE = ConfigVar(
    'WEB_SEARCH_ENGINE',
    'rag.web.search.engine',
    os.getenv('WEB_SEARCH_ENGINE', ''),
)

BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL = ConfigVar(
    'BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL',
    'rag.web.search.bypass_embedding_and_retrieval',
    os.getenv('BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL', 'False').lower() == 'true',
)


BYPASS_WEB_SEARCH_WEB_LOADER = ConfigVar(
    'BYPASS_WEB_SEARCH_WEB_LOADER',
    'rag.web.search.bypass_web_loader',
    os.getenv('BYPASS_WEB_SEARCH_WEB_LOADER', 'False').lower() == 'true',
)

WEB_SEARCH_RESULT_COUNT = ConfigVar(
    'WEB_SEARCH_RESULT_COUNT',
    'rag.web.search.result_count',
    int(os.getenv('WEB_SEARCH_RESULT_COUNT', '3')),
)


try:
    web_search_domain_filter_list = json.loads(os.getenv('WEB_SEARCH_DOMAIN_FILTER_LIST', '[]'))
except Exception as e:
    web_search_domain_filter_list = [
        # "wikipedia.com",
        # "wikimedia.org",
        # "wikidata.org",
        # "!stackoverflow.com",
    ]

# You can provide a list of your own websites to filter after performing a web search.
# This ensures the highest level of safety and reliability of the information sources.
WEB_SEARCH_DOMAIN_FILTER_LIST = ConfigVar(
    'WEB_SEARCH_DOMAIN_FILTER_LIST',
    'rag.web.search.domain.filter_list',
    web_search_domain_filter_list,
)

WEB_SEARCH_CONCURRENT_REQUESTS = ConfigVar(
    'WEB_SEARCH_CONCURRENT_REQUESTS',
    'rag.web.search.concurrent_requests',
    int(os.getenv('WEB_SEARCH_CONCURRENT_REQUESTS', '0')),
)

WEB_FETCH_MAX_CONTENT_LENGTH = ConfigVar(
    'WEB_FETCH_MAX_CONTENT_LENGTH',
    'rag.web.fetch.max_content_length',
    (int(os.getenv('WEB_FETCH_MAX_CONTENT_LENGTH')) if os.getenv('WEB_FETCH_MAX_CONTENT_LENGTH') else None),
)

WEB_LOADER_ENGINE = ConfigVar(
    'WEB_LOADER_ENGINE',
    'rag.web.loader.engine',
    os.getenv('WEB_LOADER_ENGINE', ''),
)


WEB_LOADER_CONCURRENT_REQUESTS = ConfigVar(
    'WEB_LOADER_CONCURRENT_REQUESTS',
    'rag.web.loader.concurrent_requests',
    int(os.getenv('WEB_LOADER_CONCURRENT_REQUESTS', '10')),
)

WEB_LOADER_TIMEOUT = ConfigVar(
    'WEB_LOADER_TIMEOUT',
    'rag.web.loader.timeout',
    os.getenv('WEB_LOADER_TIMEOUT', ''),
)


ENABLE_WEB_LOADER_SSL_VERIFICATION = ConfigVar(
    'ENABLE_WEB_LOADER_SSL_VERIFICATION',
    'rag.web.loader.ssl_verification',
    os.getenv('ENABLE_WEB_LOADER_SSL_VERIFICATION', 'True').lower() == 'true',
)

WEB_SEARCH_TRUST_ENV = ConfigVar(
    'WEB_SEARCH_TRUST_ENV',
    'rag.web.search.trust_env',
    os.getenv('WEB_SEARCH_TRUST_ENV', 'True').lower() == 'true',
)


OLLAMA_CLOUD_WEB_SEARCH_API_KEY = ConfigVar(
    'OLLAMA_CLOUD_WEB_SEARCH_API_KEY',
    'rag.web.search.ollama_cloud_api_key',
    os.getenv('OLLAMA_CLOUD_API_KEY', ''),
)

SEARXNG_QUERY_URL = ConfigVar(
    'SEARXNG_QUERY_URL',
    'rag.web.search.searxng_query_url',
    os.getenv('SEARXNG_QUERY_URL', ''),
)

SEARXNG_LANGUAGE = ConfigVar(
    'SEARXNG_LANGUAGE',
    'rag.web.search.searxng_language',
    os.getenv('SEARXNG_LANGUAGE', 'all'),
)

YACY_QUERY_URL = ConfigVar(
    'YACY_QUERY_URL',
    'rag.web.search.yacy_query_url',
    os.getenv('YACY_QUERY_URL', ''),
)

YACY_USERNAME = ConfigVar(
    'YACY_USERNAME',
    'rag.web.search.yacy_username',
    os.getenv('YACY_USERNAME', ''),
)

YACY_PASSWORD = ConfigVar(
    'YACY_PASSWORD',
    'rag.web.search.yacy_password',
    os.getenv('YACY_PASSWORD', ''),
)

GOOGLE_PSE_API_KEY = ConfigVar(
    'GOOGLE_PSE_API_KEY',
    'rag.web.search.google_pse_api_key',
    os.getenv('GOOGLE_PSE_API_KEY', ''),
)

GOOGLE_PSE_ENGINE_ID = ConfigVar(
    'GOOGLE_PSE_ENGINE_ID',
    'rag.web.search.google_pse_engine_id',
    os.getenv('GOOGLE_PSE_ENGINE_ID', ''),
)

BRAVE_SEARCH_API_KEY = ConfigVar(
    'BRAVE_SEARCH_API_KEY',
    'rag.web.search.brave_search_api_key',
    os.getenv('BRAVE_SEARCH_API_KEY', ''),
)

BRAVE_SEARCH_CONTEXT_TOKENS = ConfigVar(
    'BRAVE_SEARCH_CONTEXT_TOKENS',
    'rag.web.search.brave_search_context_tokens',
    int(os.getenv('BRAVE_SEARCH_CONTEXT_TOKENS', '8192')),
)

KAGI_SEARCH_API_KEY = ConfigVar(
    'KAGI_SEARCH_API_KEY',
    'rag.web.search.kagi_search_api_key',
    os.getenv('KAGI_SEARCH_API_KEY', ''),
)

MOJEEK_SEARCH_API_KEY = ConfigVar(
    'MOJEEK_SEARCH_API_KEY',
    'rag.web.search.mojeek_search_api_key',
    os.getenv('MOJEEK_SEARCH_API_KEY', ''),
)

BOCHA_SEARCH_API_KEY = ConfigVar(
    'BOCHA_SEARCH_API_KEY',
    'rag.web.search.bocha_search_api_key',
    os.getenv('BOCHA_SEARCH_API_KEY', ''),
)

SERPSTACK_API_KEY = ConfigVar(
    'SERPSTACK_API_KEY',
    'rag.web.search.serpstack_api_key',
    os.getenv('SERPSTACK_API_KEY', ''),
)

SERPSTACK_HTTPS = ConfigVar(
    'SERPSTACK_HTTPS',
    'rag.web.search.serpstack_https',
    os.getenv('SERPSTACK_HTTPS', 'True').lower() == 'true',
)

SERPER_API_KEY = ConfigVar(
    'SERPER_API_KEY',
    'rag.web.search.serper_api_key',
    os.getenv('SERPER_API_KEY', ''),
)

SERPLY_API_KEY = ConfigVar(
    'SERPLY_API_KEY',
    'rag.web.search.serply_api_key',
    os.getenv('SERPLY_API_KEY', ''),
)

DDGS_BACKEND = ConfigVar(
    'DDGS_BACKEND',
    'rag.web.search.ddgs_backend',
    os.getenv('DDGS_BACKEND', 'auto'),
)

JINA_API_KEY = ConfigVar(
    'JINA_API_KEY',
    'rag.web.search.jina_api_key',
    os.getenv('JINA_API_KEY', ''),
)

JINA_API_BASE_URL = ConfigVar(
    'JINA_API_BASE_URL',
    'rag.web.search.jina_api_base_url',
    os.getenv('JINA_API_BASE_URL', ''),
)

SEARCHAPI_API_KEY = ConfigVar(
    'SEARCHAPI_API_KEY',
    'rag.web.search.searchapi_api_key',
    os.getenv('SEARCHAPI_API_KEY', ''),
)

SEARCHAPI_ENGINE = ConfigVar(
    'SEARCHAPI_ENGINE',
    'rag.web.search.searchapi_engine',
    os.getenv('SEARCHAPI_ENGINE', ''),
)

SERPAPI_API_KEY = ConfigVar(
    'SERPAPI_API_KEY',
    'rag.web.search.serpapi_api_key',
    os.getenv('SERPAPI_API_KEY', ''),
)

SERPAPI_ENGINE = ConfigVar(
    'SERPAPI_ENGINE',
    'rag.web.search.serpapi_engine',
    os.getenv('SERPAPI_ENGINE', ''),
)

BING_SEARCH_V7_ENDPOINT = ConfigVar(
    'BING_SEARCH_V7_ENDPOINT',
    'rag.web.search.bing_search_v7_endpoint',
    os.getenv('BING_SEARCH_V7_ENDPOINT', 'https://api.bing.microsoft.com/v7.0/search'),
)

BING_SEARCH_V7_SUBSCRIPTION_KEY = ConfigVar(
    'BING_SEARCH_V7_SUBSCRIPTION_KEY',
    'rag.web.search.bing_search_v7_subscription_key',
    os.getenv('BING_SEARCH_V7_SUBSCRIPTION_KEY', ''),
)

AZURE_AI_SEARCH_API_KEY = ConfigVar(
    'AZURE_AI_SEARCH_API_KEY',
    'rag.web.search.azure_ai_search_api_key',
    os.getenv('AZURE_AI_SEARCH_API_KEY', ''),
)

AZURE_AI_SEARCH_ENDPOINT = ConfigVar(
    'AZURE_AI_SEARCH_ENDPOINT',
    'rag.web.search.azure_ai_search_endpoint',
    os.getenv('AZURE_AI_SEARCH_ENDPOINT', ''),
)

AZURE_AI_SEARCH_INDEX_NAME = ConfigVar(
    'AZURE_AI_SEARCH_INDEX_NAME',
    'rag.web.search.azure_ai_search_index_name',
    os.getenv('AZURE_AI_SEARCH_INDEX_NAME', ''),
)

EXA_API_KEY = ConfigVar(
    'EXA_API_KEY',
    'rag.web.search.exa_api_key',
    os.getenv('EXA_API_KEY', ''),
)

PERPLEXITY_API_KEY = ConfigVar(
    'PERPLEXITY_API_KEY',
    'rag.web.search.perplexity_api_key',
    os.getenv('PERPLEXITY_API_KEY', ''),
)

PERPLEXITY_MODEL = ConfigVar(
    'PERPLEXITY_MODEL',
    'rag.web.search.perplexity_model',
    os.getenv('PERPLEXITY_MODEL', 'sonar'),
)

PERPLEXITY_SEARCH_CONTEXT_USAGE = ConfigVar(
    'PERPLEXITY_SEARCH_CONTEXT_USAGE',
    'rag.web.search.perplexity_search_context_usage',
    os.getenv('PERPLEXITY_SEARCH_CONTEXT_USAGE', 'medium'),
)

PERPLEXITY_SEARCH_API_URL = ConfigVar(
    'PERPLEXITY_SEARCH_API_URL',
    'rag.web.search.perplexity_search_api_url',
    os.getenv('PERPLEXITY_SEARCH_API_URL', 'https://api.perplexity.ai/search'),
)

SOUGOU_API_SID = ConfigVar(
    'SOUGOU_API_SID',
    'rag.web.search.sougou_api_sid',
    os.getenv('SOUGOU_API_SID', ''),
)

SOUGOU_API_SK = ConfigVar(
    'SOUGOU_API_SK',
    'rag.web.search.sougou_api_sk',
    os.getenv('SOUGOU_API_SK', ''),
)

TAVILY_API_KEY = ConfigVar(
    'TAVILY_API_KEY',
    'rag.web.search.tavily_api_key',
    os.getenv('TAVILY_API_KEY', ''),
)

TAVILY_EXTRACT_DEPTH = ConfigVar(
    'TAVILY_EXTRACT_DEPTH',
    'rag.web.search.tavily_extract_depth',
    os.getenv('TAVILY_EXTRACT_DEPTH', 'basic'),
)

PLAYWRIGHT_WS_URL = ConfigVar(
    'PLAYWRIGHT_WS_URL',
    'rag.web.loader.playwright_ws_url',
    os.getenv('PLAYWRIGHT_WS_URL', ''),
)

PLAYWRIGHT_TIMEOUT = ConfigVar(
    'PLAYWRIGHT_TIMEOUT',
    'rag.web.loader.playwright_timeout',
    int(os.getenv('PLAYWRIGHT_TIMEOUT', '10000')),
)

FIRECRAWL_API_KEY = ConfigVar(
    'FIRECRAWL_API_KEY',
    'rag.web.loader.firecrawl_api_key',
    os.getenv('FIRECRAWL_API_KEY', ''),
)

FIRECRAWL_API_BASE_URL = ConfigVar(
    'FIRECRAWL_API_BASE_URL',
    'rag.web.loader.firecrawl_api_url',
    os.getenv('FIRECRAWL_API_BASE_URL', 'https://api.firecrawl.dev'),
)

FIRECRAWL_TIMEOUT = ConfigVar(
    'FIRECRAWL_TIMEOUT',
    'rag.web.loader.firecrawl_timeout',
    os.getenv('FIRECRAWL_TIMEOUT', ''),
)

EXTERNAL_WEB_SEARCH_URL = ConfigVar(
    'EXTERNAL_WEB_SEARCH_URL',
    'rag.web.search.external_web_search_url',
    os.getenv('EXTERNAL_WEB_SEARCH_URL', ''),
)

EXTERNAL_WEB_SEARCH_API_KEY = ConfigVar(
    'EXTERNAL_WEB_SEARCH_API_KEY',
    'rag.web.search.external_web_search_api_key',
    os.getenv('EXTERNAL_WEB_SEARCH_API_KEY', ''),
)

EXTERNAL_WEB_LOADER_URL = ConfigVar(
    'EXTERNAL_WEB_LOADER_URL',
    'rag.web.loader.external_web_loader_url',
    os.getenv('EXTERNAL_WEB_LOADER_URL', ''),
)

EXTERNAL_WEB_LOADER_API_KEY = ConfigVar(
    'EXTERNAL_WEB_LOADER_API_KEY',
    'rag.web.loader.external_web_loader_api_key',
    os.getenv('EXTERNAL_WEB_LOADER_API_KEY', ''),
)

YANDEX_WEB_SEARCH_URL = ConfigVar(
    'YANDEX_WEB_SEARCH_URL',
    'rag.web.search.yandex_web_search_url',
    os.getenv('YANDEX_WEB_SEARCH_URL', ''),
)

YANDEX_WEB_SEARCH_API_KEY = ConfigVar(
    'YANDEX_WEB_SEARCH_API_KEY',
    'rag.web.search.yandex_web_search_api_key',
    os.getenv('YANDEX_WEB_SEARCH_API_KEY', ''),
)

YANDEX_WEB_SEARCH_CONFIG = ConfigVar(
    'YANDEX_WEB_SEARCH_CONFIG',
    'rag.web.search.yandex_web_search_config',
    os.getenv('YANDEX_WEB_SEARCH_CONFIG', ''),
)

YOUCOM_API_KEY = ConfigVar(
    'YOUCOM_API_KEY',
    'rag.web.search.youcom_api_key',
    os.getenv('YOUCOM_API_KEY', ''),
)

LINKUP_API_KEY = ConfigVar(
    'LINKUP_API_KEY',
    'rag.web.search.linkup_api_key',
    os.getenv('LINKUP_API_KEY', ''),
)

linkup_search_params = os.getenv('LINKUP_SEARCH_PARAMS', '')
try:
    linkup_search_params = json.loads(linkup_search_params)
except json.JSONDecodeError:
    linkup_search_params = {}

LINKUP_SEARCH_PARAMS = ConfigVar(
    'LINKUP_SEARCH_PARAMS',
    'rag.web.search.linkup_search_params',
    linkup_search_params,
)

####################################
# Images
####################################

ENABLE_IMAGE_GENERATION = ConfigVar(
    'ENABLE_IMAGE_GENERATION',
    'image_generation.enable',
    os.getenv('ENABLE_IMAGE_GENERATION', '').lower() == 'true',
)

IMAGE_GENERATION_ENGINE = ConfigVar(
    'IMAGE_GENERATION_ENGINE',
    'image_generation.engine',
    os.getenv('IMAGE_GENERATION_ENGINE', 'openai'),
)

IMAGE_GENERATION_MODEL = ConfigVar(
    'IMAGE_GENERATION_MODEL',
    'image_generation.model',
    os.getenv('IMAGE_GENERATION_MODEL', ''),
)

# Regex pattern for models that support IMAGE_SIZE = "auto".
IMAGE_AUTO_SIZE_MODELS_REGEX_PATTERN = os.getenv('IMAGE_AUTO_SIZE_MODELS_REGEX_PATTERN', '^gpt-image')

# Regex pattern for models that return URLs instead of base64 data.
IMAGE_URL_RESPONSE_MODELS_REGEX_PATTERN = os.getenv('IMAGE_URL_RESPONSE_MODELS_REGEX_PATTERN', '^gpt-image')

IMAGE_SIZE = ConfigVar('IMAGE_SIZE', 'image_generation.size', os.getenv('IMAGE_SIZE', '512x512'))

IMAGE_STEPS = ConfigVar('IMAGE_STEPS', 'image_generation.steps', int(os.getenv('IMAGE_STEPS', 50)))

ENABLE_IMAGE_PROMPT_GENERATION = ConfigVar(
    'ENABLE_IMAGE_PROMPT_GENERATION',
    'image_generation.prompt.enable',
    os.getenv('ENABLE_IMAGE_PROMPT_GENERATION', 'true').lower() == 'true',
)

AUTOMATIC1111_BASE_URL = ConfigVar(
    'AUTOMATIC1111_BASE_URL',
    'image_generation.automatic1111.base_url',
    os.getenv('AUTOMATIC1111_BASE_URL', ''),
)
AUTOMATIC1111_API_AUTH = ConfigVar(
    'AUTOMATIC1111_API_AUTH',
    'image_generation.automatic1111.api_auth',
    os.getenv('AUTOMATIC1111_API_AUTH', ''),
)

automatic1111_params = os.getenv('AUTOMATIC1111_PARAMS', '')
try:
    automatic1111_params = json.loads(automatic1111_params)
except json.JSONDecodeError:
    automatic1111_params = {}

AUTOMATIC1111_PARAMS = ConfigVar(
    'AUTOMATIC1111_PARAMS',
    'image_generation.automatic1111.api_params',
    automatic1111_params,
)

COMFYUI_BASE_URL = ConfigVar(
    'COMFYUI_BASE_URL',
    'image_generation.comfyui.base_url',
    os.getenv('COMFYUI_BASE_URL', ''),
)

COMFYUI_API_KEY = ConfigVar(
    'COMFYUI_API_KEY',
    'image_generation.comfyui.api_key',
    os.getenv('COMFYUI_API_KEY', ''),
)

COMFYUI_DEFAULT_WORKFLOW = """
{
  "3": {
    "inputs": {
      "seed": 0,
      "steps": 20,
      "cfg": 8,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1,
      "model": [
        "4",
        0
      ],
      "positive": [
        "6",
        0
      ],
      "negative": [
        "7",
        0
      ],
      "latent_image": [
        "5",
        0
      ]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "KSampler"
    }
  },
  "4": {
    "inputs": {
      "ckpt_name": "model.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint"
    }
  },
  "5": {
    "inputs": {
      "width": 512,
      "height": 512,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  },
  "6": {
    "inputs": {
      "text": "Prompt",
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "7": {
    "inputs": {
      "text": "",
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "8": {
    "inputs": {
      "samples": [
        "3",
        0
      ],
      "vae": [
        "4",
        2
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "9": {
    "inputs": {
      "filename_prefix": "ComfyUI",
      "images": [
        "8",
        0
      ]
    },
    "class_type": "SaveImage",
    "_meta": {
      "title": "Save Image"
    }
  }
}
"""


COMFYUI_WORKFLOW = ConfigVar(
    'COMFYUI_WORKFLOW',
    'image_generation.comfyui.workflow',
    os.getenv('COMFYUI_WORKFLOW', COMFYUI_DEFAULT_WORKFLOW),
)

comfyui_workflow_nodes = os.getenv('COMFYUI_WORKFLOW_NODES', '')
try:
    comfyui_workflow_nodes = json.loads(comfyui_workflow_nodes)
except json.JSONDecodeError:
    comfyui_workflow_nodes = []

COMFYUI_WORKFLOW_NODES = ConfigVar(
    'COMFYUI_WORKFLOW_NODES',
    'image_generation.comfyui.nodes',
    comfyui_workflow_nodes,
)

IMAGES_OPENAI_API_BASE_URL = ConfigVar(
    'IMAGES_OPENAI_API_BASE_URL',
    'image_generation.openai.api_base_url',
    os.getenv('IMAGES_OPENAI_API_BASE_URL', OPENAI_API_BASE_URL),
)
IMAGES_OPENAI_API_VERSION = ConfigVar(
    'IMAGES_OPENAI_API_VERSION',
    'image_generation.openai.api_version',
    os.getenv('IMAGES_OPENAI_API_VERSION', ''),
)

IMAGES_OPENAI_API_KEY = ConfigVar(
    'IMAGES_OPENAI_API_KEY',
    'image_generation.openai.api_key',
    os.getenv('IMAGES_OPENAI_API_KEY', OPENAI_API_KEY),
)

images_openai_params = os.getenv('IMAGES_OPENAI_PARAMS', '')
try:
    images_openai_params = json.loads(images_openai_params)
except json.JSONDecodeError:
    images_openai_params = {}


IMAGES_OPENAI_API_PARAMS = ConfigVar('IMAGES_OPENAI_API_PARAMS', 'image_generation.openai.params', images_openai_params)


IMAGES_GEMINI_API_BASE_URL = ConfigVar(
    'IMAGES_GEMINI_API_BASE_URL',
    'image_generation.gemini.api_base_url',
    os.getenv('IMAGES_GEMINI_API_BASE_URL', GEMINI_API_BASE_URL),
)
IMAGES_GEMINI_API_KEY = ConfigVar(
    'IMAGES_GEMINI_API_KEY',
    'image_generation.gemini.api_key',
    os.getenv('IMAGES_GEMINI_API_KEY', GEMINI_API_KEY),
)

IMAGES_GEMINI_ENDPOINT_METHOD = ConfigVar(
    'IMAGES_GEMINI_ENDPOINT_METHOD',
    'image_generation.gemini.endpoint_method',
    os.getenv('IMAGES_GEMINI_ENDPOINT_METHOD', ''),
)

ENABLE_IMAGE_EDIT = ConfigVar(
    'ENABLE_IMAGE_EDIT',
    'images.edit.enable',
    os.getenv('ENABLE_IMAGE_EDIT', '').lower() == 'true',
)

IMAGE_EDIT_ENGINE = ConfigVar(
    'IMAGE_EDIT_ENGINE',
    'images.edit.engine',
    os.getenv('IMAGE_EDIT_ENGINE', 'openai'),
)

IMAGE_EDIT_MODEL = ConfigVar(
    'IMAGE_EDIT_MODEL',
    'images.edit.model',
    os.getenv('IMAGE_EDIT_MODEL', ''),
)

IMAGE_EDIT_SIZE = ConfigVar('IMAGE_EDIT_SIZE', 'images.edit.size', os.getenv('IMAGE_EDIT_SIZE', ''))

IMAGES_EDIT_OPENAI_API_BASE_URL = ConfigVar(
    'IMAGES_EDIT_OPENAI_API_BASE_URL',
    'images.edit.openai.api_base_url',
    os.getenv('IMAGES_EDIT_OPENAI_API_BASE_URL', OPENAI_API_BASE_URL),
)
IMAGES_EDIT_OPENAI_API_VERSION = ConfigVar(
    'IMAGES_EDIT_OPENAI_API_VERSION',
    'images.edit.openai.api_version',
    os.getenv('IMAGES_EDIT_OPENAI_API_VERSION', ''),
)

IMAGES_EDIT_OPENAI_API_KEY = ConfigVar(
    'IMAGES_EDIT_OPENAI_API_KEY',
    'images.edit.openai.api_key',
    os.getenv('IMAGES_EDIT_OPENAI_API_KEY', OPENAI_API_KEY),
)

IMAGES_EDIT_GEMINI_API_BASE_URL = ConfigVar(
    'IMAGES_EDIT_GEMINI_API_BASE_URL',
    'images.edit.gemini.api_base_url',
    os.getenv('IMAGES_EDIT_GEMINI_API_BASE_URL', GEMINI_API_BASE_URL),
)
IMAGES_EDIT_GEMINI_API_KEY = ConfigVar(
    'IMAGES_EDIT_GEMINI_API_KEY',
    'images.edit.gemini.api_key',
    os.getenv('IMAGES_EDIT_GEMINI_API_KEY', GEMINI_API_KEY),
)


IMAGES_EDIT_COMFYUI_BASE_URL = ConfigVar(
    'IMAGES_EDIT_COMFYUI_BASE_URL',
    'images.edit.comfyui.base_url',
    os.getenv('IMAGES_EDIT_COMFYUI_BASE_URL', ''),
)
IMAGES_EDIT_COMFYUI_API_KEY = ConfigVar(
    'IMAGES_EDIT_COMFYUI_API_KEY',
    'images.edit.comfyui.api_key',
    os.getenv('IMAGES_EDIT_COMFYUI_API_KEY', ''),
)

IMAGES_EDIT_COMFYUI_WORKFLOW = ConfigVar(
    'IMAGES_EDIT_COMFYUI_WORKFLOW',
    'images.edit.comfyui.workflow',
    os.getenv('IMAGES_EDIT_COMFYUI_WORKFLOW', ''),
)

images_edit_comfyui_workflow_nodes = os.getenv('IMAGES_EDIT_COMFYUI_WORKFLOW_NODES', '')
try:
    images_edit_comfyui_workflow_nodes = json.loads(images_edit_comfyui_workflow_nodes)
except json.JSONDecodeError:
    images_edit_comfyui_workflow_nodes = []

IMAGES_EDIT_COMFYUI_WORKFLOW_NODES = ConfigVar(
    'IMAGES_EDIT_COMFYUI_WORKFLOW_NODES',
    'images.edit.comfyui.nodes',
    images_edit_comfyui_workflow_nodes,
)

####################################
# Audio
####################################

# Transcription
WHISPER_MODEL = ConfigVar(
    'WHISPER_MODEL',
    'audio.stt.whisper_model',
    os.getenv('WHISPER_MODEL', 'base'),
)

WHISPER_COMPUTE_TYPE = os.getenv('WHISPER_COMPUTE_TYPE', 'int8')
WHISPER_MODEL_DIR = os.getenv('WHISPER_MODEL_DIR', f'{CACHE_DIR}/whisper/models')
WHISPER_MODEL_AUTO_UPDATE = not OFFLINE_MODE and os.getenv('WHISPER_MODEL_AUTO_UPDATE', '').lower() == 'true'

WHISPER_VAD_FILTER = os.getenv('WHISPER_VAD_FILTER', 'False').lower() == 'true'

WHISPER_MULTILINGUAL = os.getenv('WHISPER_MULTILINGUAL', 'False').lower() == 'true'

WHISPER_LANGUAGE = os.getenv('WHISPER_LANGUAGE', '').lower() or None

# Add Deepgram configuration
DEEPGRAM_API_KEY = ConfigVar(
    'DEEPGRAM_API_KEY',
    'audio.stt.deepgram.api_key',
    os.getenv('DEEPGRAM_API_KEY', ''),
)

# ElevenLabs configuration
ELEVENLABS_API_BASE_URL = os.getenv('ELEVENLABS_API_BASE_URL', 'https://api.elevenlabs.io')

AUDIO_STT_OPENAI_API_BASE_URL = ConfigVar(
    'AUDIO_STT_OPENAI_API_BASE_URL',
    'audio.stt.openai.api_base_url',
    os.getenv('AUDIO_STT_OPENAI_API_BASE_URL', OPENAI_API_BASE_URL),
)

AUDIO_STT_OPENAI_API_KEY = ConfigVar(
    'AUDIO_STT_OPENAI_API_KEY',
    'audio.stt.openai.api_key',
    os.getenv('AUDIO_STT_OPENAI_API_KEY', OPENAI_API_KEY),
)

AUDIO_STT_ENGINE = ConfigVar(
    'AUDIO_STT_ENGINE',
    'audio.stt.engine',
    os.getenv('AUDIO_STT_ENGINE', ''),
)

AUDIO_STT_MODEL = ConfigVar(
    'AUDIO_STT_MODEL',
    'audio.stt.model',
    os.getenv('AUDIO_STT_MODEL', ''),
)

AUDIO_STT_SUPPORTED_CONTENT_TYPES = ConfigVar(
    'AUDIO_STT_SUPPORTED_CONTENT_TYPES',
    'audio.stt.supported_content_types',
    [
        content_type.strip()
        for content_type in os.getenv('AUDIO_STT_SUPPORTED_CONTENT_TYPES', '').split(',')
        if content_type.strip()
    ],
)

AUDIO_STT_ALLOWED_EXTENSIONS = ConfigVar(
    'AUDIO_STT_ALLOWED_EXTENSIONS',
    'audio.stt.allowed_extensions',
    [
        ext.strip()
        for ext in os.getenv(
            'AUDIO_STT_ALLOWED_EXTENSIONS',
            'mp3,wav,m4a,webm,ogg,flac,mp4,mpga,mpeg',
        ).split(',')
        if ext.strip()
    ],
)

AUDIO_STT_AZURE_API_KEY = ConfigVar(
    'AUDIO_STT_AZURE_API_KEY',
    'audio.stt.azure.api_key',
    os.getenv('AUDIO_STT_AZURE_API_KEY', ''),
)

AUDIO_STT_AZURE_REGION = ConfigVar(
    'AUDIO_STT_AZURE_REGION',
    'audio.stt.azure.region',
    os.getenv('AUDIO_STT_AZURE_REGION', ''),
)

AUDIO_STT_AZURE_LOCALES = ConfigVar(
    'AUDIO_STT_AZURE_LOCALES',
    'audio.stt.azure.locales',
    os.getenv('AUDIO_STT_AZURE_LOCALES', ''),
)

AUDIO_STT_AZURE_BASE_URL = ConfigVar(
    'AUDIO_STT_AZURE_BASE_URL',
    'audio.stt.azure.base_url',
    os.getenv('AUDIO_STT_AZURE_BASE_URL', ''),
)

AUDIO_STT_AZURE_MAX_SPEAKERS = ConfigVar(
    'AUDIO_STT_AZURE_MAX_SPEAKERS',
    'audio.stt.azure.max_speakers',
    os.getenv('AUDIO_STT_AZURE_MAX_SPEAKERS', ''),
)

AUDIO_STT_MISTRAL_API_KEY = ConfigVar(
    'AUDIO_STT_MISTRAL_API_KEY',
    'audio.stt.mistral.api_key',
    os.getenv('AUDIO_STT_MISTRAL_API_KEY', ''),
)

AUDIO_STT_MISTRAL_API_BASE_URL = ConfigVar(
    'AUDIO_STT_MISTRAL_API_BASE_URL',
    'audio.stt.mistral.api_base_url',
    os.getenv('AUDIO_STT_MISTRAL_API_BASE_URL', 'https://api.mistral.ai/v1'),
)

AUDIO_STT_MISTRAL_USE_CHAT_COMPLETIONS = ConfigVar(
    'AUDIO_STT_MISTRAL_USE_CHAT_COMPLETIONS',
    'audio.stt.mistral.use_chat_completions',
    os.getenv('AUDIO_STT_MISTRAL_USE_CHAT_COMPLETIONS', 'false').lower() == 'true',
)

AUDIO_TTS_OPENAI_API_BASE_URL = ConfigVar(
    'AUDIO_TTS_OPENAI_API_BASE_URL',
    'audio.tts.openai.api_base_url',
    os.getenv('AUDIO_TTS_OPENAI_API_BASE_URL', OPENAI_API_BASE_URL),
)
AUDIO_TTS_OPENAI_API_KEY = ConfigVar(
    'AUDIO_TTS_OPENAI_API_KEY',
    'audio.tts.openai.api_key',
    os.getenv('AUDIO_TTS_OPENAI_API_KEY', OPENAI_API_KEY),
)

audio_tts_openai_params = os.getenv('AUDIO_TTS_OPENAI_PARAMS', '')
try:
    audio_tts_openai_params = json.loads(audio_tts_openai_params)
except json.JSONDecodeError:
    audio_tts_openai_params = {}

AUDIO_TTS_OPENAI_PARAMS = ConfigVar(
    'AUDIO_TTS_OPENAI_PARAMS',
    'audio.tts.openai.params',
    audio_tts_openai_params,
)


AUDIO_TTS_API_KEY = ConfigVar(
    'AUDIO_TTS_API_KEY',
    'audio.tts.api_key',
    os.getenv('AUDIO_TTS_API_KEY', ''),
)

AUDIO_TTS_ENGINE = ConfigVar(
    'AUDIO_TTS_ENGINE',
    'audio.tts.engine',
    os.getenv('AUDIO_TTS_ENGINE', ''),
)


AUDIO_TTS_MODEL = ConfigVar(
    'AUDIO_TTS_MODEL',
    'audio.tts.model',
    os.getenv('AUDIO_TTS_MODEL', 'tts-1'),  # OpenAI default model
)

AUDIO_TTS_VOICE = ConfigVar(
    'AUDIO_TTS_VOICE',
    'audio.tts.voice',
    os.getenv('AUDIO_TTS_VOICE', 'alloy'),  # OpenAI default voice
)

AUDIO_TTS_SPLIT_ON = ConfigVar(
    'AUDIO_TTS_SPLIT_ON',
    'audio.tts.split_on',
    os.getenv('AUDIO_TTS_SPLIT_ON', 'punctuation'),
)

AUDIO_TTS_AZURE_SPEECH_REGION = ConfigVar(
    'AUDIO_TTS_AZURE_SPEECH_REGION',
    'audio.tts.azure.speech_region',
    os.getenv('AUDIO_TTS_AZURE_SPEECH_REGION', ''),
)

AUDIO_TTS_AZURE_SPEECH_BASE_URL = ConfigVar(
    'AUDIO_TTS_AZURE_SPEECH_BASE_URL',
    'audio.tts.azure.speech_base_url',
    os.getenv('AUDIO_TTS_AZURE_SPEECH_BASE_URL', ''),
)

AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT = ConfigVar(
    'AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT',
    'audio.tts.azure.speech_output_format',
    os.getenv('AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT', 'audio-24khz-160kbitrate-mono-mp3'),
)

AUDIO_TTS_MISTRAL_API_KEY = ConfigVar(
    'AUDIO_TTS_MISTRAL_API_KEY',
    'audio.tts.mistral.api_key',
    os.getenv('AUDIO_TTS_MISTRAL_API_KEY', ''),
)

AUDIO_TTS_MISTRAL_API_BASE_URL = ConfigVar(
    'AUDIO_TTS_MISTRAL_API_BASE_URL',
    'audio.tts.mistral.api_base_url',
    os.getenv('AUDIO_TTS_MISTRAL_API_BASE_URL', 'https://api.mistral.ai/v1'),
)

####################################
# WEBUI
####################################


WEBUI_URL = ConfigVar('WEBUI_URL', 'webui.url', os.getenv('WEBUI_URL', ''))


ENABLE_SIGNUP = ConfigVar(
    'ENABLE_SIGNUP',
    'ui.enable_signup',
    (False if not WEBUI_AUTH else os.getenv('ENABLE_SIGNUP', 'True').lower() == 'true'),
)

ENABLE_LOGIN_FORM = ConfigVar(
    'ENABLE_LOGIN_FORM',
    'ui.enable_login_form',
    os.getenv('ENABLE_LOGIN_FORM', 'True').lower() == 'true',
)

ENABLE_PASSWORD_CHANGE_FORM = ConfigVar(
    'ENABLE_PASSWORD_CHANGE_FORM',
    'ui.enable_password_change_form',
    os.getenv('ENABLE_PASSWORD_CHANGE_FORM', 'True').lower() == 'true',
)

ENABLE_PASSWORD_AUTH = os.getenv('ENABLE_PASSWORD_AUTH', 'True').lower() == 'true'

DEFAULT_LOCALE = ConfigVar(
    'DEFAULT_LOCALE',
    'ui.default_locale',
    os.getenv('DEFAULT_LOCALE', ''),
)

DEFAULT_MODELS = ConfigVar('DEFAULT_MODELS', 'ui.default_models', os.getenv('DEFAULT_MODELS', None))

DEFAULT_PINNED_MODELS = ConfigVar(
    'DEFAULT_PINNED_MODELS',
    'ui.default_pinned_models',
    os.getenv('DEFAULT_PINNED_MODELS', None),
)

try:
    default_prompt_suggestions = json.loads(os.getenv('DEFAULT_PROMPT_SUGGESTIONS', '[]'))
except Exception as e:
    log.exception(f'Error loading DEFAULT_PROMPT_SUGGESTIONS: {e}')
    default_prompt_suggestions = []
if default_prompt_suggestions == []:
    default_prompt_suggestions = [
        {
            'title': ['Help me study', 'vocabulary for a college entrance exam'],
            'content': "Help me study vocabulary: write a sentence for me to fill in the blank, and I'll try to pick the correct option.",
        },
        {
            'title': ['Give me ideas', "for what to do with my kids' art"],
            'content': "What are 5 creative things I could do with my kids' art? I don't want to throw them away, but it's also so much clutter.",
        },
        {
            'title': ['Tell me a fun fact', 'about the Roman Empire'],
            'content': 'Tell me a random fun fact about the Roman Empire',
        },
        {
            'title': ['Show me a code snippet', "of a website's sticky header"],
            'content': "Show me a code snippet of a website's sticky header in CSS and JavaScript.",
        },
        {
            'title': [
                'Explain options trading',
                "if I'm familiar with buying and selling stocks",
            ],
            'content': "Explain options trading in simple terms if I'm familiar with buying and selling stocks.",
        },
        {
            'title': ['Overcome procrastination', 'give me tips'],
            'content': 'Could you start by asking me about instances when I procrastinate the most and then give me some suggestions to overcome it?',
        },
    ]

DEFAULT_PROMPT_SUGGESTIONS = ConfigVar(
    'DEFAULT_PROMPT_SUGGESTIONS',
    'ui.prompt_suggestions',
    default_prompt_suggestions,
)

MODEL_ORDER_LIST = ConfigVar(
    'MODEL_ORDER_LIST',
    'ui.model_order_list',
    [],
)

try:
    default_model_metadata = json.loads(os.getenv('DEFAULT_MODEL_METADATA', '{}'))
except Exception as e:
    log.exception(f'Error loading DEFAULT_MODEL_METADATA: {e}')
    default_model_metadata = {}

DEFAULT_MODEL_METADATA = ConfigVar(
    'DEFAULT_MODEL_METADATA',
    'models.default_metadata',
    default_model_metadata,
)

try:
    default_model_params = json.loads(os.getenv('DEFAULT_MODEL_PARAMS', '{}'))
except Exception as e:
    log.exception(f'Error loading DEFAULT_MODEL_PARAMS: {e}')
    default_model_params = {}

DEFAULT_MODEL_PARAMS = ConfigVar(
    'DEFAULT_MODEL_PARAMS',
    'models.default_params',
    default_model_params,
)

DEFAULT_USER_ROLE = ConfigVar(
    'DEFAULT_USER_ROLE',
    'ui.default_user_role',
    os.getenv('DEFAULT_USER_ROLE', 'pending'),
)

DEFAULT_GROUP_ID = ConfigVar(
    'DEFAULT_GROUP_ID',
    'ui.default_group_id',
    os.getenv('DEFAULT_GROUP_ID', ''),
)

PENDING_USER_OVERLAY_TITLE = ConfigVar(
    'PENDING_USER_OVERLAY_TITLE',
    'ui.pending_user_overlay_title',
    os.getenv('PENDING_USER_OVERLAY_TITLE', ''),
)

PENDING_USER_OVERLAY_CONTENT = ConfigVar(
    'PENDING_USER_OVERLAY_CONTENT',
    'ui.pending_user_overlay_content',
    os.getenv('PENDING_USER_OVERLAY_CONTENT', ''),
)


RESPONSE_WATERMARK = ConfigVar(
    'RESPONSE_WATERMARK',
    'ui.watermark',
    os.getenv('RESPONSE_WATERMARK', ''),
)

IFRAME_CSP = os.getenv('IFRAME_CSP', '')

USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ACCESS = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ACCESS', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_TOOLS_ACCESS = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_TOOLS_ACCESS', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_SKILLS_ACCESS = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_SKILLS_ACCESS', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_MODELS_IMPORT = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_MODELS_IMPORT', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_MODELS_EXPORT = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_MODELS_EXPORT', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_PROMPTS_IMPORT = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_PROMPTS_IMPORT', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_PROMPTS_EXPORT = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_PROMPTS_EXPORT', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_TOOLS_IMPORT = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_TOOLS_IMPORT', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_TOOLS_EXPORT = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_TOOLS_EXPORT', 'False').lower() == 'true'
)


USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_SHARING = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_SHARING', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_PUBLIC_SHARING = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_PUBLIC_SHARING', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ALLOW_SHARING = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ALLOW_SHARING', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ALLOW_PUBLIC_SHARING = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ALLOW_PUBLIC_SHARING', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_PROMPTS_ALLOW_SHARING = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_PROMPTS_ALLOW_SHARING', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_PROMPTS_ALLOW_PUBLIC_SHARING = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_PROMPTS_ALLOW_PUBLIC_SHARING', 'False').lower() == 'true'
)


USER_PERMISSIONS_WORKSPACE_TOOLS_ALLOW_SHARING = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_TOOLS_ALLOW_SHARING', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_TOOLS_ALLOW_PUBLIC_SHARING = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_TOOLS_ALLOW_PUBLIC_SHARING', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_SKILLS_ALLOW_SHARING = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_SKILLS_ALLOW_SHARING', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_SKILLS_ALLOW_PUBLIC_SHARING = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_SKILLS_ALLOW_PUBLIC_SHARING', 'False').lower() == 'true'
)


USER_PERMISSIONS_NOTES_ALLOW_SHARING = os.getenv('USER_PERMISSIONS_NOTES_ALLOW_SHARING', 'False').lower() == 'true'

USER_PERMISSIONS_NOTES_ALLOW_PUBLIC_SHARING = (
    os.getenv('USER_PERMISSIONS_NOTES_ALLOW_PUBLIC_SHARING', 'False').lower() == 'true'
)

USER_PERMISSIONS_CALENDAR_ALLOW_PUBLIC_SHARING = (
    os.getenv('USER_PERMISSIONS_CALENDAR_ALLOW_PUBLIC_SHARING', 'False').lower() == 'true'
)

USER_PERMISSIONS_ACCESS_GRANTS_ALLOW_USERS = (
    os.getenv('USER_PERMISSIONS_ACCESS_GRANTS_ALLOW_USERS', 'True').lower() == 'true'
)


USER_PERMISSIONS_CHAT_CONTROLS = os.getenv('USER_PERMISSIONS_CHAT_CONTROLS', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_VALVES = os.getenv('USER_PERMISSIONS_CHAT_VALVES', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_SYSTEM_PROMPT = os.getenv('USER_PERMISSIONS_CHAT_SYSTEM_PROMPT', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_PARAMS = os.getenv('USER_PERMISSIONS_CHAT_PARAMS', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_FILE_UPLOAD = os.getenv('USER_PERMISSIONS_CHAT_FILE_UPLOAD', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_WEB_UPLOAD = os.getenv('USER_PERMISSIONS_CHAT_WEB_UPLOAD', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_DELETE = os.getenv('USER_PERMISSIONS_CHAT_DELETE', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_DELETE_MESSAGE = os.getenv('USER_PERMISSIONS_CHAT_DELETE_MESSAGE', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_CONTINUE_RESPONSE = os.getenv('USER_PERMISSIONS_CHAT_CONTINUE_RESPONSE', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_REGENERATE_RESPONSE = (
    os.getenv('USER_PERMISSIONS_CHAT_REGENERATE_RESPONSE', 'True').lower() == 'true'
)

USER_PERMISSIONS_CHAT_RATE_RESPONSE = os.getenv('USER_PERMISSIONS_CHAT_RATE_RESPONSE', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_EDIT = os.getenv('USER_PERMISSIONS_CHAT_EDIT', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_SHARE = os.getenv('USER_PERMISSIONS_CHAT_SHARE', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_ALLOW_PUBLIC_SHARING = (
    os.getenv('USER_PERMISSIONS_CHAT_ALLOW_PUBLIC_SHARING', 'False').lower() == 'true'
)

USER_PERMISSIONS_CHAT_EXPORT = os.getenv('USER_PERMISSIONS_CHAT_EXPORT', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_STT = os.getenv('USER_PERMISSIONS_CHAT_STT', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_TTS = os.getenv('USER_PERMISSIONS_CHAT_TTS', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_CALL = os.getenv('USER_PERMISSIONS_CHAT_CALL', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_MULTIPLE_MODELS = os.getenv('USER_PERMISSIONS_CHAT_MULTIPLE_MODELS', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_TEMPORARY = os.getenv('USER_PERMISSIONS_CHAT_TEMPORARY', 'True').lower() == 'true'

USER_PERMISSIONS_CHAT_TEMPORARY_ENFORCED = (
    os.getenv('USER_PERMISSIONS_CHAT_TEMPORARY_ENFORCED', 'False').lower() == 'true'
)


USER_PERMISSIONS_FEATURES_DIRECT_TOOL_SERVERS = (
    os.getenv('USER_PERMISSIONS_FEATURES_DIRECT_TOOL_SERVERS', 'False').lower() == 'true'
)

USER_PERMISSIONS_FEATURES_WEB_SEARCH = os.getenv('USER_PERMISSIONS_FEATURES_WEB_SEARCH', 'True').lower() == 'true'

USER_PERMISSIONS_FEATURES_IMAGE_GENERATION = (
    os.getenv('USER_PERMISSIONS_FEATURES_IMAGE_GENERATION', 'True').lower() == 'true'
)

USER_PERMISSIONS_FEATURES_CODE_INTERPRETER = (
    os.getenv('USER_PERMISSIONS_FEATURES_CODE_INTERPRETER', 'True').lower() == 'true'
)

USER_PERMISSIONS_FEATURES_FOLDERS = os.getenv('USER_PERMISSIONS_FEATURES_FOLDERS', 'True').lower() == 'true'

USER_PERMISSIONS_FEATURES_NOTES = os.getenv('USER_PERMISSIONS_FEATURES_NOTES', 'True').lower() == 'true'

USER_PERMISSIONS_FEATURES_CHANNELS = os.getenv('USER_PERMISSIONS_FEATURES_CHANNELS', 'True').lower() == 'true'

USER_PERMISSIONS_FEATURES_API_KEYS = os.getenv('USER_PERMISSIONS_FEATURES_API_KEYS', 'False').lower() == 'true'

USER_PERMISSIONS_FEATURES_MEMORIES = os.getenv('USER_PERMISSIONS_FEATURES_MEMORIES', 'True').lower() == 'true'

USER_PERMISSIONS_FEATURES_AUTOMATIONS = os.getenv('USER_PERMISSIONS_FEATURES_AUTOMATIONS', 'False').lower() == 'true'

USER_PERMISSIONS_FEATURES_CALENDAR = os.getenv('USER_PERMISSIONS_FEATURES_CALENDAR', 'True').lower() == 'true'


USER_PERMISSIONS_SETTINGS_INTERFACE = os.getenv('USER_PERMISSIONS_SETTINGS_INTERFACE', 'True').lower() == 'true'


DEFAULT_USER_PERMISSIONS = {
    'workspace': {
        'models': USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS,
        'knowledge': USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ACCESS,
        'prompts': USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS,
        'tools': USER_PERMISSIONS_WORKSPACE_TOOLS_ACCESS,
        'skills': USER_PERMISSIONS_WORKSPACE_SKILLS_ACCESS,
        'models_import': USER_PERMISSIONS_WORKSPACE_MODELS_IMPORT,
        'models_export': USER_PERMISSIONS_WORKSPACE_MODELS_EXPORT,
        'prompts_import': USER_PERMISSIONS_WORKSPACE_PROMPTS_IMPORT,
        'prompts_export': USER_PERMISSIONS_WORKSPACE_PROMPTS_EXPORT,
        'tools_import': USER_PERMISSIONS_WORKSPACE_TOOLS_IMPORT,
        'tools_export': USER_PERMISSIONS_WORKSPACE_TOOLS_EXPORT,
    },
    'sharing': {
        'models': USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_SHARING,
        'public_models': USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_PUBLIC_SHARING,
        'knowledge': USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ALLOW_SHARING,
        'public_knowledge': USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ALLOW_PUBLIC_SHARING,
        'prompts': USER_PERMISSIONS_WORKSPACE_PROMPTS_ALLOW_SHARING,
        'public_prompts': USER_PERMISSIONS_WORKSPACE_PROMPTS_ALLOW_PUBLIC_SHARING,
        'tools': USER_PERMISSIONS_WORKSPACE_TOOLS_ALLOW_SHARING,
        'public_tools': USER_PERMISSIONS_WORKSPACE_TOOLS_ALLOW_PUBLIC_SHARING,
        'skills': USER_PERMISSIONS_WORKSPACE_SKILLS_ALLOW_SHARING,
        'public_skills': USER_PERMISSIONS_WORKSPACE_SKILLS_ALLOW_PUBLIC_SHARING,
        'notes': USER_PERMISSIONS_NOTES_ALLOW_SHARING,
        'public_notes': USER_PERMISSIONS_NOTES_ALLOW_PUBLIC_SHARING,
        'public_chats': USER_PERMISSIONS_CHAT_ALLOW_PUBLIC_SHARING,
        'public_calendars': USER_PERMISSIONS_CALENDAR_ALLOW_PUBLIC_SHARING,
    },
    'access_grants': {
        'allow_users': USER_PERMISSIONS_ACCESS_GRANTS_ALLOW_USERS,
    },
    'chat': {
        'controls': USER_PERMISSIONS_CHAT_CONTROLS,
        'valves': USER_PERMISSIONS_CHAT_VALVES,
        'system_prompt': USER_PERMISSIONS_CHAT_SYSTEM_PROMPT,
        'params': USER_PERMISSIONS_CHAT_PARAMS,
        'file_upload': USER_PERMISSIONS_CHAT_FILE_UPLOAD,
        'web_upload': USER_PERMISSIONS_CHAT_WEB_UPLOAD,
        'delete': USER_PERMISSIONS_CHAT_DELETE,
        'delete_message': USER_PERMISSIONS_CHAT_DELETE_MESSAGE,
        'continue_response': USER_PERMISSIONS_CHAT_CONTINUE_RESPONSE,
        'regenerate_response': USER_PERMISSIONS_CHAT_REGENERATE_RESPONSE,
        'rate_response': USER_PERMISSIONS_CHAT_RATE_RESPONSE,
        'edit': USER_PERMISSIONS_CHAT_EDIT,
        'share': USER_PERMISSIONS_CHAT_SHARE,
        'export': USER_PERMISSIONS_CHAT_EXPORT,
        'stt': USER_PERMISSIONS_CHAT_STT,
        'tts': USER_PERMISSIONS_CHAT_TTS,
        'call': USER_PERMISSIONS_CHAT_CALL,
        'multiple_models': USER_PERMISSIONS_CHAT_MULTIPLE_MODELS,
        'temporary': USER_PERMISSIONS_CHAT_TEMPORARY,
        'temporary_enforced': USER_PERMISSIONS_CHAT_TEMPORARY_ENFORCED,
    },
    'features': {
        # General features
        'api_keys': USER_PERMISSIONS_FEATURES_API_KEYS,
        'notes': USER_PERMISSIONS_FEATURES_NOTES,
        'folders': USER_PERMISSIONS_FEATURES_FOLDERS,
        'channels': USER_PERMISSIONS_FEATURES_CHANNELS,
        'direct_tool_servers': USER_PERMISSIONS_FEATURES_DIRECT_TOOL_SERVERS,
        # Chat features
        'web_search': USER_PERMISSIONS_FEATURES_WEB_SEARCH,
        'image_generation': USER_PERMISSIONS_FEATURES_IMAGE_GENERATION,
        'code_interpreter': USER_PERMISSIONS_FEATURES_CODE_INTERPRETER,
        'memories': USER_PERMISSIONS_FEATURES_MEMORIES,
        'automations': USER_PERMISSIONS_FEATURES_AUTOMATIONS,
        'calendar': USER_PERMISSIONS_FEATURES_CALENDAR,
    },
    'settings': {
        'interface': USER_PERMISSIONS_SETTINGS_INTERFACE,
    },
}

USER_PERMISSIONS = ConfigVar(
    'USER_PERMISSIONS',
    'user.permissions',
    DEFAULT_USER_PERMISSIONS,
)

ENABLE_FOLDERS = ConfigVar(
    'ENABLE_FOLDERS',
    'folders.enable',
    os.getenv('ENABLE_FOLDERS', 'True').lower() == 'true',
)

FOLDER_MAX_FILE_COUNT = ConfigVar(
    'FOLDER_MAX_FILE_COUNT',
    'folders.max_file_count',
    os.getenv('FOLDER_MAX_FILE_COUNT', ''),
)

ENABLE_CHANNELS = ConfigVar(
    'ENABLE_CHANNELS',
    'channels.enable',
    os.getenv('ENABLE_CHANNELS', 'False').lower() == 'true',
)

ENABLE_CALENDAR = ConfigVar(
    'ENABLE_CALENDAR',
    'calendar.enable',
    os.getenv('ENABLE_CALENDAR', 'True').lower() == 'true',
)

ENABLE_AUTOMATIONS = ConfigVar(
    'ENABLE_AUTOMATIONS',
    'automations.enable',
    os.getenv('ENABLE_AUTOMATIONS', 'True').lower() == 'true',
)

AUTOMATION_MAX_COUNT = ConfigVar(
    'AUTOMATION_MAX_COUNT',
    'automations.max_count',
    os.getenv('AUTOMATION_MAX_COUNT', ''),
)

AUTOMATION_MIN_INTERVAL = ConfigVar(
    'AUTOMATION_MIN_INTERVAL',
    'automations.min_interval',
    os.getenv('AUTOMATION_MIN_INTERVAL', ''),
)

ENABLE_NOTES = ConfigVar(
    'ENABLE_NOTES',
    'notes.enable',
    os.getenv('ENABLE_NOTES', 'True').lower() == 'true',
)

ENABLE_USER_STATUS = ConfigVar(
    'ENABLE_USER_STATUS',
    'users.enable_status',
    os.getenv('ENABLE_USER_STATUS', 'True').lower() == 'true',
)

ENABLE_EVALUATION_ARENA_MODELS = ConfigVar(
    'ENABLE_EVALUATION_ARENA_MODELS',
    'evaluation.arena.enable',
    os.getenv('ENABLE_EVALUATION_ARENA_MODELS', 'True').lower() == 'true',
)
EVALUATION_ARENA_MODELS = ConfigVar(
    'EVALUATION_ARENA_MODELS',
    'evaluation.arena.models',
    [],
)

DEFAULT_ARENA_MODEL = {
    'id': 'arena-model',
    'name': 'Arena Model',
    'meta': {
        'profile_image_url': '/favicon.png',
        'description': 'Submit your questions to anonymous AI chatbots and vote on the best response.',
        'model_ids': None,
    },
}

WEBHOOK_URL = ConfigVar('WEBHOOK_URL', 'webhook_url', os.getenv('WEBHOOK_URL', ''))

ENABLE_ADMIN_EXPORT = os.getenv('ENABLE_ADMIN_EXPORT', 'True').lower() == 'true'

ENABLE_ADMIN_WORKSPACE_CONTENT_ACCESS = os.getenv('ENABLE_ADMIN_WORKSPACE_CONTENT_ACCESS', 'True').lower() == 'true'

BYPASS_ADMIN_ACCESS_CONTROL = (
    os.getenv(
        'BYPASS_ADMIN_ACCESS_CONTROL',
        os.getenv('ENABLE_ADMIN_WORKSPACE_CONTENT_ACCESS', 'True'),
    ).lower()
    == 'true'
)

ENABLE_ADMIN_CHAT_ACCESS = os.getenv('ENABLE_ADMIN_CHAT_ACCESS', 'True').lower() == 'true'

ENABLE_ADMIN_ANALYTICS = os.getenv('ENABLE_ADMIN_ANALYTICS', 'True').lower() == 'true'

ENABLE_COMMUNITY_SHARING = ConfigVar(
    'ENABLE_COMMUNITY_SHARING',
    'ui.enable_community_sharing',
    os.getenv('ENABLE_COMMUNITY_SHARING', 'True').lower() == 'true',
)

ENABLE_MESSAGE_RATING = ConfigVar(
    'ENABLE_MESSAGE_RATING',
    'ui.enable_message_rating',
    os.getenv('ENABLE_MESSAGE_RATING', 'True').lower() == 'true',
)

ENABLE_USER_WEBHOOKS = ConfigVar(
    'ENABLE_USER_WEBHOOKS',
    'ui.enable_user_webhooks',
    os.getenv('ENABLE_USER_WEBHOOKS', 'False').lower() == 'true',
)

# FastAPI / AnyIO settings
THREAD_POOL_SIZE = os.getenv('THREAD_POOL_SIZE', None)

if THREAD_POOL_SIZE is not None and isinstance(THREAD_POOL_SIZE, str):
    try:
        THREAD_POOL_SIZE = int(THREAD_POOL_SIZE)
    except ValueError:
        log.warning(f'THREAD_POOL_SIZE is not a valid integer: {THREAD_POOL_SIZE}. Defaulting to None.')
        THREAD_POOL_SIZE = None


def validate_cors_origin(origin):
    parsed_url = urlparse(origin)

    # Check if the scheme is either http or https, or a custom scheme
    schemes = ['http', 'https'] + CORS_ALLOW_CUSTOM_SCHEME
    if parsed_url.scheme not in schemes:
        raise ValueError(
            f"Invalid scheme in CORS_ALLOW_ORIGIN: '{origin}'. Only 'http' and 'https' and CORS_ALLOW_CUSTOM_SCHEME are allowed."
        )

    # Ensure that the netloc (domain + port) is present, indicating it's a valid URL
    if not parsed_url.netloc:
        raise ValueError(f"Invalid URL structure in CORS_ALLOW_ORIGIN: '{origin}'.")


# For production, you should only need one host as
# fastapi serves the svelte-kit built frontend and backend from the same host and port.
# To test CORS_ALLOW_ORIGIN locally, you can set something like
# CORS_ALLOW_ORIGIN=http://localhost:5173;http://localhost:8080
# in your .env file depending on your frontend port, 5173 in this case.
CORS_ALLOW_ORIGIN = os.getenv('CORS_ALLOW_ORIGIN', '*').split(';')

# Allows custom URL schemes (e.g., app://) to be used as origins for CORS.
# Useful for local development or desktop clients with schemes like app:// or other custom protocols.
# Provide a semicolon-separated list of allowed schemes in the environment variable CORS_ALLOW_CUSTOM_SCHEMES.
CORS_ALLOW_CUSTOM_SCHEME = os.getenv('CORS_ALLOW_CUSTOM_SCHEME', '').split(';')

if CORS_ALLOW_ORIGIN == ['*']:
    log.warning("\n\nWARNING: CORS_ALLOW_ORIGIN IS SET TO '*' - NOT RECOMMENDED FOR PRODUCTION DEPLOYMENTS.\n")
else:
    # You have to pick between a single wildcard or a list of origins.
    # Doing both will result in CORS errors in the browser.
    for origin in CORS_ALLOW_ORIGIN:
        validate_cors_origin(origin)


class BannerModel(BaseModel):
    id: str
    type: str
    title: str | None = None
    content: str
    dismissible: bool
    timestamp: int


try:
    banners = json.loads(os.getenv('WEBUI_BANNERS', '[]'))
    banners = [BannerModel(**banner) for banner in banners]
except Exception as e:
    log.exception(f'Error loading WEBUI_BANNERS: {e}')
    banners = []

WEBUI_BANNERS = ConfigVar('WEBUI_BANNERS', 'ui.banners', banners)


SHOW_ADMIN_DETAILS = ConfigVar(
    'SHOW_ADMIN_DETAILS',
    'auth.admin.show',
    os.getenv('SHOW_ADMIN_DETAILS', 'true').lower() == 'true',
)

ADMIN_EMAIL = ConfigVar(
    'ADMIN_EMAIL',
    'auth.admin.email',
    os.getenv('ADMIN_EMAIL', None),
)


####################################
# TASKS
####################################


TASK_MODEL = ConfigVar(
    'TASK_MODEL',
    'task.model.default',
    os.getenv('TASK_MODEL', ''),
)

TASK_MODEL_EXTERNAL = ConfigVar(
    'TASK_MODEL_EXTERNAL',
    'task.model.external',
    os.getenv('TASK_MODEL_EXTERNAL', ''),
)

TITLE_GENERATION_PROMPT_TEMPLATE = ConfigVar(
    'TITLE_GENERATION_PROMPT_TEMPLATE',
    'task.title.prompt_template',
    os.getenv('TITLE_GENERATION_PROMPT_TEMPLATE', ''),
)

DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE = """### Task:
Generate a concise, 3-5 word title with an emoji summarizing the chat history.
### Guidelines:
- The title should clearly represent the main theme or subject of the conversation.
- Use emojis that enhance understanding of the topic, but avoid quotation marks or special formatting.
- Write the title in the chat's primary language; default to English if multilingual.
- Prioritize accuracy over excessive creativity; keep it clear and simple.
- Your entire response must consist solely of the JSON object, without any introductory or concluding text.
- The output must be a single, raw JSON object, without any markdown code fences or other encapsulating text.
- Ensure no conversational text, affirmations, or explanations precede or follow the raw JSON output, as this will cause direct parsing failure.
### Output:
JSON format: { "title": "your concise title here" }
### Examples:
- { "title": "📉 Stock Market Trends" },
- { "title": "🍪 Perfect Chocolate Chip Recipe" },
- { "title": "Evolution of Music Streaming" },
- { "title": "Remote Work Productivity Tips" },
- { "title": "Artificial Intelligence in Healthcare" },
- { "title": "🎮 Video Game Development Insights" }
### Chat History:
<chat_history>
{{MESSAGES:END:2}}
</chat_history>"""

TAGS_GENERATION_PROMPT_TEMPLATE = ConfigVar(
    'TAGS_GENERATION_PROMPT_TEMPLATE',
    'task.tags.prompt_template',
    os.getenv('TAGS_GENERATION_PROMPT_TEMPLATE', ''),
)

DEFAULT_TAGS_GENERATION_PROMPT_TEMPLATE = """### Task:
Generate 1-3 broad tags categorizing the main themes of the chat history, along with 1-3 more specific subtopic tags.

### Guidelines:
- Start with high-level domains (e.g. Science, Technology, Philosophy, Arts, Politics, Business, Health, Sports, Entertainment, Education)
- Consider including relevant subfields/subdomains if they are strongly represented throughout the conversation
- If content is too short (less than 3 messages) or too diverse, use only ["General"]
- Use the chat's primary language; default to English if multilingual
- Prioritize accuracy over specificity

### Output:
JSON format: { "tags": ["tag1", "tag2", "tag3"] }

### Chat History:
<chat_history>
{{MESSAGES:END:6}}
</chat_history>"""

IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE = ConfigVar(
    'IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE',
    'task.image.prompt_template',
    os.getenv('IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE', ''),
)

DEFAULT_IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE = """### Task:
Generate a detailed prompt for am image generation task based on the given language and context. Describe the image as if you were explaining it to someone who cannot see it. Include relevant details, colors, shapes, and any other important elements.

### Guidelines:
- Be descriptive and detailed, focusing on the most important aspects of the image.
- Avoid making assumptions or adding information not present in the image.
- Use the chat's primary language; default to English if multilingual.
- If the image is too complex, focus on the most prominent elements.

### Output:
Strictly return in JSON format:
{
    "prompt": "Your detailed description here."
}

### Chat History:
<chat_history>
{{MESSAGES:END:6}}
</chat_history>"""


FOLLOW_UP_GENERATION_PROMPT_TEMPLATE = ConfigVar(
    'FOLLOW_UP_GENERATION_PROMPT_TEMPLATE',
    'task.follow_up.prompt_template',
    os.getenv('FOLLOW_UP_GENERATION_PROMPT_TEMPLATE', ''),
)

DEFAULT_FOLLOW_UP_GENERATION_PROMPT_TEMPLATE = """### Task:
Suggest 3-5 relevant follow-up questions or prompts that the user might naturally ask next in this conversation as a **user**, based on the chat history, to help continue or deepen the discussion.
### Guidelines:
- Write all follow-up questions from the user’s point of view, directed to the assistant.
- Make questions concise, clear, and directly related to the discussed topic(s).
- Only suggest follow-ups that make sense given the chat content and do not repeat what was already covered.
- If the conversation is very short or not specific, suggest more general (but relevant) follow-ups the user might ask.
- Use the conversation's primary language; default to English if multilingual.
- Response must be a JSON object with a "follow_ups" key containing an array of strings, no extra text or formatting.
### Output:
JSON format: { "follow_ups": ["Question 1?", "Question 2?", "Question 3?"] }
### Chat History:
<chat_history>
{{MESSAGES:END:6}}
</chat_history>"""

ENABLE_FOLLOW_UP_GENERATION = ConfigVar(
    'ENABLE_FOLLOW_UP_GENERATION',
    'task.follow_up.enable',
    os.getenv('ENABLE_FOLLOW_UP_GENERATION', 'True').lower() == 'true',
)

ENABLE_TAGS_GENERATION = ConfigVar(
    'ENABLE_TAGS_GENERATION',
    'task.tags.enable',
    os.getenv('ENABLE_TAGS_GENERATION', 'True').lower() == 'true',
)

ENABLE_TITLE_GENERATION = ConfigVar(
    'ENABLE_TITLE_GENERATION',
    'task.title.enable',
    os.getenv('ENABLE_TITLE_GENERATION', 'True').lower() == 'true',
)


ENABLE_SEARCH_QUERY_GENERATION = ConfigVar(
    'ENABLE_SEARCH_QUERY_GENERATION',
    'task.query.search.enable',
    os.getenv('ENABLE_SEARCH_QUERY_GENERATION', 'True').lower() == 'true',
)

ENABLE_RETRIEVAL_QUERY_GENERATION = ConfigVar(
    'ENABLE_RETRIEVAL_QUERY_GENERATION',
    'task.query.retrieval.enable',
    os.getenv('ENABLE_RETRIEVAL_QUERY_GENERATION', 'True').lower() == 'true',
)


QUERY_GENERATION_PROMPT_TEMPLATE = ConfigVar(
    'QUERY_GENERATION_PROMPT_TEMPLATE',
    'task.query.prompt_template',
    os.getenv('QUERY_GENERATION_PROMPT_TEMPLATE', ''),
)

DEFAULT_QUERY_GENERATION_PROMPT_TEMPLATE = """### Task:
Analyze the chat history to determine the necessity of generating search queries, in the given language. By default, **prioritize generating 1-3 broad and relevant search queries** unless it is absolutely certain that no additional information is required. The aim is to retrieve comprehensive, updated, and valuable information even with minimal uncertainty. If no search is unequivocally needed, return an empty list.

### Guidelines:
- Respond **EXCLUSIVELY** with a JSON object. Any form of extra commentary, explanation, or additional text is strictly prohibited.
- When generating search queries, respond in the format: { "queries": ["query1", "query2"] }, ensuring each query is distinct, concise, and relevant to the topic.
- If and only if it is entirely certain that no useful results can be retrieved by a search, return: { "queries": [] }.
- Err on the side of suggesting search queries if there is **any chance** they might provide useful or updated information.
- Be concise and focused on composing high-quality search queries, avoiding unnecessary elaboration, commentary, or assumptions.
- Today's date is: {{CURRENT_DATE}}.
- Always prioritize providing actionable and broad queries that maximize informational coverage.

### Output:
Strictly return in JSON format: 
{
  "queries": ["query1", "query2"]
}

### Chat History:
<chat_history>
{{MESSAGES:END:6}}
</chat_history>
"""

ENABLE_AUTOCOMPLETE_GENERATION = ConfigVar(
    'ENABLE_AUTOCOMPLETE_GENERATION',
    'task.autocomplete.enable',
    os.getenv('ENABLE_AUTOCOMPLETE_GENERATION', 'False').lower() == 'true',
)

AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH = ConfigVar(
    'AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH',
    'task.autocomplete.input_max_length',
    int(os.getenv('AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH', '-1')),
)

AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE = ConfigVar(
    'AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE',
    'task.autocomplete.prompt_template',
    os.getenv('AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE', ''),
)


DEFAULT_AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE = """### Task:
You are an autocompletion system. Continue the text in `<text>` based on the **completion type** in `<type>` and the given language.  

### **Instructions**:
1. Analyze `<text>` for context and meaning.  
2. Use `<type>` to guide your output:  
   - **General**: Provide a natural, concise continuation.  
   - **Search Query**: Complete as if generating a realistic search query.  
3. Start as if you are directly continuing `<text>`. Do **not** repeat, paraphrase, or respond as a model. Simply complete the text.  
4. Ensure the continuation:
   - Flows naturally from `<text>`.  
   - Avoids repetition, overexplaining, or unrelated ideas.  
5. If unsure, return: `{ "text": "" }`.  

### **Output Rules**:
- Respond only in JSON format: `{ "text": "<your_completion>" }`.

### **Examples**:
#### Example 1:  
Input:  
<type>General</type>  
<text>The sun was setting over the horizon, painting the sky</text>  
Output:  
{ "text": "with vibrant shades of orange and pink." }

#### Example 2:  
Input:  
<type>Search Query</type>  
<text>Top-rated restaurants in</text>  
Output:  
{ "text": "New York City for Italian cuisine." }  

---
### Context:
<chat_history>
{{MESSAGES:END:6}}
</chat_history>
<type>{{TYPE}}</type>  
<text>{{PROMPT}}</text>  
#### Output:
"""


VOICE_MODE_PROMPT_TEMPLATE = ConfigVar(
    'VOICE_MODE_PROMPT_TEMPLATE',
    'task.voice.prompt_template',
    os.getenv('VOICE_MODE_PROMPT_TEMPLATE', ''),
)

ENABLE_VOICE_MODE_PROMPT = ConfigVar(
    'ENABLE_VOICE_MODE_PROMPT',
    'task.voice.prompt.enable',
    os.getenv('ENABLE_VOICE_MODE_PROMPT', 'True').lower() == 'true',
)

DEFAULT_VOICE_MODE_PROMPT_TEMPLATE = """You are a friendly, concise voice assistant.

Everything you say will be spoken aloud.
Keep responses short, clear, and natural.

STYLE:
- Use simple words and short sentences.
- Sound warm and conversational.
- Avoid long explanations, lists, or complex phrasing.

BEHAVIOR:
- Give the quickest helpful answer first.
- Offer extra detail only if needed.
- Ask for clarification only when necessary.

VOICE OPTIMIZATION:
- Break information into small, easy-to-hear chunks.
- Avoid dense wording or anything that sounds like reading text.

ERROR HANDLING:
- If unsure, say so briefly and offer options.
- If something is unsafe or impossible, decline kindly and suggest a safe alternative.

Stay consistent, helpful, and easy to listen to."""

TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = ConfigVar(
    'TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE',
    'task.tools.prompt_template',
    os.getenv('TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE', ''),
)


DEFAULT_TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = """Available Tools: {{TOOLS}}

Your task is to choose and return the correct tool(s) from the list of available tools based on the query. Follow these guidelines:

- Return only the JSON object, without any additional text or explanation.

- If no tools match the query, return an empty array: 
   {
     "tool_calls": []
   }

- If one or more tools match the query, construct a JSON response containing a "tool_calls" array with objects that include:
   - "name": The tool's name.
   - "parameters": A dictionary of required parameters and their corresponding values.

The format for the JSON response is strictly:
{
  "tool_calls": [
    {"name": "toolName1", "parameters": {"key1": "value1"}},
    {"name": "toolName2", "parameters": {"key2": "value2"}}
  ]
}"""


DEFAULT_EMOJI_GENERATION_PROMPT_TEMPLATE = """Your task is to reflect the speaker's likely facial expression through a fitting emoji. Interpret emotions from the message and reflect their facial expression using fitting, diverse emojis (e.g., 😊, 😢, 😡, 😱).

Message: ```{{prompt}}```"""

DEFAULT_MOA_GENERATION_PROMPT_TEMPLATE = """You have been provided with a set of responses from various models to the latest user query: "{{prompt}}"

Your task is to synthesize these responses into a single, high-quality response. It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect. Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction. Ensure your response is well-structured, coherent, and adheres to the highest standards of accuracy and reliability.

Responses from models: {{responses}}"""


####################################
# Auth
####################################

ENABLE_API_KEYS = ConfigVar(
    'ENABLE_API_KEYS',
    'auth.enable_api_keys',
    os.getenv('ENABLE_API_KEYS', 'False').lower() == 'true',
)

ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS = ConfigVar(
    'ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS',
    'auth.api_key.endpoint_restrictions',
    os.getenv(
        'ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS',
        os.getenv('ENABLE_API_KEY_ENDPOINT_RESTRICTIONS', 'False'),
    ).lower()
    == 'true',
)

API_KEYS_ALLOWED_ENDPOINTS = ConfigVar(
    'API_KEYS_ALLOWED_ENDPOINTS',
    'auth.api_key.allowed_endpoints',
    os.getenv('API_KEYS_ALLOWED_ENDPOINTS', os.getenv('API_KEY_ALLOWED_ENDPOINTS', '')),
)

JWT_EXPIRES_IN = ConfigVar('JWT_EXPIRES_IN', 'auth.jwt_expiry', os.getenv('JWT_EXPIRES_IN', '4w'))

if JWT_EXPIRES_IN.value == '-1':
    log.warning(
        "⚠️  SECURITY WARNING: JWT_EXPIRES_IN is set to '-1'\n"
        '    See: https://docs.openwebui.com/reference/env-configuration\n'
    )

####################################
# OAuth config
####################################

ENABLE_OAUTH_SIGNUP = ConfigVar(
    'ENABLE_OAUTH_SIGNUP',
    'oauth.enable_signup',
    os.getenv('ENABLE_OAUTH_SIGNUP', 'False').lower() == 'true',
)

OAUTH_REFRESH_TOKEN_INCLUDE_SCOPE = ConfigVar(
    'OAUTH_REFRESH_TOKEN_INCLUDE_SCOPE',
    'oauth.refresh_token_include_scope',
    os.getenv('OAUTH_REFRESH_TOKEN_INCLUDE_SCOPE', 'False').lower() == 'true',
)


OAUTH_MERGE_ACCOUNTS_BY_EMAIL = ConfigVar(
    'OAUTH_MERGE_ACCOUNTS_BY_EMAIL',
    'oauth.merge_accounts_by_email',
    os.getenv('OAUTH_MERGE_ACCOUNTS_BY_EMAIL', 'False').lower() == 'true',
)

OAUTH_PROVIDERS = {}

GOOGLE_CLIENT_ID = ConfigVar(
    'GOOGLE_CLIENT_ID',
    'oauth.google.client_id',
    os.getenv('GOOGLE_CLIENT_ID', ''),
)

GOOGLE_CLIENT_SECRET = ConfigVar(
    'GOOGLE_CLIENT_SECRET',
    'oauth.google.client_secret',
    os.getenv('GOOGLE_CLIENT_SECRET', ''),
)


GOOGLE_OAUTH_SCOPE = ConfigVar(
    'GOOGLE_OAUTH_SCOPE',
    'oauth.google.scope',
    os.getenv('GOOGLE_OAUTH_SCOPE', 'openid email profile'),
)

GOOGLE_REDIRECT_URI = ConfigVar(
    'GOOGLE_REDIRECT_URI',
    'oauth.google.redirect_uri',
    os.getenv('GOOGLE_REDIRECT_URI', ''),
)

GOOGLE_OAUTH_AUTHORIZE_PARAMS = {}
_google_oauth_authorize_params = os.getenv('GOOGLE_OAUTH_AUTHORIZE_PARAMS', '')
if _google_oauth_authorize_params:
    try:
        _parsed = json.loads(_google_oauth_authorize_params)
        if isinstance(_parsed, dict):
            GOOGLE_OAUTH_AUTHORIZE_PARAMS = _parsed
        else:
            log.warning('GOOGLE_OAUTH_AUTHORIZE_PARAMS must be a JSON object, ignoring')
    except (json.JSONDecodeError, TypeError):
        log.warning('GOOGLE_OAUTH_AUTHORIZE_PARAMS is not valid JSON, ignoring')

MICROSOFT_CLIENT_ID = ConfigVar(
    'MICROSOFT_CLIENT_ID',
    'oauth.microsoft.client_id',
    os.getenv('MICROSOFT_CLIENT_ID', ''),
)

MICROSOFT_CLIENT_SECRET = ConfigVar(
    'MICROSOFT_CLIENT_SECRET',
    'oauth.microsoft.client_secret',
    os.getenv('MICROSOFT_CLIENT_SECRET', ''),
)

MICROSOFT_CLIENT_TENANT_ID = ConfigVar(
    'MICROSOFT_CLIENT_TENANT_ID',
    'oauth.microsoft.tenant_id',
    os.getenv('MICROSOFT_CLIENT_TENANT_ID', ''),
)

MICROSOFT_CLIENT_LOGIN_BASE_URL = ConfigVar(
    'MICROSOFT_CLIENT_LOGIN_BASE_URL',
    'oauth.microsoft.login_base_url',
    os.getenv('MICROSOFT_CLIENT_LOGIN_BASE_URL', 'https://login.microsoftonline.com'),
)

MICROSOFT_CLIENT_PICTURE_URL = ConfigVar(
    'MICROSOFT_CLIENT_PICTURE_URL',
    'oauth.microsoft.picture_url',
    os.getenv(
        'MICROSOFT_CLIENT_PICTURE_URL',
        'https://graph.microsoft.com/v1.0/me/photo/$value',
    ),
)


MICROSOFT_OAUTH_SCOPE = ConfigVar(
    'MICROSOFT_OAUTH_SCOPE',
    'oauth.microsoft.scope',
    os.getenv('MICROSOFT_OAUTH_SCOPE', 'openid email profile'),
)

MICROSOFT_REDIRECT_URI = ConfigVar(
    'MICROSOFT_REDIRECT_URI',
    'oauth.microsoft.redirect_uri',
    os.getenv('MICROSOFT_REDIRECT_URI', ''),
)

GITHUB_CLIENT_ID = ConfigVar(
    'GITHUB_CLIENT_ID',
    'oauth.github.client_id',
    os.getenv('GITHUB_CLIENT_ID', ''),
)

GITHUB_CLIENT_SECRET = ConfigVar(
    'GITHUB_CLIENT_SECRET',
    'oauth.github.client_secret',
    os.getenv('GITHUB_CLIENT_SECRET', ''),
)

GITHUB_CLIENT_SCOPE = ConfigVar(
    'GITHUB_CLIENT_SCOPE',
    'oauth.github.scope',
    os.getenv('GITHUB_CLIENT_SCOPE', 'user:email'),
)

GITHUB_CLIENT_REDIRECT_URI = ConfigVar(
    'GITHUB_CLIENT_REDIRECT_URI',
    'oauth.github.redirect_uri',
    os.getenv('GITHUB_CLIENT_REDIRECT_URI', ''),
)

OAUTH_CLIENT_ID = ConfigVar(
    'OAUTH_CLIENT_ID',
    'oauth.oidc.client_id',
    os.getenv('OAUTH_CLIENT_ID', ''),
)

OAUTH_CLIENT_SECRET = ConfigVar(
    'OAUTH_CLIENT_SECRET',
    'oauth.oidc.client_secret',
    os.getenv('OAUTH_CLIENT_SECRET', ''),
)

OPENID_PROVIDER_URL = ConfigVar(
    'OPENID_PROVIDER_URL',
    'oauth.oidc.provider_url',
    os.getenv('OPENID_PROVIDER_URL', ''),
)

OPENID_END_SESSION_ENDPOINT = ConfigVar(
    'OPENID_END_SESSION_ENDPOINT',
    'oauth.oidc.end_session_endpoint',
    os.getenv('OPENID_END_SESSION_ENDPOINT', ''),
)

OPENID_REDIRECT_URI = ConfigVar(
    'OPENID_REDIRECT_URI',
    'oauth.oidc.redirect_uri',
    os.getenv('OPENID_REDIRECT_URI', ''),
)

OAUTH_SCOPES = ConfigVar(
    'OAUTH_SCOPES',
    'oauth.oidc.scopes',
    os.getenv('OAUTH_SCOPES', 'openid email profile'),
)

OAUTH_TIMEOUT = ConfigVar(
    'OAUTH_TIMEOUT',
    'oauth.oidc.oauth_timeout',
    os.getenv('OAUTH_TIMEOUT', ''),
)

OAUTH_TOKEN_ENDPOINT_AUTH_METHOD = ConfigVar(
    'OAUTH_TOKEN_ENDPOINT_AUTH_METHOD',
    'oauth.oidc.token_endpoint_auth_method',
    os.getenv('OAUTH_TOKEN_ENDPOINT_AUTH_METHOD', None),
)

OAUTH_CODE_CHALLENGE_METHOD = ConfigVar(
    'OAUTH_CODE_CHALLENGE_METHOD',
    'oauth.oidc.code_challenge_method',
    os.getenv('OAUTH_CODE_CHALLENGE_METHOD', None),
)

OAUTH_PROVIDER_NAME = ConfigVar(
    'OAUTH_PROVIDER_NAME',
    'oauth.oidc.provider_name',
    os.getenv('OAUTH_PROVIDER_NAME', 'SSO'),
)

OAUTH_SUB_CLAIM = ConfigVar(
    'OAUTH_SUB_CLAIM',
    'oauth.oidc.sub_claim',
    os.getenv('OAUTH_SUB_CLAIM', None),
)

OAUTH_USERNAME_CLAIM = ConfigVar(
    'OAUTH_USERNAME_CLAIM',
    'oauth.oidc.username_claim',
    os.getenv('OAUTH_USERNAME_CLAIM', 'name'),
)


OAUTH_PICTURE_CLAIM = ConfigVar(
    'OAUTH_PICTURE_CLAIM',
    'oauth.oidc.avatar_claim',
    os.getenv('OAUTH_PICTURE_CLAIM', 'picture'),
)

OAUTH_EMAIL_CLAIM = ConfigVar(
    'OAUTH_EMAIL_CLAIM',
    'oauth.oidc.email_claim',
    os.getenv('OAUTH_EMAIL_CLAIM', 'email'),
)

OAUTH_GROUPS_CLAIM = ConfigVar(
    'OAUTH_GROUPS_CLAIM',
    'oauth.oidc.group_claim',
    os.getenv('OAUTH_GROUPS_CLAIM', os.getenv('OAUTH_GROUP_CLAIM', 'groups')),
)

FEISHU_CLIENT_ID = ConfigVar(
    'FEISHU_CLIENT_ID',
    'oauth.feishu.client_id',
    os.getenv('FEISHU_CLIENT_ID', ''),
)

FEISHU_CLIENT_SECRET = ConfigVar(
    'FEISHU_CLIENT_SECRET',
    'oauth.feishu.client_secret',
    os.getenv('FEISHU_CLIENT_SECRET', ''),
)

FEISHU_OAUTH_SCOPE = ConfigVar(
    'FEISHU_OAUTH_SCOPE',
    'oauth.feishu.scope',
    os.getenv('FEISHU_OAUTH_SCOPE', 'contact:user.base:readonly'),
)

FEISHU_REDIRECT_URI = ConfigVar(
    'FEISHU_REDIRECT_URI',
    'oauth.feishu.redirect_uri',
    os.getenv('FEISHU_REDIRECT_URI', ''),
)

ENABLE_OAUTH_ROLE_MANAGEMENT = ConfigVar(
    'ENABLE_OAUTH_ROLE_MANAGEMENT',
    'oauth.enable_role_mapping',
    os.getenv('ENABLE_OAUTH_ROLE_MANAGEMENT', 'False').lower() == 'true',
)

ENABLE_OAUTH_GROUP_MANAGEMENT = ConfigVar(
    'ENABLE_OAUTH_GROUP_MANAGEMENT',
    'oauth.enable_group_mapping',
    os.getenv('ENABLE_OAUTH_GROUP_MANAGEMENT', 'False').lower() == 'true',
)

ENABLE_OAUTH_GROUP_CREATION = ConfigVar(
    'ENABLE_OAUTH_GROUP_CREATION',
    'oauth.enable_group_creation',
    os.getenv('ENABLE_OAUTH_GROUP_CREATION', 'False').lower() == 'true',
)


oauth_group_default_share = os.getenv('OAUTH_GROUP_DEFAULT_SHARE', 'true').strip().lower()
OAUTH_GROUP_DEFAULT_SHARE = ConfigVar(
    'OAUTH_GROUP_DEFAULT_SHARE',
    'oauth.group_default_share',
    ('members' if oauth_group_default_share == 'members' else oauth_group_default_share == 'true'),
)


OAUTH_BLOCKED_GROUPS = ConfigVar(
    'OAUTH_BLOCKED_GROUPS',
    'oauth.blocked_groups',
    os.getenv('OAUTH_BLOCKED_GROUPS', '[]'),
)

OAUTH_GROUPS_SEPARATOR = os.getenv('OAUTH_GROUPS_SEPARATOR', ';')

OAUTH_ROLES_CLAIM = ConfigVar(
    'OAUTH_ROLES_CLAIM',
    'oauth.roles_claim',
    os.getenv('OAUTH_ROLES_CLAIM', 'roles'),
)

OAUTH_ROLES_SEPARATOR = os.getenv('OAUTH_ROLES_SEPARATOR', ',')

OAUTH_ALLOWED_ROLES = ConfigVar(
    'OAUTH_ALLOWED_ROLES',
    'oauth.allowed_roles',
    [
        role.strip()
        for role in os.getenv('OAUTH_ALLOWED_ROLES', f'user{OAUTH_ROLES_SEPARATOR}admin').split(OAUTH_ROLES_SEPARATOR)
        if role
    ],
)

OAUTH_ADMIN_ROLES = ConfigVar(
    'OAUTH_ADMIN_ROLES',
    'oauth.admin_roles',
    [role.strip() for role in os.getenv('OAUTH_ADMIN_ROLES', 'admin').split(OAUTH_ROLES_SEPARATOR) if role],
)

OAUTH_ALLOWED_DOMAINS = ConfigVar(
    'OAUTH_ALLOWED_DOMAINS',
    'oauth.allowed_domains',
    [domain.strip() for domain in os.getenv('OAUTH_ALLOWED_DOMAINS', '*').split(',')],
)

OAUTH_UPDATE_PICTURE_ON_LOGIN = ConfigVar(
    'OAUTH_UPDATE_PICTURE_ON_LOGIN',
    'oauth.update_picture_on_login',
    os.getenv('OAUTH_UPDATE_PICTURE_ON_LOGIN', 'False').lower() == 'true',
)

OAUTH_UPDATE_NAME_ON_LOGIN = ConfigVar(
    'OAUTH_UPDATE_NAME_ON_LOGIN',
    'oauth.update_name_on_login',
    os.getenv('OAUTH_UPDATE_NAME_ON_LOGIN', 'False').lower() == 'true',
)

OAUTH_UPDATE_EMAIL_ON_LOGIN = ConfigVar(
    'OAUTH_UPDATE_EMAIL_ON_LOGIN',
    'oauth.update_email_on_login',
    os.getenv('OAUTH_UPDATE_EMAIL_ON_LOGIN', 'False').lower() == 'true',
)

OAUTH_ACCESS_TOKEN_REQUEST_INCLUDE_CLIENT_ID = (
    os.getenv('OAUTH_ACCESS_TOKEN_REQUEST_INCLUDE_CLIENT_ID', 'False').lower() == 'true'
)

OAUTH_AUDIENCE = ConfigVar(
    'OAUTH_AUDIENCE',
    'oauth.audience',
    os.getenv('OAUTH_AUDIENCE', ''),
)

OAUTH_AUTHORIZE_PARAMS = {}
_oauth_authorize_params = os.getenv('OAUTH_AUTHORIZE_PARAMS', '')
if _oauth_authorize_params:
    try:
        _parsed = json.loads(_oauth_authorize_params)
        if isinstance(_parsed, dict):
            OAUTH_AUTHORIZE_PARAMS = _parsed
        else:
            log.warning('OAUTH_AUTHORIZE_PARAMS must be a JSON object, ignoring')
    except (json.JSONDecodeError, TypeError):
        log.warning('OAUTH_AUTHORIZE_PARAMS is not valid JSON, ignoring')


def load_oauth_providers():
    OAUTH_PROVIDERS.clear()
    if GOOGLE_CLIENT_ID.value and GOOGLE_CLIENT_SECRET.value:

        def google_oauth_register(oauth: OAuth):
            client = oauth.register(
                name='google',
                client_id=GOOGLE_CLIENT_ID.value,
                client_secret=GOOGLE_CLIENT_SECRET.value,
                server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
                client_kwargs={
                    'scope': GOOGLE_OAUTH_SCOPE.value,
                    **({'timeout': int(OAUTH_TIMEOUT.value)} if OAUTH_TIMEOUT.value else {}),
                },
                redirect_uri=GOOGLE_REDIRECT_URI.value,
                **({'authorize_params': GOOGLE_OAUTH_AUTHORIZE_PARAMS} if GOOGLE_OAUTH_AUTHORIZE_PARAMS else {}),
            )
            return client

        OAUTH_PROVIDERS['google'] = {
            'register': google_oauth_register,
        }

    if MICROSOFT_CLIENT_ID.value and MICROSOFT_CLIENT_SECRET.value and MICROSOFT_CLIENT_TENANT_ID.value:

        def microsoft_oauth_register(oauth: OAuth):
            client = oauth.register(
                name='microsoft',
                client_id=MICROSOFT_CLIENT_ID.value,
                client_secret=MICROSOFT_CLIENT_SECRET.value,
                server_metadata_url=f'{MICROSOFT_CLIENT_LOGIN_BASE_URL.value}/{MICROSOFT_CLIENT_TENANT_ID.value}/v2.0/.well-known/openid-configuration?appid={MICROSOFT_CLIENT_ID.value}',
                client_kwargs={
                    'scope': MICROSOFT_OAUTH_SCOPE.value,
                    **({'timeout': int(OAUTH_TIMEOUT.value)} if OAUTH_TIMEOUT.value else {}),
                },
                redirect_uri=MICROSOFT_REDIRECT_URI.value,
            )
            return client

        OAUTH_PROVIDERS['microsoft'] = {
            'picture_url': MICROSOFT_CLIENT_PICTURE_URL.value,
            'register': microsoft_oauth_register,
        }

    if GITHUB_CLIENT_ID.value and GITHUB_CLIENT_SECRET.value:

        def github_oauth_register(oauth: OAuth):
            client = oauth.register(
                name='github',
                client_id=GITHUB_CLIENT_ID.value,
                client_secret=GITHUB_CLIENT_SECRET.value,
                access_token_url='https://github.com/login/oauth/access_token',
                authorize_url='https://github.com/login/oauth/authorize',
                api_base_url='https://api.github.com',
                userinfo_endpoint='https://api.github.com/user',
                client_kwargs={
                    'scope': GITHUB_CLIENT_SCOPE.value,
                    **({'timeout': int(OAUTH_TIMEOUT.value)} if OAUTH_TIMEOUT.value else {}),
                },
                redirect_uri=GITHUB_CLIENT_REDIRECT_URI.value,
            )
            return client

        OAUTH_PROVIDERS['github'] = {
            'register': github_oauth_register,
            'sub_claim': 'id',
        }

    if (
        OAUTH_CLIENT_ID.value
        and (OAUTH_CLIENT_SECRET.value or OAUTH_CODE_CHALLENGE_METHOD.value)
        and OPENID_PROVIDER_URL.value
    ):

        def oidc_oauth_register(oauth: OAuth):
            client_kwargs = {
                'scope': OAUTH_SCOPES.value,
                **(
                    {'token_endpoint_auth_method': OAUTH_TOKEN_ENDPOINT_AUTH_METHOD.value}
                    if OAUTH_TOKEN_ENDPOINT_AUTH_METHOD.value
                    else {}
                ),
                **({'timeout': int(OAUTH_TIMEOUT.value)} if OAUTH_TIMEOUT.value else {}),
            }

            if OAUTH_CODE_CHALLENGE_METHOD.value and OAUTH_CODE_CHALLENGE_METHOD.value == 'S256':
                client_kwargs['code_challenge_method'] = 'S256'
            elif OAUTH_CODE_CHALLENGE_METHOD.value:
                raise Exception(
                    'Code challenge methods other than "%s" not supported. Given: "%s"'
                    % ('S256', OAUTH_CODE_CHALLENGE_METHOD.value)
                )

            client = oauth.register(
                name='oidc',
                client_id=OAUTH_CLIENT_ID.value,
                client_secret=OAUTH_CLIENT_SECRET.value,
                server_metadata_url=OPENID_PROVIDER_URL.value,
                client_kwargs=client_kwargs,
                redirect_uri=OPENID_REDIRECT_URI.value,
            )
            return client

        OAUTH_PROVIDERS['oidc'] = {
            'name': OAUTH_PROVIDER_NAME.value,
            'register': oidc_oauth_register,
        }

    if FEISHU_CLIENT_ID.value and FEISHU_CLIENT_SECRET.value:

        def feishu_oauth_register(oauth: OAuth):
            client = oauth.register(
                name='feishu',
                client_id=FEISHU_CLIENT_ID.value,
                client_secret=FEISHU_CLIENT_SECRET.value,
                access_token_url='https://open.feishu.cn/open-apis/authen/v2/oauth/token',
                authorize_url='https://accounts.feishu.cn/open-apis/authen/v1/authorize',
                api_base_url='https://open.feishu.cn/open-apis',
                userinfo_endpoint='https://open.feishu.cn/open-apis/authen/v1/user_info',
                client_kwargs={
                    'scope': FEISHU_OAUTH_SCOPE.value,
                    **({'timeout': int(OAUTH_TIMEOUT.value)} if OAUTH_TIMEOUT.value else {}),
                },
                redirect_uri=FEISHU_REDIRECT_URI.value,
            )
            return client

        OAUTH_PROVIDERS['feishu'] = {
            'register': feishu_oauth_register,
            'sub_claim': 'user_id',
        }

    configured_providers = []
    if GOOGLE_CLIENT_ID.value:
        configured_providers.append('Google')
    if MICROSOFT_CLIENT_ID.value:
        configured_providers.append('Microsoft')
    if GITHUB_CLIENT_ID.value:
        configured_providers.append('GitHub')
    if FEISHU_CLIENT_ID.value:
        configured_providers.append('Feishu')

    if configured_providers and not OPENID_PROVIDER_URL.value and not OPENID_END_SESSION_ENDPOINT.value:
        provider_list = ', '.join(configured_providers)
        log.warning(
            f'⚠️  OAuth providers configured ({provider_list}) but OPENID_PROVIDER_URL not set - logout will not work!'
        )
        log.warning(
            f"Set OPENID_PROVIDER_URL to your OAuth provider's OpenID Connect discovery endpoint,"
            f' or set OPENID_END_SESSION_ENDPOINT to a custom logout URL to fix logout functionality.'
        )


load_oauth_providers()

####################################
# LDAP
####################################

ENABLE_LDAP = ConfigVar(
    'ENABLE_LDAP',
    'ldap.enable',
    os.getenv('ENABLE_LDAP', 'false').lower() == 'true',
)

LDAP_SERVER_LABEL = ConfigVar(
    'LDAP_SERVER_LABEL',
    'ldap.server.label',
    os.getenv('LDAP_SERVER_LABEL', 'LDAP Server'),
)

LDAP_SERVER_HOST = ConfigVar(
    'LDAP_SERVER_HOST',
    'ldap.server.host',
    os.getenv('LDAP_SERVER_HOST', 'localhost'),
)

LDAP_SERVER_PORT = ConfigVar(
    'LDAP_SERVER_PORT',
    'ldap.server.port',
    int(os.getenv('LDAP_SERVER_PORT', '389')),
)

LDAP_ATTRIBUTE_FOR_MAIL = ConfigVar(
    'LDAP_ATTRIBUTE_FOR_MAIL',
    'ldap.server.attribute_for_mail',
    os.getenv('LDAP_ATTRIBUTE_FOR_MAIL', 'mail'),
)

LDAP_ATTRIBUTE_FOR_USERNAME = ConfigVar(
    'LDAP_ATTRIBUTE_FOR_USERNAME',
    'ldap.server.attribute_for_username',
    os.getenv('LDAP_ATTRIBUTE_FOR_USERNAME', 'uid'),
)

LDAP_APP_DN = ConfigVar('LDAP_APP_DN', 'ldap.server.app_dn', os.getenv('LDAP_APP_DN', ''))

LDAP_APP_PASSWORD = ConfigVar(
    'LDAP_APP_PASSWORD',
    'ldap.server.app_password',
    os.getenv('LDAP_APP_PASSWORD', ''),
)

LDAP_SEARCH_BASE = ConfigVar('LDAP_SEARCH_BASE', 'ldap.server.users_dn', os.getenv('LDAP_SEARCH_BASE', ''))

LDAP_SEARCH_FILTERS = ConfigVar(
    'LDAP_SEARCH_FILTER',
    'ldap.server.search_filter',
    os.getenv('LDAP_SEARCH_FILTER', os.getenv('LDAP_SEARCH_FILTERS', '')),
)

LDAP_USE_TLS = ConfigVar(
    'LDAP_USE_TLS',
    'ldap.server.use_tls',
    os.getenv('LDAP_USE_TLS', 'True').lower() == 'true',
)

LDAP_CA_CERT_FILE = ConfigVar(
    'LDAP_CA_CERT_FILE',
    'ldap.server.ca_cert_file',
    os.getenv('LDAP_CA_CERT_FILE', ''),
)

LDAP_VALIDATE_CERT = ConfigVar(
    'LDAP_VALIDATE_CERT',
    'ldap.server.validate_cert',
    os.getenv('LDAP_VALIDATE_CERT', 'True').lower() == 'true',
)

LDAP_CIPHERS = ConfigVar('LDAP_CIPHERS', 'ldap.server.ciphers', os.getenv('LDAP_CIPHERS', 'ALL'))

ENABLE_LDAP_GROUP_MANAGEMENT = ConfigVar(
    'ENABLE_LDAP_GROUP_MANAGEMENT',
    'ldap.group.enable_management',
    os.getenv('ENABLE_LDAP_GROUP_MANAGEMENT', 'False').lower() == 'true',
)

ENABLE_LDAP_GROUP_CREATION = ConfigVar(
    'ENABLE_LDAP_GROUP_CREATION',
    'ldap.group.enable_creation',
    os.getenv('ENABLE_LDAP_GROUP_CREATION', 'False').lower() == 'true',
)

LDAP_ATTRIBUTE_FOR_GROUPS = ConfigVar(
    'LDAP_ATTRIBUTE_FOR_GROUPS',
    'ldap.server.attribute_for_groups',
    os.getenv('LDAP_ATTRIBUTE_FOR_GROUPS', 'memberOf'),
)

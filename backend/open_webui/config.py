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
from open_webui.models.config import Config


async def seed_registered_defaults():
    await Config.rename_prefix('rag.web', 'web')
    await Config.repair_flattened_dict_configs()
    await Config.seed_defaults(DEFAULT_CONFIG)


async def async_reset_config():
    await Config.clear()


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


async def import_legacy_config_json():
    """Migrate legacy config.json → database on first run."""
    if not os.path.exists(f'{DATA_DIR}/config.json'):
        return
    with open(f'{DATA_DIR}/config.json', 'r') as _f:
        await Config.upsert(json.load(_f))
    os.rename(f'{DATA_DIR}/config.json', f'{DATA_DIR}/old_config.json')


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

ENABLE_DIRECT_CONNECTIONS = os.getenv('ENABLE_DIRECT_CONNECTIONS', 'False').lower() == 'true'

####################################
# OLLAMA_BASE_URL
####################################

ENABLE_OLLAMA_API = os.getenv('ENABLE_OLLAMA_API', 'True').lower() == 'true'

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
OLLAMA_BASE_URLS = OLLAMA_BASE_URLS

OLLAMA_API_CONFIGS = {}
_ollama_api_configs = os.getenv('OLLAMA_API_CONFIGS', '')
if _ollama_api_configs:
    try:
        parsed = json.loads(_ollama_api_configs)
        if isinstance(parsed, dict):
            OLLAMA_API_CONFIGS = parsed
        else:
            log.warning('OLLAMA_API_CONFIGS must be a JSON object, ignoring')
    except (json.JSONDecodeError, TypeError):
        log.warning('OLLAMA_API_CONFIGS is not valid JSON, ignoring')

####################################
# OPENAI_API
####################################


ENABLE_OPENAI_API = os.getenv('ENABLE_OPENAI_API', 'True').lower() == 'true'


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
OPENAI_API_KEYS = OPENAI_API_KEYS

OPENAI_API_BASE_URLS = os.getenv('OPENAI_API_BASE_URLS', '')
OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS if OPENAI_API_BASE_URLS != '' else OPENAI_API_BASE_URL

OPENAI_API_BASE_URLS = [
    url.strip() if url != '' else 'https://api.openai.com/v1' for url in OPENAI_API_BASE_URLS.split(';')
]
OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS

OPENAI_API_CONFIGS = {}
_openai_api_configs = os.getenv('OPENAI_API_CONFIGS', '')
if _openai_api_configs:
    try:
        parsed = json.loads(_openai_api_configs)
        if isinstance(parsed, dict):
            OPENAI_API_CONFIGS = parsed
        else:
            log.warning('OPENAI_API_CONFIGS must be a JSON object, ignoring')
    except (json.JSONDecodeError, TypeError):
        log.warning('OPENAI_API_CONFIGS is not valid JSON, ignoring')

# Get the actual OpenAI API key based on the base URL
OPENAI_API_KEY = ''
try:
    OPENAI_API_KEY = OPENAI_API_KEYS[OPENAI_API_BASE_URLS.index('https://api.openai.com/v1')]
except Exception:
    pass
OPENAI_API_BASE_URL = 'https://api.openai.com/v1'


####################################
# MODELS
####################################

ENABLE_BASE_MODELS_CACHE = os.getenv('ENABLE_BASE_MODELS_CACHE', 'False').lower() == 'true'


####################################
# TOOL_SERVERS
####################################

try:
    tool_server_connections = json.loads(os.getenv('TOOL_SERVER_CONNECTIONS', '[]'))
except Exception as e:
    log.exception(f'Error loading TOOL_SERVER_CONNECTIONS: {e}')
    tool_server_connections = []


TOOL_SERVER_CONNECTIONS = tool_server_connections

OAUTH_CLIENT_TIMEOUT = os.getenv('OAUTH_CLIENT_TIMEOUT', '')

####################################
# TERMINAL_SERVER
####################################

terminal_server_connections = json.loads(os.getenv('TERMINAL_SERVER_CONNECTIONS', '[]'))

TERMINAL_SERVER_CONNECTIONS = terminal_server_connections

try:
    TERMINAL_PROXY_HEADERS = json.loads(os.getenv('TERMINAL_PROXY_HEADERS', '{}'))
except Exception:
    TERMINAL_PROXY_HEADERS = {}

####################################
# Code Interpreter
####################################

ENABLE_CODE_EXECUTION = os.getenv('ENABLE_CODE_EXECUTION', 'True').lower() == 'true'

CODE_EXECUTION_ENGINE = os.getenv('CODE_EXECUTION_ENGINE', 'pyodide')

CODE_EXECUTION_JUPYTER_URL = os.getenv('CODE_EXECUTION_JUPYTER_URL', '')

CODE_EXECUTION_JUPYTER_AUTH = os.getenv('CODE_EXECUTION_JUPYTER_AUTH', '')

CODE_EXECUTION_JUPYTER_AUTH_TOKEN = os.getenv('CODE_EXECUTION_JUPYTER_AUTH_TOKEN', '')


CODE_EXECUTION_JUPYTER_AUTH_PASSWORD = os.getenv('CODE_EXECUTION_JUPYTER_AUTH_PASSWORD', '')

CODE_EXECUTION_JUPYTER_TIMEOUT = int(os.getenv('CODE_EXECUTION_JUPYTER_TIMEOUT', '60'))

ENABLE_CODE_INTERPRETER = os.getenv('ENABLE_CODE_INTERPRETER', 'True').lower() == 'true'

ENABLE_MEMORIES = os.getenv('ENABLE_MEMORIES', 'True').lower() == 'true'
ENABLE_MEMORY_SYSTEM_CONTEXT = os.getenv('ENABLE_MEMORY_SYSTEM_CONTEXT', 'True').lower() == 'true'
ENABLE_MEMORY_BACKGROUND_REVIEW = os.getenv('ENABLE_MEMORY_BACKGROUND_REVIEW', 'False').lower() == 'true'
MEMORIES_REVIEW_INTERVAL_TURNS = int(os.getenv('MEMORIES_REVIEW_INTERVAL_TURNS', '10'))
MEMORIES_USER_CHAR_LIMIT = int(os.getenv('MEMORIES_USER_CHAR_LIMIT', '2000'))
MEMORIES_CONTEXT_CHAR_LIMIT = int(os.getenv('MEMORIES_CONTEXT_CHAR_LIMIT', '2000'))

CODE_INTERPRETER_ENGINE = os.getenv('CODE_INTERPRETER_ENGINE', 'pyodide')

CODE_INTERPRETER_PROMPT_TEMPLATE = os.getenv('CODE_INTERPRETER_PROMPT_TEMPLATE', '')

CODE_INTERPRETER_JUPYTER_URL = os.getenv('CODE_INTERPRETER_JUPYTER_URL', os.getenv('CODE_EXECUTION_JUPYTER_URL', ''))

CODE_INTERPRETER_JUPYTER_AUTH = os.getenv(
    'CODE_INTERPRETER_JUPYTER_AUTH',
    os.getenv('CODE_EXECUTION_JUPYTER_AUTH', ''),
)

CODE_INTERPRETER_JUPYTER_AUTH_TOKEN = os.getenv(
    'CODE_INTERPRETER_JUPYTER_AUTH_TOKEN',
    os.getenv('CODE_EXECUTION_JUPYTER_AUTH_TOKEN', ''),
)


CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD = os.getenv(
    'CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD',
    os.getenv('CODE_EXECUTION_JUPYTER_AUTH_PASSWORD', ''),
)

CODE_INTERPRETER_JUPYTER_TIMEOUT = int(
    os.getenv(
        'CODE_INTERPRETER_JUPYTER_TIMEOUT',
        os.getenv('CODE_EXECUTION_JUPYTER_TIMEOUT', '60'),
    )
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

# Valkey Vector Store
VALKEY_URL = os.getenv('VALKEY_URL', '')
VALKEY_COLLECTION_PREFIX = os.getenv('VALKEY_COLLECTION_PREFIX', 'open_webui')
VALKEY_INDEX_TYPE = os.getenv('VALKEY_INDEX_TYPE', 'HNSW').upper()
VALKEY_DISTANCE_METRIC = os.getenv('VALKEY_DISTANCE_METRIC', 'COSINE').upper()
VALKEY_HNSW_M = int(os.getenv('VALKEY_HNSW_M', '16'))
VALKEY_HNSW_EF_CONSTRUCTION = int(os.getenv('VALKEY_HNSW_EF_CONSTRUCTION', '200'))
VALKEY_HNSW_EF_RUNTIME = int(os.getenv('VALKEY_HNSW_EF_RUNTIME', '10'))

####################################
# Information Retrieval (RAG)
####################################


# If configured, Google Drive will be available as an upload option.
ENABLE_GOOGLE_DRIVE_INTEGRATION = os.getenv('ENABLE_GOOGLE_DRIVE_INTEGRATION', 'False').lower() == 'true'

GOOGLE_DRIVE_CLIENT_ID = os.getenv('GOOGLE_DRIVE_CLIENT_ID', '')

GOOGLE_DRIVE_API_KEY = os.getenv('GOOGLE_DRIVE_API_KEY', '')

ENABLE_ONEDRIVE_INTEGRATION = os.getenv('ENABLE_ONEDRIVE_INTEGRATION', 'False').lower() == 'true'


ONEDRIVE_CLIENT_ID = os.getenv('ONEDRIVE_CLIENT_ID', '')
ONEDRIVE_CLIENT_ID_PERSONAL = os.getenv('ONEDRIVE_CLIENT_ID_PERSONAL', ONEDRIVE_CLIENT_ID)
ONEDRIVE_CLIENT_ID_BUSINESS = os.getenv('ONEDRIVE_CLIENT_ID_BUSINESS', ONEDRIVE_CLIENT_ID)

ENABLE_ONEDRIVE_PERSONAL = os.getenv('ENABLE_ONEDRIVE_PERSONAL', 'True').lower() == 'true' and bool(
    ONEDRIVE_CLIENT_ID_PERSONAL
)
ENABLE_ONEDRIVE_BUSINESS = os.getenv('ENABLE_ONEDRIVE_BUSINESS', 'True').lower() == 'true' and bool(
    ONEDRIVE_CLIENT_ID_BUSINESS
)

ONEDRIVE_SHAREPOINT_URL = os.getenv('ONEDRIVE_SHAREPOINT_URL', '')

ONEDRIVE_SHAREPOINT_TENANT_ID = os.getenv('ONEDRIVE_SHAREPOINT_TENANT_ID', '')

# RAG Content Extraction
CONTENT_EXTRACTION_ENGINE = os.getenv('CONTENT_EXTRACTION_ENGINE', '').lower()

DATALAB_MARKER_API_KEY = os.getenv('DATALAB_MARKER_API_KEY', '')

DATALAB_MARKER_API_BASE_URL = os.getenv('DATALAB_MARKER_API_BASE_URL', '')

DATALAB_MARKER_ADDITIONAL_CONFIG = os.getenv('DATALAB_MARKER_ADDITIONAL_CONFIG', '')

DATALAB_MARKER_USE_LLM = os.getenv('DATALAB_MARKER_USE_LLM', 'false').lower() == 'true'

DATALAB_MARKER_SKIP_CACHE = os.getenv('DATALAB_MARKER_SKIP_CACHE', 'false').lower() == 'true'

DATALAB_MARKER_FORCE_OCR = os.getenv('DATALAB_MARKER_FORCE_OCR', 'false').lower() == 'true'

DATALAB_MARKER_PAGINATE = os.getenv('DATALAB_MARKER_PAGINATE', 'false').lower() == 'true'

DATALAB_MARKER_STRIP_EXISTING_OCR = os.getenv('DATALAB_MARKER_STRIP_EXISTING_OCR', 'false').lower() == 'true'

DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION = (
    os.getenv('DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION', 'false').lower() == 'true'
)

DATALAB_MARKER_FORMAT_LINES = os.getenv('DATALAB_MARKER_FORMAT_LINES', 'false').lower() == 'true'

DATALAB_MARKER_OUTPUT_FORMAT = os.getenv('DATALAB_MARKER_OUTPUT_FORMAT', 'markdown')

MINERU_API_MODE = os.getenv('MINERU_API_MODE', 'local')

MINERU_API_URL = os.getenv('MINERU_API_URL', 'http://localhost:8000')

MINERU_API_TIMEOUT = os.getenv('MINERU_API_TIMEOUT', '300')

MINERU_API_KEY = os.getenv('MINERU_API_KEY', '')

mineru_params = os.getenv('MINERU_PARAMS', '')
try:
    mineru_params = json.loads(mineru_params)
except json.JSONDecodeError:
    mineru_params = {}

MINERU_PARAMS = mineru_params

MINERU_FILE_EXTENSIONS = [ext.strip() for ext in os.getenv('MINERU_FILE_EXTENSIONS', 'pdf').split(',') if ext.strip()]

EXTERNAL_DOCUMENT_LOADER_URL = os.getenv('EXTERNAL_DOCUMENT_LOADER_URL', '')

EXTERNAL_DOCUMENT_LOADER_API_KEY = os.getenv('EXTERNAL_DOCUMENT_LOADER_API_KEY', '')

external_document_loader_headers = os.getenv('EXTERNAL_DOCUMENT_LOADER_HEADERS', '')
try:
    external_document_loader_headers = json.loads(external_document_loader_headers)
except json.JSONDecodeError:
    external_document_loader_headers = {}
if not isinstance(external_document_loader_headers, dict):
    external_document_loader_headers = {}

EXTERNAL_DOCUMENT_LOADER_HEADERS = external_document_loader_headers

TIKA_SERVER_URL = os.getenv('TIKA_SERVER_URL', 'http://tika:9998')

DOCLING_SERVER_URL = os.getenv('DOCLING_SERVER_URL', 'http://docling:5001')

DOCLING_API_KEY = os.getenv('DOCLING_API_KEY', '')

docling_params = os.getenv('DOCLING_PARAMS', '')
try:
    docling_params = json.loads(docling_params)
except json.JSONDecodeError:
    docling_params = {}

DOCLING_PARAMS = docling_params

DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv('DOCUMENT_INTELLIGENCE_ENDPOINT', '')

DOCUMENT_INTELLIGENCE_KEY = os.getenv('DOCUMENT_INTELLIGENCE_KEY', '')

DOCUMENT_INTELLIGENCE_MODEL = os.getenv('DOCUMENT_INTELLIGENCE_MODEL', 'prebuilt-layout')

MISTRAL_OCR_API_BASE_URL = os.getenv('MISTRAL_OCR_API_BASE_URL', 'https://api.mistral.ai/v1')

MISTRAL_OCR_API_KEY = os.getenv('MISTRAL_OCR_API_KEY', '')

MISTRAL_OCR_USE_BASE64 = os.getenv('MISTRAL_OCR_USE_BASE64', 'False').lower() == 'true'

PADDLEOCR_VL_BASE_URL = os.getenv('PADDLEOCR_VL_BASE_URL', 'http://localhost:8080')

PADDLEOCR_VL_TOKEN = os.getenv('PADDLEOCR_VL_TOKEN', '')

BYPASS_EMBEDDING_AND_RETRIEVAL = os.getenv('BYPASS_EMBEDDING_AND_RETRIEVAL', 'False').lower() == 'true'


RAG_TOP_K = int(os.getenv('RAG_TOP_K', '3'))
RAG_TOP_K_RERANKER = int(os.getenv('RAG_TOP_K_RERANKER', '3'))
RAG_RELEVANCE_THRESHOLD = float(os.getenv('RAG_RELEVANCE_THRESHOLD', '0.0'))
RAG_HYBRID_BM25_WEIGHT = float(os.getenv('RAG_HYBRID_BM25_WEIGHT', '0.5'))

ENABLE_RAG_HYBRID_SEARCH = os.getenv('ENABLE_RAG_HYBRID_SEARCH', '').lower() == 'true'

ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS = (
    os.getenv('ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS', 'False').lower() == 'true'
)

RAG_FULL_CONTEXT = os.getenv('RAG_FULL_CONTEXT', 'False').lower() == 'true'

RAG_FILE_MAX_COUNT = int(os.getenv('RAG_FILE_MAX_COUNT')) if os.getenv('RAG_FILE_MAX_COUNT') else None

RAG_FILE_MAX_SIZE = int(os.getenv('RAG_FILE_MAX_SIZE')) if os.getenv('RAG_FILE_MAX_SIZE') else None

RAG_FILE_CONTENT_SEARCH_MAX_CHARS = int(os.getenv('RAG_FILE_CONTENT_SEARCH_MAX_CHARS', str(64 * 1024 * 1024)))

FILE_IMAGE_COMPRESSION_WIDTH = (
    int(os.getenv('FILE_IMAGE_COMPRESSION_WIDTH')) if os.getenv('FILE_IMAGE_COMPRESSION_WIDTH') else None
)

FILE_IMAGE_COMPRESSION_HEIGHT = (
    int(os.getenv('FILE_IMAGE_COMPRESSION_HEIGHT')) if os.getenv('FILE_IMAGE_COMPRESSION_HEIGHT') else None
)


RAG_ALLOWED_FILE_EXTENSIONS = [
    ext.strip() for ext in os.getenv('RAG_ALLOWED_FILE_EXTENSIONS', '').split(',') if ext.strip()
]

RAG_EMBEDDING_ENGINE = os.getenv('RAG_EMBEDDING_ENGINE', '')

PDF_EXTRACT_IMAGES = os.getenv('PDF_EXTRACT_IMAGES', 'False').lower() == 'true'

PDF_LOADER_MODE = os.getenv('PDF_LOADER_MODE', 'page')

RAG_EMBEDDING_MODEL = os.getenv('RAG_EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
log.info(f'Embedding model set: {RAG_EMBEDDING_MODEL}')

RAG_TOKENIZER_MODEL = os.getenv('RAG_TOKENIZER_MODEL', '')

RAG_EMBEDDING_MODEL_AUTO_UPDATE = (
    not OFFLINE_MODE and os.getenv('RAG_EMBEDDING_MODEL_AUTO_UPDATE', 'True').lower() == 'true'
)

RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE = os.getenv('RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE', 'True').lower() == 'true'

RAG_EMBEDDING_BATCH_SIZE = int(
    os.getenv('RAG_EMBEDDING_BATCH_SIZE') or os.getenv('RAG_EMBEDDING_OPENAI_BATCH_SIZE', '1')
)

ENABLE_ASYNC_EMBEDDING = os.getenv('ENABLE_ASYNC_EMBEDDING', 'True').lower() == 'true'

RAG_EMBEDDING_CONCURRENT_REQUESTS = int(os.getenv('RAG_EMBEDDING_CONCURRENT_REQUESTS', '0'))

RAG_EMBEDDING_QUERY_PREFIX = os.getenv('RAG_EMBEDDING_QUERY_PREFIX', None)

RAG_EMBEDDING_CONTENT_PREFIX = os.getenv('RAG_EMBEDDING_CONTENT_PREFIX', None)

RAG_EMBEDDING_PREFIX_FIELD_NAME = os.getenv('RAG_EMBEDDING_PREFIX_FIELD_NAME', None)

RAG_RERANKING_ENGINE = os.getenv('RAG_RERANKING_ENGINE', '')

RAG_RERANKING_MODEL = os.getenv('RAG_RERANKING_MODEL', '')
if RAG_RERANKING_MODEL != '':
    log.info(f'Reranking model set: {RAG_RERANKING_MODEL}')


RAG_RERANKING_MODEL_AUTO_UPDATE = (
    not OFFLINE_MODE and os.getenv('RAG_RERANKING_MODEL_AUTO_UPDATE', 'True').lower() == 'true'
)

RAG_RERANKING_MODEL_TRUST_REMOTE_CODE = os.getenv('RAG_RERANKING_MODEL_TRUST_REMOTE_CODE', 'True').lower() == 'true'

RAG_RERANKING_BATCH_SIZE = int(os.getenv('RAG_RERANKING_BATCH_SIZE', '32'))

RAG_EXTERNAL_RERANKER_URL = os.getenv('RAG_EXTERNAL_RERANKER_URL', '')

RAG_EXTERNAL_RERANKER_API_KEY = os.getenv('RAG_EXTERNAL_RERANKER_API_KEY', '')

RAG_EXTERNAL_RERANKER_TIMEOUT = os.getenv('RAG_EXTERNAL_RERANKER_TIMEOUT', '')


RAG_TEXT_SPLITTER = os.getenv('RAG_TEXT_SPLITTER', '')

ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER = os.getenv('ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER', 'True').lower() == 'true'


TIKTOKEN_CACHE_DIR = os.getenv('TIKTOKEN_CACHE_DIR', f'{CACHE_DIR}/tiktoken')
TIKTOKEN_ENCODING_NAME = os.getenv('TIKTOKEN_ENCODING_NAME', 'cl100k_base')


CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000'))

CHUNK_MIN_SIZE_TARGET = int(os.getenv('CHUNK_MIN_SIZE_TARGET', '0'))

CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '100'))

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

RAG_TEMPLATE = os.getenv('RAG_TEMPLATE', DEFAULT_RAG_TEMPLATE)

RAG_OPENAI_API_BASE_URL = os.getenv('RAG_OPENAI_API_BASE_URL', OPENAI_API_BASE_URL)
RAG_OPENAI_API_KEY = os.getenv('RAG_OPENAI_API_KEY', OPENAI_API_KEY)

RAG_AZURE_OPENAI_BASE_URL = os.getenv('RAG_AZURE_OPENAI_BASE_URL', '')
RAG_AZURE_OPENAI_API_KEY = os.getenv('RAG_AZURE_OPENAI_API_KEY', '')
RAG_AZURE_OPENAI_API_VERSION = os.getenv('RAG_AZURE_OPENAI_API_VERSION', '')

RAG_OLLAMA_BASE_URL = os.getenv('RAG_OLLAMA_BASE_URL', OLLAMA_BASE_URL)

RAG_OLLAMA_API_KEY = os.getenv('RAG_OLLAMA_API_KEY', '')


ENABLE_LOCAL_WEB_FETCH = (
    os.getenv(
        'ENABLE_LOCAL_WEB_FETCH',
        os.getenv('ENABLE_RAG_LOCAL_WEB_FETCH', 'False'),
    ).lower()
    == 'true'
)
# Deprecated compatibility alias; use ENABLE_LOCAL_WEB_FETCH for new deployments.
ENABLE_RAG_LOCAL_WEB_FETCH = ENABLE_LOCAL_WEB_FETCH


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


YOUTUBE_LOADER_LANGUAGE = os.getenv('YOUTUBE_LOADER_LANGUAGE', 'en').split(',')

YOUTUBE_LOADER_PROXY_URL = os.getenv('YOUTUBE_LOADER_PROXY_URL', '')


####################################
# Web Search
####################################

ENABLE_WEB_SEARCH = os.getenv('ENABLE_WEB_SEARCH', 'False').lower() == 'true'

ENABLE_WEB_SEARCH_CONFIRMATION = os.getenv('ENABLE_WEB_SEARCH_CONFIRMATION', 'False').lower() == 'true'

WEB_SEARCH_CONFIRMATION_CONTENT = os.getenv(
    'WEB_SEARCH_CONFIRMATION_CONTENT',
    'Your query will be sent to the configured web search provider.',
)

WEB_SEARCH_ENGINE = os.getenv('WEB_SEARCH_ENGINE', '')

BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL = (
    os.getenv('BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL', 'False').lower() == 'true'
)


BYPASS_WEB_SEARCH_WEB_LOADER = os.getenv('BYPASS_WEB_SEARCH_WEB_LOADER', 'False').lower() == 'true'

WEB_SEARCH_RESULT_COUNT = int(os.getenv('WEB_SEARCH_RESULT_COUNT', '3'))


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
WEB_SEARCH_DOMAIN_FILTER_LIST = web_search_domain_filter_list

WEB_SEARCH_CONCURRENT_REQUESTS = int(os.getenv('WEB_SEARCH_CONCURRENT_REQUESTS', '0'))

WEB_FETCH_MAX_CONTENT_LENGTH = (
    int(os.getenv('WEB_FETCH_MAX_CONTENT_LENGTH')) if os.getenv('WEB_FETCH_MAX_CONTENT_LENGTH') else None
)

WEB_LOADER_ENGINE = os.getenv('WEB_LOADER_ENGINE', '')


WEB_LOADER_CONCURRENT_REQUESTS = int(os.getenv('WEB_LOADER_CONCURRENT_REQUESTS', '10'))

WEB_LOADER_TIMEOUT = os.getenv('WEB_LOADER_TIMEOUT', '')


ENABLE_WEB_LOADER_SSL_VERIFICATION = os.getenv('ENABLE_WEB_LOADER_SSL_VERIFICATION', 'True').lower() == 'true'

WEB_SEARCH_TRUST_ENV = os.getenv('WEB_SEARCH_TRUST_ENV', 'True').lower() == 'true'


OLLAMA_CLOUD_WEB_SEARCH_API_KEY = os.getenv('OLLAMA_CLOUD_API_KEY', '')

SEARXNG_QUERY_URL = os.getenv('SEARXNG_QUERY_URL', '')

SEARXNG_LANGUAGE = os.getenv('SEARXNG_LANGUAGE', 'all')

YACY_QUERY_URL = os.getenv('YACY_QUERY_URL', '')

YACY_USERNAME = os.getenv('YACY_USERNAME', '')

YACY_PASSWORD = os.getenv('YACY_PASSWORD', '')

GOOGLE_PSE_API_KEY = os.getenv('GOOGLE_PSE_API_KEY', '')

GOOGLE_PSE_ENGINE_ID = os.getenv('GOOGLE_PSE_ENGINE_ID', '')

BRAVE_SEARCH_API_KEY = os.getenv('BRAVE_SEARCH_API_KEY', '')

BRAVE_SEARCH_CONTEXT_TOKENS = int(os.getenv('BRAVE_SEARCH_CONTEXT_TOKENS', '8192'))

KAGI_SEARCH_API_KEY = os.getenv('KAGI_SEARCH_API_KEY', '')

MOJEEK_SEARCH_API_KEY = os.getenv('MOJEEK_SEARCH_API_KEY', '')

BOCHA_SEARCH_API_KEY = os.getenv('BOCHA_SEARCH_API_KEY', '')

SERPSTACK_API_KEY = os.getenv('SERPSTACK_API_KEY', '')

SERPSTACK_HTTPS = os.getenv('SERPSTACK_HTTPS', 'True').lower() == 'true'

SERPER_API_KEY = os.getenv('SERPER_API_KEY', '')

SERPLY_API_KEY = os.getenv('SERPLY_API_KEY', '')

SERPHOUSE_API_KEY = os.getenv('SERPHOUSE_API_KEY', '')

SERPHOUSE_DOMAIN = os.getenv('SERPHOUSE_DOMAIN', 'google.com')

DDGS_BACKEND = os.getenv('DDGS_BACKEND', 'auto')

JINA_API_KEY = os.getenv('JINA_API_KEY', '')

JINA_API_BASE_URL = os.getenv('JINA_API_BASE_URL', '')

SEARCHAPI_API_KEY = os.getenv('SEARCHAPI_API_KEY', '')

SEARCHAPI_ENGINE = os.getenv('SEARCHAPI_ENGINE', '')

SERPAPI_API_KEY = os.getenv('SERPAPI_API_KEY', '')

SERPAPI_ENGINE = os.getenv('SERPAPI_ENGINE', '')

BING_SEARCH_V7_ENDPOINT = os.getenv('BING_SEARCH_V7_ENDPOINT', 'https://api.bing.microsoft.com/v7.0/search')

BING_SEARCH_V7_SUBSCRIPTION_KEY = os.getenv('BING_SEARCH_V7_SUBSCRIPTION_KEY', '')

AZURE_AI_SEARCH_API_KEY = os.getenv('AZURE_AI_SEARCH_API_KEY', '')

AZURE_AI_SEARCH_ENDPOINT = os.getenv('AZURE_AI_SEARCH_ENDPOINT', '')

AZURE_AI_SEARCH_INDEX_NAME = os.getenv('AZURE_AI_SEARCH_INDEX_NAME', '')

EXA_API_KEY = os.getenv('EXA_API_KEY', '')

PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY', '')

PERPLEXITY_MODEL = os.getenv('PERPLEXITY_MODEL', 'sonar')

PERPLEXITY_SEARCH_CONTEXT_USAGE = os.getenv('PERPLEXITY_SEARCH_CONTEXT_USAGE', 'medium')

PERPLEXITY_SEARCH_API_URL = os.getenv('PERPLEXITY_SEARCH_API_URL', 'https://api.perplexity.ai/search')

MICROSOFT_WEB_IQ_API_BASE_URL = os.getenv('MICROSOFT_WEB_IQ_API_BASE_URL', 'https://api.microsoft.ai/v3')

MICROSOFT_WEB_IQ_API_KEY = os.getenv('MICROSOFT_WEB_IQ_API_KEY', '')

MICROSOFT_WEB_IQ_LANGUAGE = os.getenv('MICROSOFT_WEB_IQ_LANGUAGE', 'en')

SOUGOU_API_SID = os.getenv('SOUGOU_API_SID', '')

SOUGOU_API_SK = os.getenv('SOUGOU_API_SK', '')

TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', '')

TAVILY_EXTRACT_DEPTH = os.getenv('TAVILY_EXTRACT_DEPTH', 'basic')

PLAYWRIGHT_WS_URL = os.getenv('PLAYWRIGHT_WS_URL', '')

PLAYWRIGHT_TIMEOUT = int(os.getenv('PLAYWRIGHT_TIMEOUT', '10000'))

FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY', '')

FIRECRAWL_API_BASE_URL = os.getenv('FIRECRAWL_API_BASE_URL', 'https://api.firecrawl.dev')

FIRECRAWL_TIMEOUT = os.getenv('FIRECRAWL_TIMEOUT', '')

EXTERNAL_WEB_SEARCH_URL = os.getenv('EXTERNAL_WEB_SEARCH_URL', '')

EXTERNAL_WEB_SEARCH_API_KEY = os.getenv('EXTERNAL_WEB_SEARCH_API_KEY', '')

EXTERNAL_WEB_LOADER_URL = os.getenv('EXTERNAL_WEB_LOADER_URL', '')

EXTERNAL_WEB_LOADER_API_KEY = os.getenv('EXTERNAL_WEB_LOADER_API_KEY', '')

YANDEX_WEB_SEARCH_URL = os.getenv('YANDEX_WEB_SEARCH_URL', '')

YANDEX_WEB_SEARCH_API_KEY = os.getenv('YANDEX_WEB_SEARCH_API_KEY', '')

YANDEX_WEB_SEARCH_CONFIG = os.getenv('YANDEX_WEB_SEARCH_CONFIG', '')

YOUCOM_API_KEY = os.getenv('YOUCOM_API_KEY', os.getenv('YDC_API_KEY', ''))

LINKUP_API_KEY = os.getenv('LINKUP_API_KEY', '')

linkup_search_params = os.getenv('LINKUP_SEARCH_PARAMS', '')
try:
    linkup_search_params = json.loads(linkup_search_params)
except json.JSONDecodeError:
    linkup_search_params = {}

LINKUP_SEARCH_PARAMS = linkup_search_params

####################################
# Images
####################################

ENABLE_IMAGE_GENERATION = os.getenv('ENABLE_IMAGE_GENERATION', '').lower() == 'true'

IMAGE_GENERATION_ENGINE = os.getenv('IMAGE_GENERATION_ENGINE', 'openai')

IMAGE_GENERATION_MODEL = os.getenv('IMAGE_GENERATION_MODEL', '')

# Regex pattern for models that support IMAGE_SIZE = "auto".
IMAGE_AUTO_SIZE_MODELS_REGEX_PATTERN = os.getenv('IMAGE_AUTO_SIZE_MODELS_REGEX_PATTERN', '^gpt-image')

# Regex pattern for models that return URLs instead of base64 data.
IMAGE_URL_RESPONSE_MODELS_REGEX_PATTERN = os.getenv('IMAGE_URL_RESPONSE_MODELS_REGEX_PATTERN', '^gpt-image')

IMAGE_SIZE = os.getenv('IMAGE_SIZE', '512x512')

IMAGE_STEPS = int(os.getenv('IMAGE_STEPS', 50))

ENABLE_IMAGE_PROMPT_GENERATION = os.getenv('ENABLE_IMAGE_PROMPT_GENERATION', 'true').lower() == 'true'

AUTOMATIC1111_BASE_URL = os.getenv('AUTOMATIC1111_BASE_URL', '')
AUTOMATIC1111_API_AUTH = os.getenv('AUTOMATIC1111_API_AUTH', '')

automatic1111_params = os.getenv('AUTOMATIC1111_PARAMS', '')
try:
    automatic1111_params = json.loads(automatic1111_params)
except json.JSONDecodeError:
    automatic1111_params = {}

AUTOMATIC1111_PARAMS = automatic1111_params

COMFYUI_BASE_URL = os.getenv('COMFYUI_BASE_URL', '')

COMFYUI_API_KEY = os.getenv('COMFYUI_API_KEY', '')

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


COMFYUI_WORKFLOW = os.getenv('COMFYUI_WORKFLOW', COMFYUI_DEFAULT_WORKFLOW)

comfyui_workflow_nodes = os.getenv('COMFYUI_WORKFLOW_NODES', '')
try:
    comfyui_workflow_nodes = json.loads(comfyui_workflow_nodes)
except json.JSONDecodeError:
    comfyui_workflow_nodes = []

COMFYUI_WORKFLOW_NODES = comfyui_workflow_nodes

IMAGES_OPENAI_API_BASE_URL = os.getenv('IMAGES_OPENAI_API_BASE_URL', OPENAI_API_BASE_URL)
IMAGES_OPENAI_API_VERSION = os.getenv('IMAGES_OPENAI_API_VERSION', '')

IMAGES_OPENAI_API_KEY = os.getenv('IMAGES_OPENAI_API_KEY', OPENAI_API_KEY)

images_openai_params = os.getenv('IMAGES_OPENAI_PARAMS', '')
try:
    images_openai_params = json.loads(images_openai_params)
except json.JSONDecodeError:
    images_openai_params = {}


IMAGES_OPENAI_API_PARAMS = images_openai_params


IMAGES_GEMINI_API_BASE_URL = os.getenv('IMAGES_GEMINI_API_BASE_URL', GEMINI_API_BASE_URL)
IMAGES_GEMINI_API_KEY = os.getenv('IMAGES_GEMINI_API_KEY', GEMINI_API_KEY)

IMAGES_GEMINI_ENDPOINT_METHOD = os.getenv('IMAGES_GEMINI_ENDPOINT_METHOD', '')

ENABLE_IMAGE_EDIT = os.getenv('ENABLE_IMAGE_EDIT', '').lower() == 'true'

IMAGE_EDIT_ENGINE = os.getenv('IMAGE_EDIT_ENGINE', 'openai')

IMAGE_EDIT_MODEL = os.getenv('IMAGE_EDIT_MODEL', '')

IMAGE_EDIT_SIZE = os.getenv('IMAGE_EDIT_SIZE', '')

ENABLE_OPENAI_IMAGE_EDIT_NORMALIZATION = os.getenv('ENABLE_OPENAI_IMAGE_EDIT_NORMALIZATION', 'true').lower() == 'true'

IMAGES_EDIT_OPENAI_API_BASE_URL = os.getenv('IMAGES_EDIT_OPENAI_API_BASE_URL', OPENAI_API_BASE_URL)
IMAGES_EDIT_OPENAI_API_VERSION = os.getenv('IMAGES_EDIT_OPENAI_API_VERSION', '')

IMAGES_EDIT_OPENAI_API_KEY = os.getenv('IMAGES_EDIT_OPENAI_API_KEY', OPENAI_API_KEY)

IMAGES_EDIT_GEMINI_API_BASE_URL = os.getenv('IMAGES_EDIT_GEMINI_API_BASE_URL', GEMINI_API_BASE_URL)
IMAGES_EDIT_GEMINI_API_KEY = os.getenv('IMAGES_EDIT_GEMINI_API_KEY', GEMINI_API_KEY)


IMAGES_EDIT_COMFYUI_BASE_URL = os.getenv('IMAGES_EDIT_COMFYUI_BASE_URL', '')
IMAGES_EDIT_COMFYUI_API_KEY = os.getenv('IMAGES_EDIT_COMFYUI_API_KEY', '')

IMAGES_EDIT_COMFYUI_WORKFLOW = os.getenv('IMAGES_EDIT_COMFYUI_WORKFLOW', '')

images_edit_comfyui_workflow_nodes = os.getenv('IMAGES_EDIT_COMFYUI_WORKFLOW_NODES', '')
try:
    images_edit_comfyui_workflow_nodes = json.loads(images_edit_comfyui_workflow_nodes)
except json.JSONDecodeError:
    images_edit_comfyui_workflow_nodes = []

IMAGES_EDIT_COMFYUI_WORKFLOW_NODES = images_edit_comfyui_workflow_nodes

####################################
# Audio
####################################

# Transcription
WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')

WHISPER_COMPUTE_TYPE = os.getenv('WHISPER_COMPUTE_TYPE', 'int8')
WHISPER_MODEL_DIR = os.getenv('WHISPER_MODEL_DIR', f'{CACHE_DIR}/whisper/models')
WHISPER_MODEL_AUTO_UPDATE = not OFFLINE_MODE and os.getenv('WHISPER_MODEL_AUTO_UPDATE', '').lower() == 'true'

WHISPER_VAD_FILTER = os.getenv('WHISPER_VAD_FILTER', 'False').lower() == 'true'

WHISPER_MULTILINGUAL = os.getenv('WHISPER_MULTILINGUAL', 'False').lower() == 'true'

WHISPER_LANGUAGE = os.getenv('WHISPER_LANGUAGE', '').lower() or None

# Add Deepgram configuration
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY', '')

# ElevenLabs configuration
ELEVENLABS_API_BASE_URL = os.getenv('ELEVENLABS_API_BASE_URL', 'https://api.elevenlabs.io')

AUDIO_STT_OPENAI_API_BASE_URL = os.getenv('AUDIO_STT_OPENAI_API_BASE_URL', OPENAI_API_BASE_URL)

AUDIO_STT_OPENAI_API_KEY = os.getenv('AUDIO_STT_OPENAI_API_KEY', OPENAI_API_KEY)

AUDIO_STT_OPENAI_API_REQUEST_FORMAT = os.getenv('AUDIO_STT_OPENAI_API_REQUEST_FORMAT', 'multipart')

AUDIO_STT_ENGINE = os.getenv('AUDIO_STT_ENGINE', '')

AUDIO_STT_MODEL = os.getenv('AUDIO_STT_MODEL', '')

AUDIO_STT_SUPPORTED_CONTENT_TYPES = [
    content_type.strip()
    for content_type in os.getenv('AUDIO_STT_SUPPORTED_CONTENT_TYPES', '').split(',')
    if content_type.strip()
]

AUDIO_STT_ALLOWED_EXTENSIONS = [
    ext.strip()
    for ext in os.getenv(
        'AUDIO_STT_ALLOWED_EXTENSIONS',
        'mp3,wav,m4a,webm,ogg,flac,mp4,mpga,mpeg',
    ).split(',')
    if ext.strip()
]

AUDIO_STT_AZURE_API_KEY = os.getenv('AUDIO_STT_AZURE_API_KEY', '')

AUDIO_STT_AZURE_REGION = os.getenv('AUDIO_STT_AZURE_REGION', '')

AUDIO_STT_AZURE_LOCALES = os.getenv('AUDIO_STT_AZURE_LOCALES', '')

AUDIO_STT_AZURE_BASE_URL = os.getenv('AUDIO_STT_AZURE_BASE_URL', '')

AUDIO_STT_AZURE_MAX_SPEAKERS = os.getenv('AUDIO_STT_AZURE_MAX_SPEAKERS', '')

AUDIO_STT_MISTRAL_API_KEY = os.getenv('AUDIO_STT_MISTRAL_API_KEY', '')

AUDIO_STT_MISTRAL_API_BASE_URL = os.getenv('AUDIO_STT_MISTRAL_API_BASE_URL', 'https://api.mistral.ai/v1')

AUDIO_STT_MISTRAL_USE_CHAT_COMPLETIONS = os.getenv('AUDIO_STT_MISTRAL_USE_CHAT_COMPLETIONS', 'false').lower() == 'true'

AUDIO_TTS_OPENAI_API_BASE_URL = os.getenv('AUDIO_TTS_OPENAI_API_BASE_URL', OPENAI_API_BASE_URL)
AUDIO_TTS_OPENAI_API_KEY = os.getenv('AUDIO_TTS_OPENAI_API_KEY', OPENAI_API_KEY)

audio_tts_openai_params = os.getenv('AUDIO_TTS_OPENAI_PARAMS', '')
try:
    audio_tts_openai_params = json.loads(audio_tts_openai_params)
except json.JSONDecodeError:
    audio_tts_openai_params = {}

AUDIO_TTS_OPENAI_PARAMS = audio_tts_openai_params


AUDIO_TTS_API_KEY = os.getenv('AUDIO_TTS_API_KEY', '')

AUDIO_TTS_ENGINE = os.getenv('AUDIO_TTS_ENGINE', '')


AUDIO_TTS_MODEL = os.getenv('AUDIO_TTS_MODEL', 'tts-1')

AUDIO_TTS_VOICE = os.getenv('AUDIO_TTS_VOICE', 'alloy')

AUDIO_TTS_SPLIT_ON = os.getenv('AUDIO_TTS_SPLIT_ON', 'punctuation')

AUDIO_TTS_AZURE_SPEECH_REGION = os.getenv('AUDIO_TTS_AZURE_SPEECH_REGION', '')

AUDIO_TTS_AZURE_SPEECH_BASE_URL = os.getenv('AUDIO_TTS_AZURE_SPEECH_BASE_URL', '')

AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT = os.getenv(
    'AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT', 'audio-24khz-160kbitrate-mono-mp3'
)

AUDIO_TTS_MISTRAL_API_KEY = os.getenv('AUDIO_TTS_MISTRAL_API_KEY', '')

AUDIO_TTS_MISTRAL_API_BASE_URL = os.getenv('AUDIO_TTS_MISTRAL_API_BASE_URL', 'https://api.mistral.ai/v1')

####################################
# WEBUI
####################################


WEBUI_URL = os.getenv('WEBUI_URL', '')


ENABLE_SIGNUP = False if not WEBUI_AUTH else os.getenv('ENABLE_SIGNUP', 'True').lower() == 'true'

ENABLE_LOGIN_FORM = os.getenv('ENABLE_LOGIN_FORM', 'True').lower() == 'true'

ENABLE_PASSWORD_CHANGE_FORM = os.getenv('ENABLE_PASSWORD_CHANGE_FORM', 'True').lower() == 'true'

ENABLE_PASSWORD_AUTH = os.getenv('ENABLE_PASSWORD_AUTH', 'True').lower() == 'true'

DEFAULT_LOCALE = os.getenv('DEFAULT_LOCALE', '')

DEFAULT_MODELS = os.getenv('DEFAULT_MODELS', None)

DEFAULT_PINNED_MODELS = os.getenv('DEFAULT_PINNED_MODELS', None)

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

DEFAULT_PROMPT_SUGGESTIONS = default_prompt_suggestions

MODEL_ORDER_LIST = []

try:
    default_model_metadata = json.loads(os.getenv('DEFAULT_MODEL_METADATA', '{}'))
except Exception as e:
    log.exception(f'Error loading DEFAULT_MODEL_METADATA: {e}')
    default_model_metadata = {}

DEFAULT_MODEL_METADATA = default_model_metadata

try:
    default_model_params = json.loads(os.getenv('DEFAULT_MODEL_PARAMS', '{}'))
except Exception as e:
    log.exception(f'Error loading DEFAULT_MODEL_PARAMS: {e}')
    default_model_params = {}

DEFAULT_MODEL_PARAMS = default_model_params

DEFAULT_USER_ROLE = os.getenv('DEFAULT_USER_ROLE', 'pending')

DEFAULT_GROUP_ID = os.getenv('DEFAULT_GROUP_ID', '')

PENDING_USER_OVERLAY_TITLE = os.getenv('PENDING_USER_OVERLAY_TITLE', '')

PENDING_USER_OVERLAY_CONTENT = os.getenv('PENDING_USER_OVERLAY_CONTENT', '')


RESPONSE_WATERMARK = os.getenv('RESPONSE_WATERMARK', '')

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

USER_PERMISSIONS_WORKSPACE_SKILLS_IMPORT = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_SKILLS_IMPORT', 'False').lower() == 'true'
)

USER_PERMISSIONS_WORKSPACE_SKILLS_EXPORT = (
    os.getenv('USER_PERMISSIONS_WORKSPACE_SKILLS_EXPORT', 'False').lower() == 'true'
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

USER_PERMISSIONS_FOLDERS_ALLOW_SHARING = os.getenv('USER_PERMISSIONS_FOLDERS_ALLOW_SHARING', 'False').lower() == 'true'


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

USER_PERMISSIONS_CHAT_IMPORT = os.getenv('USER_PERMISSIONS_CHAT_IMPORT', 'True').lower() == 'true'

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

USER_PERMISSIONS_FEATURES_USER_WEBHOOKS = (
    os.getenv('USER_PERMISSIONS_FEATURES_USER_WEBHOOKS', 'False').lower() == 'true'
)


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
        'skills_import': USER_PERMISSIONS_WORKSPACE_SKILLS_IMPORT,
        'skills_export': USER_PERMISSIONS_WORKSPACE_SKILLS_EXPORT,
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
        'folders': USER_PERMISSIONS_FOLDERS_ALLOW_SHARING,
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
        'import': USER_PERMISSIONS_CHAT_IMPORT,
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
        'webhooks': USER_PERMISSIONS_FEATURES_USER_WEBHOOKS,
    },
    'settings': {
        'interface': USER_PERMISSIONS_SETTINGS_INTERFACE,
    },
}

USER_PERMISSIONS = DEFAULT_USER_PERMISSIONS

ENABLE_FOLDERS = os.getenv('ENABLE_FOLDERS', 'True').lower() == 'true'

FOLDER_MAX_FILE_COUNT = os.getenv('FOLDER_MAX_FILE_COUNT', '')

ENABLE_CHANNELS = os.getenv('ENABLE_CHANNELS', 'False').lower() == 'true'

ENABLE_CALENDAR = os.getenv('ENABLE_CALENDAR', 'True').lower() == 'true'

ENABLE_AUTOMATIONS = os.getenv('ENABLE_AUTOMATIONS', 'True').lower() == 'true'

AUTOMATION_MAX_COUNT = os.getenv('AUTOMATION_MAX_COUNT', '')

AUTOMATION_MIN_INTERVAL = os.getenv('AUTOMATION_MIN_INTERVAL', '')

AUTOMATION_AUTH_TOKEN_EXPIRES_IN = os.getenv('AUTOMATION_AUTH_TOKEN_EXPIRES_IN', '1h')

ENABLE_NOTES = os.getenv('ENABLE_NOTES', 'True').lower() == 'true'

ENABLE_USER_STATUS = os.getenv('ENABLE_USER_STATUS', 'True').lower() == 'true'

ENABLE_EVALUATION_ARENA_MODELS = os.getenv('ENABLE_EVALUATION_ARENA_MODELS', 'True').lower() == 'true'
try:
    evaluation_arena_models = json.loads(os.getenv('EVALUATION_ARENA_MODELS', '[]'))
    if not isinstance(evaluation_arena_models, list) or not all(
        isinstance(model, dict) for model in evaluation_arena_models
    ):
        raise ValueError('EVALUATION_ARENA_MODELS must be a JSON list of objects')
except Exception as e:
    log.exception(f'Error loading EVALUATION_ARENA_MODELS: {e}')
    evaluation_arena_models = []

EVALUATION_ARENA_MODELS = evaluation_arena_models

DEFAULT_ARENA_MODEL = {
    'id': 'arena-model',
    'name': 'Arena Model',
    'meta': {
        'profile_image_url': '/favicon.png',
        'description': 'Submit your questions to anonymous AI chatbots and vote on the best response.',
        'model_ids': None,
    },
}

WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')

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

ENABLE_COMMUNITY_SHARING = os.getenv('ENABLE_COMMUNITY_SHARING', 'True').lower() == 'true'

ENABLE_MESSAGE_RATING = os.getenv('ENABLE_MESSAGE_RATING', 'True').lower() == 'true'

ENABLE_USER_WEBHOOKS = os.getenv('ENABLE_USER_WEBHOOKS', 'False').lower() == 'true'

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

WEBUI_BANNERS = banners


SHOW_ADMIN_DETAILS = os.getenv('SHOW_ADMIN_DETAILS', 'true').lower() == 'true'

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', None)


####################################
# TASKS
####################################


TASK_MODEL = os.getenv('TASK_MODEL', '')

TASK_MODEL_EXTERNAL = os.getenv('TASK_MODEL_EXTERNAL', '')

ENABLE_CONTEXT_COMPACTION = os.getenv('ENABLE_CONTEXT_COMPACTION', 'False').lower() == 'true'

CONTEXT_COMPACTION_TOKEN_THRESHOLD = int(os.getenv('CONTEXT_COMPACTION_TOKEN_THRESHOLD', '80000'))

CONTEXT_COMPACTION_PROMPT_TEMPLATE = os.getenv('CONTEXT_COMPACTION_PROMPT_TEMPLATE', '')

TITLE_GENERATION_PROMPT_TEMPLATE = os.getenv('TITLE_GENERATION_PROMPT_TEMPLATE', '')

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

TAGS_GENERATION_PROMPT_TEMPLATE = os.getenv('TAGS_GENERATION_PROMPT_TEMPLATE', '')

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

IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE = os.getenv('IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE', '')

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


FOLLOW_UP_GENERATION_PROMPT_TEMPLATE = os.getenv('FOLLOW_UP_GENERATION_PROMPT_TEMPLATE', '')

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

ENABLE_FOLLOW_UP_GENERATION = os.getenv('ENABLE_FOLLOW_UP_GENERATION', 'True').lower() == 'true'

ENABLE_TAGS_GENERATION = os.getenv('ENABLE_TAGS_GENERATION', 'True').lower() == 'true'

ENABLE_TITLE_GENERATION = os.getenv('ENABLE_TITLE_GENERATION', 'True').lower() == 'true'


ENABLE_SEARCH_QUERY_GENERATION = os.getenv('ENABLE_SEARCH_QUERY_GENERATION', 'True').lower() == 'true'

ENABLE_RETRIEVAL_QUERY_GENERATION = os.getenv('ENABLE_RETRIEVAL_QUERY_GENERATION', 'True').lower() == 'true'


QUERY_GENERATION_PROMPT_TEMPLATE = os.getenv('QUERY_GENERATION_PROMPT_TEMPLATE', '')

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

ENABLE_AUTOCOMPLETE_GENERATION = os.getenv('ENABLE_AUTOCOMPLETE_GENERATION', 'False').lower() == 'true'

AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH = int(os.getenv('AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH', '-1'))

AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE = os.getenv('AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE', '')


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


VOICE_MODE_PROMPT_TEMPLATE = os.getenv('VOICE_MODE_PROMPT_TEMPLATE', '')

ENABLE_VOICE_MODE_PROMPT = os.getenv('ENABLE_VOICE_MODE_PROMPT', 'True').lower() == 'true'

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

TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = os.getenv('TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE', '')


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

ENABLE_API_KEYS = os.getenv('ENABLE_API_KEYS', 'False').lower() == 'true'

ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS = (
    os.getenv(
        'ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS',
        os.getenv('ENABLE_API_KEY_ENDPOINT_RESTRICTIONS', 'False'),
    ).lower()
    == 'true'
)

API_KEYS_ALLOWED_ENDPOINTS = os.getenv('API_KEYS_ALLOWED_ENDPOINTS', os.getenv('API_KEY_ALLOWED_ENDPOINTS', ''))

JWT_EXPIRES_IN = os.getenv('JWT_EXPIRES_IN', '4w')

if JWT_EXPIRES_IN == '-1':
    log.warning(
        "⚠️  SECURITY WARNING: JWT_EXPIRES_IN is set to '-1'\n"
        '    See: https://docs.openwebui.com/reference/env-configuration\n'
    )

####################################
# OAuth config
####################################

ENABLE_OAUTH_SIGNUP = os.getenv('ENABLE_OAUTH_SIGNUP', 'False').lower() == 'true'

OAUTH_AUTO_REDIRECT = os.getenv('OAUTH_AUTO_REDIRECT', 'False').lower() == 'true'

OAUTH_REFRESH_TOKEN_INCLUDE_SCOPE = os.getenv('OAUTH_REFRESH_TOKEN_INCLUDE_SCOPE', 'False').lower() == 'true'


OAUTH_MERGE_ACCOUNTS_BY_EMAIL = os.getenv('OAUTH_MERGE_ACCOUNTS_BY_EMAIL', 'False').lower() == 'true'

OAUTH_PROVIDERS = {}

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')

GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')


GOOGLE_OAUTH_SCOPE = os.getenv('GOOGLE_OAUTH_SCOPE', 'openid email profile')

GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', '')

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

MICROSOFT_CLIENT_ID = os.getenv('MICROSOFT_CLIENT_ID', '')

MICROSOFT_CLIENT_SECRET = os.getenv('MICROSOFT_CLIENT_SECRET', '')

MICROSOFT_CLIENT_TENANT_ID = os.getenv('MICROSOFT_CLIENT_TENANT_ID', '')

MICROSOFT_CLIENT_LOGIN_BASE_URL = os.getenv('MICROSOFT_CLIENT_LOGIN_BASE_URL', 'https://login.microsoftonline.com')

MICROSOFT_CLIENT_PICTURE_URL = os.getenv(
    'MICROSOFT_CLIENT_PICTURE_URL',
    'https://graph.microsoft.com/v1.0/me/photo/$value',
)


MICROSOFT_OAUTH_SCOPE = os.getenv('MICROSOFT_OAUTH_SCOPE', 'openid email profile')

MICROSOFT_REDIRECT_URI = os.getenv('MICROSOFT_REDIRECT_URI', '')

GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID', '')

GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET', '')

GITHUB_CLIENT_SCOPE = os.getenv('GITHUB_CLIENT_SCOPE', 'user:email')

GITHUB_CLIENT_REDIRECT_URI = os.getenv('GITHUB_CLIENT_REDIRECT_URI', '')

OAUTH_CLIENT_ID = os.getenv('OAUTH_CLIENT_ID', '')

OAUTH_CLIENT_SECRET = os.getenv('OAUTH_CLIENT_SECRET', '')

OPENID_PROVIDER_URL = os.getenv('OPENID_PROVIDER_URL', '')

OPENID_END_SESSION_ENDPOINT = os.getenv('OPENID_END_SESSION_ENDPOINT', '')

OPENID_REDIRECT_URI = os.getenv('OPENID_REDIRECT_URI', '')

OAUTH_SCOPES = os.getenv('OAUTH_SCOPES', 'openid email profile')

OAUTH_TIMEOUT = os.getenv('OAUTH_TIMEOUT', '')

OAUTH_TOKEN_ENDPOINT_AUTH_METHOD = os.getenv('OAUTH_TOKEN_ENDPOINT_AUTH_METHOD', None)

OAUTH_CODE_CHALLENGE_METHOD = os.getenv('OAUTH_CODE_CHALLENGE_METHOD', None)

OAUTH_PROVIDER_NAME = os.getenv('OAUTH_PROVIDER_NAME', 'SSO')

OAUTH_SUB_CLAIM = os.getenv('OAUTH_SUB_CLAIM', None)

OAUTH_USERNAME_CLAIM = os.getenv('OAUTH_USERNAME_CLAIM', 'name')


OAUTH_PICTURE_CLAIM = os.getenv('OAUTH_PICTURE_CLAIM', 'picture')

OAUTH_EMAIL_CLAIM = os.getenv('OAUTH_EMAIL_CLAIM', 'email')

OAUTH_GROUPS_CLAIM = os.getenv('OAUTH_GROUPS_CLAIM', os.getenv('OAUTH_GROUP_CLAIM', 'groups'))

FEISHU_CLIENT_ID = os.getenv('FEISHU_CLIENT_ID', '')

FEISHU_CLIENT_SECRET = os.getenv('FEISHU_CLIENT_SECRET', '')

FEISHU_OAUTH_SCOPE = os.getenv('FEISHU_OAUTH_SCOPE', 'contact:user.base:readonly')

FEISHU_REDIRECT_URI = os.getenv('FEISHU_REDIRECT_URI', '')

ENABLE_OAUTH_ROLE_MANAGEMENT = os.getenv('ENABLE_OAUTH_ROLE_MANAGEMENT', 'False').lower() == 'true'

ENABLE_OAUTH_GROUP_MANAGEMENT = os.getenv('ENABLE_OAUTH_GROUP_MANAGEMENT', 'False').lower() == 'true'

ENABLE_OAUTH_GROUP_CREATION = os.getenv('ENABLE_OAUTH_GROUP_CREATION', 'False').lower() == 'true'


oauth_group_default_share = os.getenv('OAUTH_GROUP_DEFAULT_SHARE', 'true').strip().lower()
OAUTH_GROUP_DEFAULT_SHARE = 'members' if oauth_group_default_share == 'members' else oauth_group_default_share == 'true'


OAUTH_BLOCKED_GROUPS = os.getenv('OAUTH_BLOCKED_GROUPS', '[]')

OAUTH_GROUPS_SEPARATOR = os.getenv('OAUTH_GROUPS_SEPARATOR', ';')

OAUTH_ROLES_CLAIM = os.getenv('OAUTH_ROLES_CLAIM', 'roles')

OAUTH_ROLES_SEPARATOR = os.getenv('OAUTH_ROLES_SEPARATOR', ',')

OAUTH_ALLOWED_ROLES = [
    role.strip()
    for role in os.getenv('OAUTH_ALLOWED_ROLES', f'user{OAUTH_ROLES_SEPARATOR}admin').split(OAUTH_ROLES_SEPARATOR)
    if role
]

OAUTH_ADMIN_ROLES = [
    role.strip() for role in os.getenv('OAUTH_ADMIN_ROLES', 'admin').split(OAUTH_ROLES_SEPARATOR) if role
]

OAUTH_ALLOWED_DOMAINS = [domain.strip() for domain in os.getenv('OAUTH_ALLOWED_DOMAINS', '*').split(',')]

OAUTH_UPDATE_PICTURE_ON_LOGIN = os.getenv('OAUTH_UPDATE_PICTURE_ON_LOGIN', 'False').lower() == 'true'

OAUTH_UPDATE_NAME_ON_LOGIN = os.getenv('OAUTH_UPDATE_NAME_ON_LOGIN', 'False').lower() == 'true'

OAUTH_UPDATE_EMAIL_ON_LOGIN = os.getenv('OAUTH_UPDATE_EMAIL_ON_LOGIN', 'False').lower() == 'true'

OAUTH_ACCESS_TOKEN_REQUEST_INCLUDE_CLIENT_ID = (
    os.getenv('OAUTH_ACCESS_TOKEN_REQUEST_INCLUDE_CLIENT_ID', 'False').lower() == 'true'
)

OAUTH_AUDIENCE = os.getenv('OAUTH_AUDIENCE', '')

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
    if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:

        def google_oauth_register(oauth: OAuth):
            client = oauth.register(
                name='google',
                client_id=GOOGLE_CLIENT_ID,
                client_secret=GOOGLE_CLIENT_SECRET,
                server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
                client_kwargs={
                    'scope': GOOGLE_OAUTH_SCOPE,
                    **({'timeout': int(OAUTH_TIMEOUT)} if OAUTH_TIMEOUT else {}),
                },
                redirect_uri=GOOGLE_REDIRECT_URI,
                **({'authorize_params': GOOGLE_OAUTH_AUTHORIZE_PARAMS} if GOOGLE_OAUTH_AUTHORIZE_PARAMS else {}),
            )
            return client

        OAUTH_PROVIDERS['google'] = {
            'register': google_oauth_register,
        }

    if MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET and MICROSOFT_CLIENT_TENANT_ID:

        def microsoft_oauth_register(oauth: OAuth):
            client = oauth.register(
                name='microsoft',
                client_id=MICROSOFT_CLIENT_ID,
                client_secret=MICROSOFT_CLIENT_SECRET,
                server_metadata_url=f'{MICROSOFT_CLIENT_LOGIN_BASE_URL}/{MICROSOFT_CLIENT_TENANT_ID}/v2.0/.well-known/openid-configuration?appid={MICROSOFT_CLIENT_ID}',
                client_kwargs={
                    'scope': MICROSOFT_OAUTH_SCOPE,
                    **({'timeout': int(OAUTH_TIMEOUT)} if OAUTH_TIMEOUT else {}),
                },
                redirect_uri=MICROSOFT_REDIRECT_URI,
            )
            return client

        OAUTH_PROVIDERS['microsoft'] = {
            'picture_url': MICROSOFT_CLIENT_PICTURE_URL,
            'register': microsoft_oauth_register,
        }

    if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET:

        def github_oauth_register(oauth: OAuth):
            client = oauth.register(
                name='github',
                client_id=GITHUB_CLIENT_ID,
                client_secret=GITHUB_CLIENT_SECRET,
                access_token_url='https://github.com/login/oauth/access_token',
                authorize_url='https://github.com/login/oauth/authorize',
                api_base_url='https://api.github.com',
                userinfo_endpoint='https://api.github.com/user',
                client_kwargs={
                    'scope': GITHUB_CLIENT_SCOPE,
                    **({'timeout': int(OAUTH_TIMEOUT)} if OAUTH_TIMEOUT else {}),
                },
                redirect_uri=GITHUB_CLIENT_REDIRECT_URI,
            )
            return client

        OAUTH_PROVIDERS['github'] = {
            'register': github_oauth_register,
            'sub_claim': 'id',
        }

    if OAUTH_CLIENT_ID and (OAUTH_CLIENT_SECRET or OAUTH_CODE_CHALLENGE_METHOD) and OPENID_PROVIDER_URL:

        def oidc_oauth_register(oauth: OAuth):
            client_kwargs = {
                'scope': OAUTH_SCOPES,
                **(
                    {'token_endpoint_auth_method': OAUTH_TOKEN_ENDPOINT_AUTH_METHOD}
                    if OAUTH_TOKEN_ENDPOINT_AUTH_METHOD
                    else {}
                ),
                **({'timeout': int(OAUTH_TIMEOUT)} if OAUTH_TIMEOUT else {}),
            }

            if OAUTH_CODE_CHALLENGE_METHOD and OAUTH_CODE_CHALLENGE_METHOD == 'S256':
                client_kwargs['code_challenge_method'] = 'S256'
            elif OAUTH_CODE_CHALLENGE_METHOD:
                raise Exception(
                    'Code challenge methods other than "%s" not supported. Given: "%s"'
                    % ('S256', OAUTH_CODE_CHALLENGE_METHOD)
                )

            client = oauth.register(
                name='oidc',
                client_id=OAUTH_CLIENT_ID,
                client_secret=OAUTH_CLIENT_SECRET,
                server_metadata_url=OPENID_PROVIDER_URL,
                client_kwargs=client_kwargs,
                redirect_uri=OPENID_REDIRECT_URI,
            )
            return client

        OAUTH_PROVIDERS['oidc'] = {
            'name': OAUTH_PROVIDER_NAME,
            'register': oidc_oauth_register,
        }

    if FEISHU_CLIENT_ID and FEISHU_CLIENT_SECRET:

        def feishu_oauth_register(oauth: OAuth):
            client = oauth.register(
                name='feishu',
                client_id=FEISHU_CLIENT_ID,
                client_secret=FEISHU_CLIENT_SECRET,
                access_token_url='https://open.feishu.cn/open-apis/authen/v2/oauth/token',
                authorize_url='https://accounts.feishu.cn/open-apis/authen/v1/authorize',
                api_base_url='https://open.feishu.cn/open-apis',
                userinfo_endpoint='https://open.feishu.cn/open-apis/authen/v1/user_info',
                client_kwargs={
                    'scope': FEISHU_OAUTH_SCOPE,
                    **({'timeout': int(OAUTH_TIMEOUT)} if OAUTH_TIMEOUT else {}),
                },
                redirect_uri=FEISHU_REDIRECT_URI,
            )
            return client

        OAUTH_PROVIDERS['feishu'] = {
            'register': feishu_oauth_register,
            'sub_claim': 'user_id',
        }

    configured_providers = []
    if GOOGLE_CLIENT_ID:
        configured_providers.append('Google')
    if MICROSOFT_CLIENT_ID:
        configured_providers.append('Microsoft')
    if GITHUB_CLIENT_ID:
        configured_providers.append('GitHub')
    if FEISHU_CLIENT_ID:
        configured_providers.append('Feishu')

    if configured_providers and not OPENID_PROVIDER_URL and not OPENID_END_SESSION_ENDPOINT:
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

ENABLE_LDAP = os.getenv('ENABLE_LDAP', 'false').lower() == 'true'

LDAP_SERVER_LABEL = os.getenv('LDAP_SERVER_LABEL', 'LDAP Server')

LDAP_SERVER_HOST = os.getenv('LDAP_SERVER_HOST', 'localhost')

LDAP_SERVER_PORT = int(os.getenv('LDAP_SERVER_PORT', '389'))

LDAP_ATTRIBUTE_FOR_MAIL = os.getenv('LDAP_ATTRIBUTE_FOR_MAIL', 'mail')

LDAP_ATTRIBUTE_FOR_USERNAME = os.getenv('LDAP_ATTRIBUTE_FOR_USERNAME', 'uid')

LDAP_APP_DN = os.getenv('LDAP_APP_DN', '')

LDAP_APP_PASSWORD = os.getenv('LDAP_APP_PASSWORD', '')

LDAP_SEARCH_BASE = os.getenv('LDAP_SEARCH_BASE', '')

LDAP_SEARCH_FILTERS = os.getenv('LDAP_SEARCH_FILTER', os.getenv('LDAP_SEARCH_FILTERS', ''))

LDAP_USE_TLS = os.getenv('LDAP_USE_TLS', 'True').lower() == 'true'

LDAP_CA_CERT_FILE = os.getenv('LDAP_CA_CERT_FILE', '')

LDAP_VALIDATE_CERT = os.getenv('LDAP_VALIDATE_CERT', 'True').lower() == 'true'

LDAP_CIPHERS = os.getenv('LDAP_CIPHERS', 'ALL')

ENABLE_LDAP_GROUP_MANAGEMENT = os.getenv('ENABLE_LDAP_GROUP_MANAGEMENT', 'False').lower() == 'true'

ENABLE_LDAP_GROUP_CREATION = os.getenv('ENABLE_LDAP_GROUP_CREATION', 'False').lower() == 'true'

LDAP_ATTRIBUTE_FOR_GROUPS = os.getenv('LDAP_ATTRIBUTE_FOR_GROUPS', 'memberOf')

DEFAULT_CONFIG = {
    'direct.enable': ENABLE_DIRECT_CONNECTIONS,
    'ollama.enable': ENABLE_OLLAMA_API,
    'ollama.base_urls': OLLAMA_BASE_URLS,
    'ollama.api_configs': OLLAMA_API_CONFIGS,
    'openai.enable': ENABLE_OPENAI_API,
    'openai.api_keys': OPENAI_API_KEYS,
    'openai.api_base_urls': OPENAI_API_BASE_URLS,
    'openai.api_configs': OPENAI_API_CONFIGS,
    'models.base_models_cache': ENABLE_BASE_MODELS_CACHE,
    'tool_server.connections': TOOL_SERVER_CONNECTIONS,
    'oauth.client.timeout': OAUTH_CLIENT_TIMEOUT,
    'terminal_server.connections': TERMINAL_SERVER_CONNECTIONS,
    'code_execution.enable': ENABLE_CODE_EXECUTION,
    'code_execution.engine': CODE_EXECUTION_ENGINE,
    'code_execution.jupyter.url': CODE_EXECUTION_JUPYTER_URL,
    'code_execution.jupyter.auth': CODE_EXECUTION_JUPYTER_AUTH,
    'code_execution.jupyter.auth_token': CODE_EXECUTION_JUPYTER_AUTH_TOKEN,
    'code_execution.jupyter.auth_password': CODE_EXECUTION_JUPYTER_AUTH_PASSWORD,
    'code_execution.jupyter.timeout': CODE_EXECUTION_JUPYTER_TIMEOUT,
    'code_interpreter.enable': ENABLE_CODE_INTERPRETER,
    'memories.enable': ENABLE_MEMORIES,
    'memories.system_context.enable': ENABLE_MEMORY_SYSTEM_CONTEXT,
    'memories.background_review.enable': ENABLE_MEMORY_BACKGROUND_REVIEW,
    'memories.review_interval_turns': MEMORIES_REVIEW_INTERVAL_TURNS,
    'memories.user_char_limit': MEMORIES_USER_CHAR_LIMIT,
    'memories.context_char_limit': MEMORIES_CONTEXT_CHAR_LIMIT,
    'code_interpreter.engine': CODE_INTERPRETER_ENGINE,
    'code_interpreter.prompt_template': CODE_INTERPRETER_PROMPT_TEMPLATE,
    'code_interpreter.jupyter.url': CODE_INTERPRETER_JUPYTER_URL,
    'code_interpreter.jupyter.auth': CODE_INTERPRETER_JUPYTER_AUTH,
    'code_interpreter.jupyter.auth_token': CODE_INTERPRETER_JUPYTER_AUTH_TOKEN,
    'code_interpreter.jupyter.auth_password': CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD,
    'code_interpreter.jupyter.timeout': CODE_INTERPRETER_JUPYTER_TIMEOUT,
    'google_drive.enable': ENABLE_GOOGLE_DRIVE_INTEGRATION,
    'google_drive.client_id': GOOGLE_DRIVE_CLIENT_ID,
    'google_drive.api_key': GOOGLE_DRIVE_API_KEY,
    'onedrive.enable': ENABLE_ONEDRIVE_INTEGRATION,
    'onedrive.sharepoint_url': ONEDRIVE_SHAREPOINT_URL,
    'onedrive.sharepoint_tenant_id': ONEDRIVE_SHAREPOINT_TENANT_ID,
    'rag.content_extraction_engine': CONTENT_EXTRACTION_ENGINE,
    'rag.datalab_marker_api_key': DATALAB_MARKER_API_KEY,
    'rag.datalab_marker_api_base_url': DATALAB_MARKER_API_BASE_URL,
    'rag.datalab_marker_additional_config': DATALAB_MARKER_ADDITIONAL_CONFIG,
    'rag.datalab_marker_use_llm': DATALAB_MARKER_USE_LLM,
    'rag.datalab_marker_skip_cache': DATALAB_MARKER_SKIP_CACHE,
    'rag.datalab_marker_force_ocr': DATALAB_MARKER_FORCE_OCR,
    'rag.datalab_marker_paginate': DATALAB_MARKER_PAGINATE,
    'rag.datalab_marker_strip_existing_ocr': DATALAB_MARKER_STRIP_EXISTING_OCR,
    'rag.datalab_marker_disable_image_extraction': DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION,
    'rag.datalab_marker_format_lines': DATALAB_MARKER_FORMAT_LINES,
    'rag.datalab_marker_output_format': DATALAB_MARKER_OUTPUT_FORMAT,
    'rag.mineru_api_mode': MINERU_API_MODE,
    'rag.mineru_api_url': MINERU_API_URL,
    'rag.mineru_api_timeout': MINERU_API_TIMEOUT,
    'rag.mineru_api_key': MINERU_API_KEY,
    'rag.mineru_params': MINERU_PARAMS,
    'rag.mineru_file_extensions': MINERU_FILE_EXTENSIONS,
    'rag.external_document_loader_url': EXTERNAL_DOCUMENT_LOADER_URL,
    'rag.external_document_loader_api_key': EXTERNAL_DOCUMENT_LOADER_API_KEY,
    'rag.external_document_loader_headers': EXTERNAL_DOCUMENT_LOADER_HEADERS,
    'rag.tika_server_url': TIKA_SERVER_URL,
    'rag.docling_server_url': DOCLING_SERVER_URL,
    'rag.docling_api_key': DOCLING_API_KEY,
    'rag.docling_params': DOCLING_PARAMS,
    'rag.document_intelligence_endpoint': DOCUMENT_INTELLIGENCE_ENDPOINT,
    'rag.document_intelligence_key': DOCUMENT_INTELLIGENCE_KEY,
    'rag.document_intelligence_model': DOCUMENT_INTELLIGENCE_MODEL,
    'rag.mistral_ocr_api_base_url': MISTRAL_OCR_API_BASE_URL,
    'rag.mistral_ocr_api_key': MISTRAL_OCR_API_KEY,
    'rag.mistral_ocr_use_base64': MISTRAL_OCR_USE_BASE64,
    'rag.paddleocr_vl_base_url': PADDLEOCR_VL_BASE_URL,
    'rag.paddleocr_vl_token': PADDLEOCR_VL_TOKEN,
    'rag.bypass_embedding_and_retrieval': BYPASS_EMBEDDING_AND_RETRIEVAL,
    'rag.top_k': RAG_TOP_K,
    'rag.top_k_reranker': RAG_TOP_K_RERANKER,
    'rag.relevance_threshold': RAG_RELEVANCE_THRESHOLD,
    'rag.hybrid_bm25_weight': RAG_HYBRID_BM25_WEIGHT,
    'rag.enable_hybrid_search': ENABLE_RAG_HYBRID_SEARCH,
    'rag.enable_hybrid_search_enriched_texts': ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS,
    'rag.full_context': RAG_FULL_CONTEXT,
    'rag.file.max_count': RAG_FILE_MAX_COUNT,
    'rag.file.max_size': RAG_FILE_MAX_SIZE,
    'file.image_compression_width': FILE_IMAGE_COMPRESSION_WIDTH,
    'file.image_compression_height': FILE_IMAGE_COMPRESSION_HEIGHT,
    'rag.file.allowed_extensions': RAG_ALLOWED_FILE_EXTENSIONS,
    'rag.embedding_engine': RAG_EMBEDDING_ENGINE,
    'rag.pdf_extract_images': PDF_EXTRACT_IMAGES,
    'rag.pdf_loader_mode': PDF_LOADER_MODE,
    'rag.embedding_model': RAG_EMBEDDING_MODEL,
    'rag.tokenizer_model': RAG_TOKENIZER_MODEL,
    'rag.embedding_batch_size': RAG_EMBEDDING_BATCH_SIZE,
    'rag.enable_async_embedding': ENABLE_ASYNC_EMBEDDING,
    'rag.embedding_concurrent_requests': RAG_EMBEDDING_CONCURRENT_REQUESTS,
    'rag.reranking_engine': RAG_RERANKING_ENGINE,
    'rag.reranking_model': RAG_RERANKING_MODEL,
    'rag.reranking_batch_size': RAG_RERANKING_BATCH_SIZE,
    'rag.external_reranker_url': RAG_EXTERNAL_RERANKER_URL,
    'rag.external_reranker_api_key': RAG_EXTERNAL_RERANKER_API_KEY,
    'rag.external_reranker_timeout': RAG_EXTERNAL_RERANKER_TIMEOUT,
    'rag.text_splitter': RAG_TEXT_SPLITTER,
    'rag.enable_markdown_header_text_splitter': ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER,
    'rag.tiktoken_encoding_name': TIKTOKEN_ENCODING_NAME,
    'rag.chunk_size': CHUNK_SIZE,
    'rag.chunk_min_size_target': CHUNK_MIN_SIZE_TARGET,
    'rag.chunk_overlap': CHUNK_OVERLAP,
    'rag.template': RAG_TEMPLATE,
    'rag.openai.api_base_url': RAG_OPENAI_API_BASE_URL,
    'rag.openai.api_key': RAG_OPENAI_API_KEY,
    'rag.azure_openai.base_url': RAG_AZURE_OPENAI_BASE_URL,
    'rag.azure_openai.api_key': RAG_AZURE_OPENAI_API_KEY,
    'rag.azure_openai.api_version': RAG_AZURE_OPENAI_API_VERSION,
    'rag.ollama.base_url': RAG_OLLAMA_BASE_URL,
    'rag.ollama.api_key': RAG_OLLAMA_API_KEY,
    'rag.youtube_loader_language': YOUTUBE_LOADER_LANGUAGE,
    'rag.youtube_loader_proxy_url': YOUTUBE_LOADER_PROXY_URL,
    'web.search.enable': ENABLE_WEB_SEARCH,
    'web.search.confirmation.enable': ENABLE_WEB_SEARCH_CONFIRMATION,
    'web.search.confirmation.content': WEB_SEARCH_CONFIRMATION_CONTENT,
    'web.search.engine': WEB_SEARCH_ENGINE,
    'web.search.bypass_embedding_and_retrieval': BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL,
    'web.search.bypass_web_loader': BYPASS_WEB_SEARCH_WEB_LOADER,
    'web.search.result_count': WEB_SEARCH_RESULT_COUNT,
    'web.search.domain.filter_list': WEB_SEARCH_DOMAIN_FILTER_LIST,
    'web.search.concurrent_requests': WEB_SEARCH_CONCURRENT_REQUESTS,
    'web.fetch.max_content_length': WEB_FETCH_MAX_CONTENT_LENGTH,
    'web.loader.engine': WEB_LOADER_ENGINE,
    'web.loader.concurrent_requests': WEB_LOADER_CONCURRENT_REQUESTS,
    'web.loader.timeout': WEB_LOADER_TIMEOUT,
    'web.loader.ssl_verification': ENABLE_WEB_LOADER_SSL_VERIFICATION,
    'web.search.trust_env': WEB_SEARCH_TRUST_ENV,
    'web.search.ollama_cloud_api_key': OLLAMA_CLOUD_WEB_SEARCH_API_KEY,
    'web.search.searxng_query_url': SEARXNG_QUERY_URL,
    'web.search.searxng_language': SEARXNG_LANGUAGE,
    'web.search.yacy_query_url': YACY_QUERY_URL,
    'web.search.yacy_username': YACY_USERNAME,
    'web.search.yacy_password': YACY_PASSWORD,
    'web.search.google_pse_api_key': GOOGLE_PSE_API_KEY,
    'web.search.google_pse_engine_id': GOOGLE_PSE_ENGINE_ID,
    'web.search.brave_search_api_key': BRAVE_SEARCH_API_KEY,
    'web.search.brave_search_context_tokens': BRAVE_SEARCH_CONTEXT_TOKENS,
    'web.search.kagi_search_api_key': KAGI_SEARCH_API_KEY,
    'web.search.mojeek_search_api_key': MOJEEK_SEARCH_API_KEY,
    'web.search.bocha_search_api_key': BOCHA_SEARCH_API_KEY,
    'web.search.serpstack_api_key': SERPSTACK_API_KEY,
    'web.search.serpstack_https': SERPSTACK_HTTPS,
    'web.search.serper_api_key': SERPER_API_KEY,
    'web.search.serply_api_key': SERPLY_API_KEY,
    'web.search.serphouse_api_key': SERPHOUSE_API_KEY,
    'web.search.serphouse_domain': SERPHOUSE_DOMAIN,
    'web.search.ddgs_backend': DDGS_BACKEND,
    'web.search.jina_api_key': JINA_API_KEY,
    'web.search.jina_api_base_url': JINA_API_BASE_URL,
    'web.search.searchapi_api_key': SEARCHAPI_API_KEY,
    'web.search.searchapi_engine': SEARCHAPI_ENGINE,
    'web.search.serpapi_api_key': SERPAPI_API_KEY,
    'web.search.serpapi_engine': SERPAPI_ENGINE,
    'web.search.bing_search_v7_endpoint': BING_SEARCH_V7_ENDPOINT,
    'web.search.bing_search_v7_subscription_key': BING_SEARCH_V7_SUBSCRIPTION_KEY,
    'web.search.azure_ai_search_api_key': AZURE_AI_SEARCH_API_KEY,
    'web.search.azure_ai_search_endpoint': AZURE_AI_SEARCH_ENDPOINT,
    'web.search.azure_ai_search_index_name': AZURE_AI_SEARCH_INDEX_NAME,
    'web.search.exa_api_key': EXA_API_KEY,
    'web.search.perplexity_api_key': PERPLEXITY_API_KEY,
    'web.search.perplexity_model': PERPLEXITY_MODEL,
    'web.search.perplexity_search_context_usage': PERPLEXITY_SEARCH_CONTEXT_USAGE,
    'web.search.perplexity_search_api_url': PERPLEXITY_SEARCH_API_URL,
    'web.search.microsoft_web_iq_api_base_url': MICROSOFT_WEB_IQ_API_BASE_URL,
    'web.search.microsoft_web_iq_api_key': MICROSOFT_WEB_IQ_API_KEY,
    'web.search.microsoft_web_iq_language': MICROSOFT_WEB_IQ_LANGUAGE,
    'web.search.sougou_api_sid': SOUGOU_API_SID,
    'web.search.sougou_api_sk': SOUGOU_API_SK,
    'web.search.tavily_api_key': TAVILY_API_KEY,
    'web.search.tavily_extract_depth': TAVILY_EXTRACT_DEPTH,
    'web.loader.playwright_ws_url': PLAYWRIGHT_WS_URL,
    'web.loader.playwright_timeout': PLAYWRIGHT_TIMEOUT,
    'web.loader.firecrawl_api_key': FIRECRAWL_API_KEY,
    'web.loader.firecrawl_api_url': FIRECRAWL_API_BASE_URL,
    'web.loader.firecrawl_timeout': FIRECRAWL_TIMEOUT,
    'web.search.external_web_search_url': EXTERNAL_WEB_SEARCH_URL,
    'web.search.external_web_search_api_key': EXTERNAL_WEB_SEARCH_API_KEY,
    'web.loader.external_web_loader_url': EXTERNAL_WEB_LOADER_URL,
    'web.loader.external_web_loader_api_key': EXTERNAL_WEB_LOADER_API_KEY,
    'web.search.yandex_web_search_url': YANDEX_WEB_SEARCH_URL,
    'web.search.yandex_web_search_api_key': YANDEX_WEB_SEARCH_API_KEY,
    'web.search.yandex_web_search_config': YANDEX_WEB_SEARCH_CONFIG,
    'web.search.youcom_api_key': YOUCOM_API_KEY,
    'web.search.linkup_api_key': LINKUP_API_KEY,
    'web.search.linkup_search_params': LINKUP_SEARCH_PARAMS,
    'image_generation.enable': ENABLE_IMAGE_GENERATION,
    'image_generation.engine': IMAGE_GENERATION_ENGINE,
    'image_generation.model': IMAGE_GENERATION_MODEL,
    'image_generation.size': IMAGE_SIZE,
    'image_generation.steps': IMAGE_STEPS,
    'image_generation.prompt.enable': ENABLE_IMAGE_PROMPT_GENERATION,
    'image_generation.automatic1111.base_url': AUTOMATIC1111_BASE_URL,
    'image_generation.automatic1111.api_auth': AUTOMATIC1111_API_AUTH,
    'image_generation.automatic1111.api_params': AUTOMATIC1111_PARAMS,
    'image_generation.comfyui.base_url': COMFYUI_BASE_URL,
    'image_generation.comfyui.api_key': COMFYUI_API_KEY,
    'image_generation.comfyui.workflow': COMFYUI_WORKFLOW,
    'image_generation.comfyui.nodes': COMFYUI_WORKFLOW_NODES,
    'image_generation.openai.api_base_url': IMAGES_OPENAI_API_BASE_URL,
    'image_generation.openai.api_version': IMAGES_OPENAI_API_VERSION,
    'image_generation.openai.api_key': IMAGES_OPENAI_API_KEY,
    'image_generation.openai.params': IMAGES_OPENAI_API_PARAMS,
    'image_generation.gemini.api_base_url': IMAGES_GEMINI_API_BASE_URL,
    'image_generation.gemini.api_key': IMAGES_GEMINI_API_KEY,
    'image_generation.gemini.endpoint_method': IMAGES_GEMINI_ENDPOINT_METHOD,
    'images.edit.enable': ENABLE_IMAGE_EDIT,
    'images.edit.engine': IMAGE_EDIT_ENGINE,
    'images.edit.model': IMAGE_EDIT_MODEL,
    'images.edit.size': IMAGE_EDIT_SIZE,
    'images.edit.openai.api_base_url': IMAGES_EDIT_OPENAI_API_BASE_URL,
    'images.edit.openai.api_version': IMAGES_EDIT_OPENAI_API_VERSION,
    'images.edit.openai.api_key': IMAGES_EDIT_OPENAI_API_KEY,
    'images.edit.gemini.api_base_url': IMAGES_EDIT_GEMINI_API_BASE_URL,
    'images.edit.gemini.api_key': IMAGES_EDIT_GEMINI_API_KEY,
    'images.edit.comfyui.base_url': IMAGES_EDIT_COMFYUI_BASE_URL,
    'images.edit.comfyui.api_key': IMAGES_EDIT_COMFYUI_API_KEY,
    'images.edit.comfyui.workflow': IMAGES_EDIT_COMFYUI_WORKFLOW,
    'images.edit.comfyui.nodes': IMAGES_EDIT_COMFYUI_WORKFLOW_NODES,
    'audio.stt.whisper_model': WHISPER_MODEL,
    'audio.stt.deepgram.api_key': DEEPGRAM_API_KEY,
    'audio.stt.openai.api_base_url': AUDIO_STT_OPENAI_API_BASE_URL,
    'audio.stt.openai.api_key': AUDIO_STT_OPENAI_API_KEY,
    'audio.stt.openai.api_request_format': AUDIO_STT_OPENAI_API_REQUEST_FORMAT,
    'audio.stt.engine': AUDIO_STT_ENGINE,
    'audio.stt.model': AUDIO_STT_MODEL,
    'audio.stt.supported_content_types': AUDIO_STT_SUPPORTED_CONTENT_TYPES,
    'audio.stt.allowed_extensions': AUDIO_STT_ALLOWED_EXTENSIONS,
    'audio.stt.azure.api_key': AUDIO_STT_AZURE_API_KEY,
    'audio.stt.azure.region': AUDIO_STT_AZURE_REGION,
    'audio.stt.azure.locales': AUDIO_STT_AZURE_LOCALES,
    'audio.stt.azure.base_url': AUDIO_STT_AZURE_BASE_URL,
    'audio.stt.azure.max_speakers': AUDIO_STT_AZURE_MAX_SPEAKERS,
    'audio.stt.mistral.api_key': AUDIO_STT_MISTRAL_API_KEY,
    'audio.stt.mistral.api_base_url': AUDIO_STT_MISTRAL_API_BASE_URL,
    'audio.stt.mistral.use_chat_completions': AUDIO_STT_MISTRAL_USE_CHAT_COMPLETIONS,
    'audio.tts.openai.api_base_url': AUDIO_TTS_OPENAI_API_BASE_URL,
    'audio.tts.openai.api_key': AUDIO_TTS_OPENAI_API_KEY,
    'audio.tts.openai.params': AUDIO_TTS_OPENAI_PARAMS,
    'audio.tts.api_key': AUDIO_TTS_API_KEY,
    'audio.tts.engine': AUDIO_TTS_ENGINE,
    'audio.tts.model': AUDIO_TTS_MODEL,
    'audio.tts.voice': AUDIO_TTS_VOICE,
    'audio.tts.split_on': AUDIO_TTS_SPLIT_ON,
    'audio.tts.azure.speech_region': AUDIO_TTS_AZURE_SPEECH_REGION,
    'audio.tts.azure.speech_base_url': AUDIO_TTS_AZURE_SPEECH_BASE_URL,
    'audio.tts.azure.speech_output_format': AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT,
    'audio.tts.mistral.api_key': AUDIO_TTS_MISTRAL_API_KEY,
    'audio.tts.mistral.api_base_url': AUDIO_TTS_MISTRAL_API_BASE_URL,
    'webui.url': WEBUI_URL,
    'ui.enable_signup': ENABLE_SIGNUP,
    'ui.enable_login_form': ENABLE_LOGIN_FORM,
    'ui.enable_password_change_form': ENABLE_PASSWORD_CHANGE_FORM,
    'ui.default_locale': DEFAULT_LOCALE,
    'ui.default_models': DEFAULT_MODELS,
    'ui.default_pinned_models': DEFAULT_PINNED_MODELS,
    'ui.prompt_suggestions': DEFAULT_PROMPT_SUGGESTIONS,
    'ui.model_order_list': MODEL_ORDER_LIST,
    'models.default_metadata': DEFAULT_MODEL_METADATA,
    'models.default_params': DEFAULT_MODEL_PARAMS,
    'ui.default_user_role': DEFAULT_USER_ROLE,
    'ui.default_group_id': DEFAULT_GROUP_ID,
    'ui.pending_user_overlay_title': PENDING_USER_OVERLAY_TITLE,
    'ui.pending_user_overlay_content': PENDING_USER_OVERLAY_CONTENT,
    'ui.watermark': RESPONSE_WATERMARK,
    'user.permissions': USER_PERMISSIONS,
    'folders.enable': ENABLE_FOLDERS,
    'folders.max_file_count': FOLDER_MAX_FILE_COUNT,
    'channels.enable': ENABLE_CHANNELS,
    'calendar.enable': ENABLE_CALENDAR,
    'automations.enable': ENABLE_AUTOMATIONS,
    'automations.max_count': AUTOMATION_MAX_COUNT,
    'automations.min_interval': AUTOMATION_MIN_INTERVAL,
    'automations.auth_token_expires_in': AUTOMATION_AUTH_TOKEN_EXPIRES_IN,
    'notes.enable': ENABLE_NOTES,
    'users.enable_status': ENABLE_USER_STATUS,
    'evaluation.arena.enable': ENABLE_EVALUATION_ARENA_MODELS,
    'evaluation.arena.models': EVALUATION_ARENA_MODELS,
    'webhook_url': WEBHOOK_URL,
    'ui.enable_community_sharing': ENABLE_COMMUNITY_SHARING,
    'ui.enable_message_rating': ENABLE_MESSAGE_RATING,
    'ui.enable_user_webhooks': ENABLE_USER_WEBHOOKS,
    'ui.banners': WEBUI_BANNERS,
    'auth.admin.show': SHOW_ADMIN_DETAILS,
    'auth.admin.email': ADMIN_EMAIL,
    'task.model.default': TASK_MODEL,
    'task.model.external': TASK_MODEL_EXTERNAL,
    'chat.context_compaction.enable': ENABLE_CONTEXT_COMPACTION,
    'chat.context_compaction.token_threshold': CONTEXT_COMPACTION_TOKEN_THRESHOLD,
    'chat.context_compaction.prompt_template': CONTEXT_COMPACTION_PROMPT_TEMPLATE,
    'task.title.prompt_template': TITLE_GENERATION_PROMPT_TEMPLATE,
    'task.tags.prompt_template': TAGS_GENERATION_PROMPT_TEMPLATE,
    'task.image.prompt_template': IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE,
    'task.follow_up.prompt_template': FOLLOW_UP_GENERATION_PROMPT_TEMPLATE,
    'task.follow_up.enable': ENABLE_FOLLOW_UP_GENERATION,
    'task.tags.enable': ENABLE_TAGS_GENERATION,
    'task.title.enable': ENABLE_TITLE_GENERATION,
    'task.query.search.enable': ENABLE_SEARCH_QUERY_GENERATION,
    'task.query.retrieval.enable': ENABLE_RETRIEVAL_QUERY_GENERATION,
    'task.query.prompt_template': QUERY_GENERATION_PROMPT_TEMPLATE,
    'task.autocomplete.enable': ENABLE_AUTOCOMPLETE_GENERATION,
    'task.autocomplete.input_max_length': AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH,
    'task.autocomplete.prompt_template': AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE,
    'task.voice.prompt_template': VOICE_MODE_PROMPT_TEMPLATE,
    'task.voice.prompt.enable': ENABLE_VOICE_MODE_PROMPT,
    'task.tools.prompt_template': TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    'auth.enable_api_keys': ENABLE_API_KEYS,
    'auth.api_key.endpoint_restrictions': ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS,
    'auth.api_key.allowed_endpoints': API_KEYS_ALLOWED_ENDPOINTS,
    'auth.jwt_expiry': JWT_EXPIRES_IN,
    'oauth.enable_signup': ENABLE_OAUTH_SIGNUP,
    'oauth.auto_redirect': OAUTH_AUTO_REDIRECT,
    'oauth.refresh_token.include_scope': OAUTH_REFRESH_TOKEN_INCLUDE_SCOPE,
    'oauth.merge_accounts_by_email': OAUTH_MERGE_ACCOUNTS_BY_EMAIL,
    'oauth.google.client_id': GOOGLE_CLIENT_ID,
    'oauth.google.client_secret': GOOGLE_CLIENT_SECRET,
    'oauth.google.scope': GOOGLE_OAUTH_SCOPE,
    'oauth.google.redirect_uri': GOOGLE_REDIRECT_URI,
    'oauth.microsoft.client_id': MICROSOFT_CLIENT_ID,
    'oauth.microsoft.client_secret': MICROSOFT_CLIENT_SECRET,
    'oauth.microsoft.tenant_id': MICROSOFT_CLIENT_TENANT_ID,
    'oauth.microsoft.login_base_url': MICROSOFT_CLIENT_LOGIN_BASE_URL,
    'oauth.microsoft.picture_url': MICROSOFT_CLIENT_PICTURE_URL,
    'oauth.microsoft.scope': MICROSOFT_OAUTH_SCOPE,
    'oauth.microsoft.redirect_uri': MICROSOFT_REDIRECT_URI,
    'oauth.github.client_id': GITHUB_CLIENT_ID,
    'oauth.github.client_secret': GITHUB_CLIENT_SECRET,
    'oauth.github.scope': GITHUB_CLIENT_SCOPE,
    'oauth.github.redirect_uri': GITHUB_CLIENT_REDIRECT_URI,
    'oauth.client_id': OAUTH_CLIENT_ID,
    'oauth.client_secret': OAUTH_CLIENT_SECRET,
    'oauth.provider_url': OPENID_PROVIDER_URL,
    'oauth.end_session_endpoint': OPENID_END_SESSION_ENDPOINT,
    'oauth.redirect_uri': OPENID_REDIRECT_URI,
    'oauth.scopes': OAUTH_SCOPES,
    'oauth.timeout': OAUTH_TIMEOUT,
    'oauth.token_endpoint_auth_method': OAUTH_TOKEN_ENDPOINT_AUTH_METHOD,
    'oauth.code_challenge_method': OAUTH_CODE_CHALLENGE_METHOD,
    'oauth.provider_name': OAUTH_PROVIDER_NAME,
    'oauth.sub_claim': OAUTH_SUB_CLAIM,
    'oauth.username_claim': OAUTH_USERNAME_CLAIM,
    'oauth.picture_claim': OAUTH_PICTURE_CLAIM,
    'oauth.email_claim': OAUTH_EMAIL_CLAIM,
    'oauth.group_claim': OAUTH_GROUPS_CLAIM,
    'oauth.feishu.client_id': FEISHU_CLIENT_ID,
    'oauth.feishu.client_secret': FEISHU_CLIENT_SECRET,
    'oauth.feishu.scope': FEISHU_OAUTH_SCOPE,
    'oauth.feishu.redirect_uri': FEISHU_REDIRECT_URI,
    'oauth.enable_role_mapping': ENABLE_OAUTH_ROLE_MANAGEMENT,
    'oauth.enable_group_mapping': ENABLE_OAUTH_GROUP_MANAGEMENT,
    'oauth.enable_group_creation': ENABLE_OAUTH_GROUP_CREATION,
    'oauth.group_default_share': OAUTH_GROUP_DEFAULT_SHARE,
    'oauth.blocked_groups': OAUTH_BLOCKED_GROUPS,
    'oauth.roles_claim': OAUTH_ROLES_CLAIM,
    'oauth.allowed_roles': OAUTH_ALLOWED_ROLES,
    'oauth.admin_roles': OAUTH_ADMIN_ROLES,
    'oauth.allowed_domains': OAUTH_ALLOWED_DOMAINS,
    'oauth.update_picture_on_login': OAUTH_UPDATE_PICTURE_ON_LOGIN,
    'oauth.update_name_on_login': OAUTH_UPDATE_NAME_ON_LOGIN,
    'oauth.update_email_on_login': OAUTH_UPDATE_EMAIL_ON_LOGIN,
    'oauth.audience': OAUTH_AUDIENCE,
    'ldap.enable': ENABLE_LDAP,
    'ldap.server.label': LDAP_SERVER_LABEL,
    'ldap.server.host': LDAP_SERVER_HOST,
    'ldap.server.port': LDAP_SERVER_PORT,
    'ldap.server.attribute_for_mail': LDAP_ATTRIBUTE_FOR_MAIL,
    'ldap.server.attribute_for_username': LDAP_ATTRIBUTE_FOR_USERNAME,
    'ldap.server.app_dn': LDAP_APP_DN,
    'ldap.server.app_password': LDAP_APP_PASSWORD,
    'ldap.server.users_dn': LDAP_SEARCH_BASE,
    'ldap.server.search_filter': LDAP_SEARCH_FILTERS,
    'ldap.server.use_tls': LDAP_USE_TLS,
    'ldap.server.ca_cert_file': LDAP_CA_CERT_FILE,
    'ldap.server.validate_cert': LDAP_VALIDATE_CERT,
    'ldap.server.ciphers': LDAP_CIPHERS,
    'ldap.group.enable_management': ENABLE_LDAP_GROUP_MANAGEMENT,
    'ldap.group.enable_creation': ENABLE_LDAP_GROUP_CREATION,
    'ldap.server.attribute_for_groups': LDAP_ATTRIBUTE_FOR_GROUPS,
}


ENABLE_PERSISTENT_CONFIG = os.getenv('ENABLE_PERSISTENT_CONFIG', 'True').lower() == 'true'
ENABLE_OAUTH_PERSISTENT_CONFIG = os.getenv('ENABLE_OAUTH_PERSISTENT_CONFIG', 'False').lower() == 'true'

Config.configure(
    defaults=DEFAULT_CONFIG,
    enable_persistent=ENABLE_PERSISTENT_CONFIG,
    enable_oauth_persistent=ENABLE_OAUTH_PERSISTENT_CONFIG,
)

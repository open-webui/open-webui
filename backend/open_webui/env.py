import datetime as dt
import importlib.metadata
import json
import logging
import os
import pkgutil
import re
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import markdown
from bs4 import BeautifulSoup
from cryptography.hazmat.primitives import serialization

from open_webui.constants import ERROR_MESSAGES

####################################
# Load .env file
####################################

# Use .resolve() to get the canonical path, removing any '..' or '.' components
ENV_FILE_PATH = Path(__file__).resolve()

# OPEN_WEBUI_DIR should be the directory where env.py resides (open_webui/)
OPEN_WEBUI_DIR = ENV_FILE_PATH.parent

# BACKEND_DIR is the parent of OPEN_WEBUI_DIR (backend/)
BACKEND_DIR = OPEN_WEBUI_DIR.parent

# BASE_DIR is the parent of BACKEND_DIR (open-webui-dev/)
BASE_DIR = BACKEND_DIR.parent

try:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(str(BASE_DIR / '.env')))
except ImportError:
    print('dotenv not installed, skipping...')

DOCKER = os.getenv('DOCKER', 'False').lower() == 'true'

USE_CUDA = os.getenv('USE_CUDA_DOCKER', 'false')
DEVICE_TYPE = 'cpu'
_cuda_error: Optional[str] = None

if USE_CUDA.lower() == 'true':
    try:
        import torch  # noqa: E402

        if not torch.cuda.is_available():
            raise RuntimeError('CUDA not available')
        DEVICE_TYPE = 'cuda'
    except Exception as exc:
        _cuda_error = f'CUDA unavailable (USE_CUDA_DOCKER=true), falling back to CPU: {exc}'
        os.environ['USE_CUDA_DOCKER'] = 'false'
        USE_CUDA = 'false'

if sys.platform == 'darwin' and DEVICE_TYPE == 'cpu':
    try:
        import torch  # noqa: E402

        if torch.backends.mps.is_available() and torch.backends.mps.is_built():
            DEVICE_TYPE = 'mps'
    except Exception:
        pass

####################################
# LOGGING
####################################

_LEVEL_MAP = {
    'DEBUG': 'debug',
    'INFO': 'info',
    'WARNING': 'warn',
    'ERROR': 'error',
    'CRITICAL': 'fatal',
}


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            'ts': dt.datetime.fromtimestamp(record.created, tz=dt.UTC).isoformat(timespec='milliseconds'),
            'level': _LEVEL_MAP.get(record.levelname, record.levelname.lower()),
            'msg': record.getMessage(),
            'caller': record.name,
        }

        if record.exc_info and record.exc_info[0] is not None:
            log_entry['error'] = ''.join(traceback.format_exception(*record.exc_info)).rstrip()
        elif record.exc_text:
            log_entry['error'] = record.exc_text

        if record.stack_info:
            log_entry['stacktrace'] = record.stack_info

        return json.dumps(log_entry, ensure_ascii=False, default=str)


LOG_FORMAT = os.getenv('LOG_FORMAT', '').lower()

GLOBAL_LOG_LEVEL = os.getenv('GLOBAL_LOG_LEVEL', '').upper()
if GLOBAL_LOG_LEVEL in logging.getLevelNamesMapping():
    _log_cfg: dict[str, Any] = {'level': GLOBAL_LOG_LEVEL, 'force': True}
    if LOG_FORMAT == 'json':
        _json_handler = logging.StreamHandler(sys.stdout)
        _json_handler.setFormatter(JSONFormatter())
        _log_cfg['handlers'] = [_json_handler]
    else:
        _log_cfg['stream'] = sys.stdout
    logging.basicConfig(**_log_cfg)
else:
    GLOBAL_LOG_LEVEL = 'INFO'

log = logging.getLogger(__name__)
log.info('GLOBAL_LOG_LEVEL: %s', GLOBAL_LOG_LEVEL)

if _cuda_error:
    log.error(_cuda_error)
    _cuda_error = None

SRC_LOG_LEVELS = {}  # Legacy variable, do not remove

####################################
# ENV (dev,test,prod)
####################################

ENV = os.getenv('ENV', 'dev')

FROM_INIT_PY = os.getenv('FROM_INIT_PY', 'False').lower() == 'true'

if FROM_INIT_PY:
    PACKAGE_DATA = {'version': importlib.metadata.version('open-webui')}
else:
    try:
        PACKAGE_DATA = json.loads((BASE_DIR / 'package.json').read_text())
    except Exception:
        PACKAGE_DATA = {'version': '0.0.0'}

VERSION = PACKAGE_DATA['version']


DEPLOYMENT_ID = os.getenv('DEPLOYMENT_ID', '')
INSTANCE_ID = os.getenv('INSTANCE_ID', str(uuid4()))

ENABLE_DB_MIGRATIONS = os.getenv('ENABLE_DB_MIGRATIONS', 'True').lower() == 'true'


# Function to parse each section
def parse_section(section):
    items = []
    for li in section.find_all('li'):
        # Extract raw HTML string
        raw_html = str(li)

        # Extract text without HTML tags
        text = li.get_text(separator=' ', strip=True)

        # Split into title and content
        parts = text.split(': ', 1)
        title = parts[0].strip() if len(parts) > 1 else ''
        content = parts[1].strip() if len(parts) > 1 else text

        items.append({'title': title, 'content': content, 'raw': raw_html})
    return items


try:
    changelog_path = BASE_DIR / 'CHANGELOG.md'
    with open(str(changelog_path.absolute()), encoding='utf8') as file:
        changelog_content = file.read()

except Exception:
    changelog_content = (pkgutil.get_data('open_webui', 'CHANGELOG.md') or b'').decode()

# Convert markdown content to HTML
html_content = markdown.markdown(changelog_content)

# Parse the HTML content
soup = BeautifulSoup(html_content, 'html.parser')

# Initialize JSON structure
changelog_json = {}

# Iterate over each version
for version in soup.find_all('h2'):
    version_number = version.get_text().strip().split(' - ')[0][1:-1]  # Remove brackets
    date = version.get_text().strip().split(' - ')[1]

    version_data = {'date': date}

    # Find the next sibling that is a h3 tag (section title)
    current = version.find_next_sibling()

    while current and current.name != 'h2':
        if current.name == 'h3':
            section_title = current.get_text().lower()  # e.g., "added", "fixed"
            section_items = parse_section(current.find_next_sibling('ul'))
            version_data[section_title] = section_items

        # Move to the next element
        current = current.find_next_sibling()

    changelog_json[version_number] = version_data

CHANGELOG = changelog_json

####################################
# DATA/FRONTEND BUILD DIR
####################################

DATA_DIR = Path(os.getenv('DATA_DIR', BACKEND_DIR / 'data')).resolve()

if FROM_INIT_PY:
    NEW_DATA_DIR = Path(os.getenv('DATA_DIR', OPEN_WEBUI_DIR / 'data')).resolve()
    NEW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Check if the data directory exists in the package directory
    if DATA_DIR.exists() and DATA_DIR != NEW_DATA_DIR:
        log.info(f'Moving {DATA_DIR} to {NEW_DATA_DIR}')
        for item in DATA_DIR.iterdir():
            dest = NEW_DATA_DIR / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

        # Zip the data directory
        shutil.make_archive(DATA_DIR.parent / 'open_webui_data', 'zip', DATA_DIR)

        # Remove the old data directory
        shutil.rmtree(DATA_DIR)

    DATA_DIR = Path(os.getenv('DATA_DIR', OPEN_WEBUI_DIR / 'data'))

STATIC_DIR = Path(os.getenv('STATIC_DIR', OPEN_WEBUI_DIR / 'static'))

FONTS_DIR = Path(os.getenv('FONTS_DIR', OPEN_WEBUI_DIR / 'static' / 'fonts'))

FRONTEND_BUILD_DIR = Path(os.getenv('FRONTEND_BUILD_DIR', BASE_DIR / 'build')).resolve()

if FROM_INIT_PY:
    FRONTEND_BUILD_DIR = Path(os.getenv('FRONTEND_BUILD_DIR', OPEN_WEBUI_DIR / 'frontend')).resolve()

####################################
# Database
####################################

# Check if the file exists
if os.path.exists(f'{DATA_DIR}/ollama.db'):
    # Rename the file
    os.rename(f'{DATA_DIR}/ollama.db', f'{DATA_DIR}/webui.db')
    log.info('Database migrated from Ollama-WebUI successfully.')
else:
    pass

DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DATA_DIR}/webui.db')

DATABASE_TYPE = os.getenv('DATABASE_TYPE')
DATABASE_USER = os.getenv('DATABASE_USER')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')

DATABASE_CRED = ''
if DATABASE_USER:
    DATABASE_CRED += f'{DATABASE_USER}'
if DATABASE_PASSWORD:
    DATABASE_CRED += f':{DATABASE_PASSWORD}'

DB_VARS = {
    'db_type': DATABASE_TYPE,
    'db_cred': DATABASE_CRED,
    'db_host': os.getenv('DATABASE_HOST'),
    'db_port': os.getenv('DATABASE_PORT'),
    'db_name': os.getenv('DATABASE_NAME'),
}

if all(DB_VARS.values()):
    DATABASE_URL = (
        f'{DB_VARS["db_type"]}://{DB_VARS["db_cred"]}@{DB_VARS["db_host"]}:{DB_VARS["db_port"]}/{DB_VARS["db_name"]}'
    )
elif DATABASE_TYPE == 'sqlite+sqlcipher' and not os.getenv('DATABASE_URL'):
    # Handle SQLCipher with local file when DATABASE_URL wasn't explicitly set
    DATABASE_URL = f'sqlite+sqlcipher:///{DATA_DIR}/webui.db'

# Replace the postgres:// with postgresql://
if 'postgres://' in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://')

DATABASE_SCHEMA = os.getenv('DATABASE_SCHEMA', None)

_pool_size_raw = os.getenv('DATABASE_POOL_SIZE')
try:
    DATABASE_POOL_SIZE = int(_pool_size_raw) if _pool_size_raw else None
except (ValueError, TypeError):
    DATABASE_POOL_SIZE = None

_pool_overflow_raw = os.getenv('DATABASE_POOL_MAX_OVERFLOW', '0')
try:
    DATABASE_POOL_MAX_OVERFLOW = int(_pool_overflow_raw) if _pool_overflow_raw else 0
except (ValueError, TypeError):
    DATABASE_POOL_MAX_OVERFLOW = 0

_pool_timeout_raw = os.getenv('DATABASE_POOL_TIMEOUT', '30')
try:
    DATABASE_POOL_TIMEOUT = int(_pool_timeout_raw) if _pool_timeout_raw else 30
except (ValueError, TypeError):
    DATABASE_POOL_TIMEOUT = 30

_pool_recycle_raw = os.getenv('DATABASE_POOL_RECYCLE', '3600')
try:
    DATABASE_POOL_RECYCLE = int(_pool_recycle_raw) if _pool_recycle_raw else 3600
except (ValueError, TypeError):
    DATABASE_POOL_RECYCLE = 3600

DATABASE_ENABLE_SQLITE_WAL = os.getenv('DATABASE_ENABLE_SQLITE_WAL', 'True').lower() == 'true'

# SQLite PRAGMA tuning — these defaults are optimised for WAL-mode web-server
# workloads.  Each can be overridden via its environment variable.
# Set any value to an empty string to skip that PRAGMA entirely.

# PRAGMA synchronous: NORMAL (1) is safe with WAL and avoids an fsync per
# transaction.  Valid values: OFF (0), NORMAL (1), FULL (2), EXTRA (3).
DATABASE_SQLITE_PRAGMA_SYNCHRONOUS = os.getenv('DATABASE_SQLITE_PRAGMA_SYNCHRONOUS', 'NORMAL')

# PRAGMA busy_timeout (ms): how long a connection waits for a write lock
# before raising SQLITE_BUSY.
DATABASE_SQLITE_PRAGMA_BUSY_TIMEOUT = os.getenv('DATABASE_SQLITE_PRAGMA_BUSY_TIMEOUT', '5000')

# PRAGMA cache_size: negative value = KiB.  -65536 ≈ 64 MB page cache.
DATABASE_SQLITE_PRAGMA_CACHE_SIZE = os.getenv('DATABASE_SQLITE_PRAGMA_CACHE_SIZE', '-65536')

# PRAGMA temp_store: MEMORY (2) keeps temp tables and indices in RAM.
# Valid values: DEFAULT (0), FILE (1), MEMORY (2).
DATABASE_SQLITE_PRAGMA_TEMP_STORE = os.getenv('DATABASE_SQLITE_PRAGMA_TEMP_STORE', 'MEMORY')

# PRAGMA mmap_size (bytes): memory-mapped I/O size.  268435456 ≈ 256 MB.
# Set to 0 to disable mmap.
DATABASE_SQLITE_PRAGMA_MMAP_SIZE = os.getenv('DATABASE_SQLITE_PRAGMA_MMAP_SIZE', '268435456')

# PRAGMA journal_size_limit (bytes): caps the WAL file size after checkpoint.
# Without this the WAL grows unbounded during write bursts and is never
# truncated.  67108864 ≈ 64 MB.  Set to -1 for no limit (SQLite default).
DATABASE_SQLITE_PRAGMA_JOURNAL_SIZE_LIMIT = os.getenv('DATABASE_SQLITE_PRAGMA_JOURNAL_SIZE_LIMIT', '67108864')

DATABASE_USER_ACTIVE_STATUS_UPDATE_INTERVAL = os.getenv('DATABASE_USER_ACTIVE_STATUS_UPDATE_INTERVAL', None)
if DATABASE_USER_ACTIVE_STATUS_UPDATE_INTERVAL is not None:
    try:
        DATABASE_USER_ACTIVE_STATUS_UPDATE_INTERVAL = float(DATABASE_USER_ACTIVE_STATUS_UPDATE_INTERVAL)
    except Exception:
        DATABASE_USER_ACTIVE_STATUS_UPDATE_INTERVAL = 0.0

DATABASE_ENABLE_SESSION_SHARING = os.getenv('DATABASE_ENABLE_SESSION_SHARING', 'False').lower() == 'true'
ENABLE_PUBLIC_ACTIVE_USERS_COUNT = os.getenv('ENABLE_PUBLIC_ACTIVE_USERS_COUNT', 'True').lower() == 'true'
RESET_CONFIG_ON_START = os.getenv('RESET_CONFIG_ON_START', 'False').lower() == 'true'
ENABLE_REALTIME_CHAT_SAVE = os.getenv('ENABLE_REALTIME_CHAT_SAVE', 'False').lower() == 'true'
ENABLE_QUERIES_CACHE = os.getenv('ENABLE_QUERIES_CACHE', 'False').lower() == 'true'
RAG_SYSTEM_CONTEXT = os.getenv('RAG_SYSTEM_CONTEXT', 'False').lower() == 'true'

####################################
# REDIS
####################################

REDIS_URL = os.getenv('REDIS_URL', '')
REDIS_CLUSTER = os.getenv('REDIS_CLUSTER', 'False').lower() == 'true'

REDIS_KEY_PREFIX = os.getenv('REDIS_KEY_PREFIX', 'open-webui')

REDIS_SENTINEL_HOSTS = os.getenv('REDIS_SENTINEL_HOSTS', '')
REDIS_SENTINEL_PORT = os.getenv('REDIS_SENTINEL_PORT', '26379')

# Maximum number of retries for Redis operations when using Sentinel fail-over
REDIS_SENTINEL_MAX_RETRY_COUNT = os.getenv('REDIS_SENTINEL_MAX_RETRY_COUNT', '2')
try:
    REDIS_SENTINEL_MAX_RETRY_COUNT = int(REDIS_SENTINEL_MAX_RETRY_COUNT)
    if REDIS_SENTINEL_MAX_RETRY_COUNT < 1:
        REDIS_SENTINEL_MAX_RETRY_COUNT = 2
except ValueError:
    REDIS_SENTINEL_MAX_RETRY_COUNT = 2


REDIS_SOCKET_CONNECT_TIMEOUT = os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', '')
try:
    REDIS_SOCKET_CONNECT_TIMEOUT = float(REDIS_SOCKET_CONNECT_TIMEOUT)
except ValueError:
    REDIS_SOCKET_CONNECT_TIMEOUT = None

# Whether to enable TCP SO_KEEPALIVE on Redis client sockets. Opt-in:
# defaults to off so behavior is unchanged for existing deployments. When
# enabled, the kernel sends TCP keepalive probes on idle connections so
# half-closed sockets (e.g. after a silent firewall/LB reset or a NIC
# flap) are detected before the next command lands on them.
REDIS_SOCKET_KEEPALIVE = os.getenv('REDIS_SOCKET_KEEPALIVE', 'False').lower() == 'true'

# How often (in seconds) redis-py should PING an idle pooled connection
# before reusing it. Opt-in: defaults to unset (empty string) so behavior
# is unchanged for existing deployments. When set, should be shorter than
# the Redis server `timeout` setting and any firewall/LB idle timeout on
# the path to Redis, so stale connections are detected before a real
# command lands on them. Set to 0 or empty to disable.
REDIS_HEALTH_CHECK_INTERVAL = os.getenv('REDIS_HEALTH_CHECK_INTERVAL', '')
try:
    REDIS_HEALTH_CHECK_INTERVAL = int(REDIS_HEALTH_CHECK_INTERVAL)
    if REDIS_HEALTH_CHECK_INTERVAL <= 0:
        REDIS_HEALTH_CHECK_INTERVAL = None
except ValueError:
    REDIS_HEALTH_CHECK_INTERVAL = None

REDIS_RECONNECT_DELAY = os.getenv('REDIS_RECONNECT_DELAY', '')

if REDIS_RECONNECT_DELAY == '':
    REDIS_RECONNECT_DELAY = None
else:
    try:
        REDIS_RECONNECT_DELAY = float(REDIS_RECONNECT_DELAY)
        if REDIS_RECONNECT_DELAY < 0:
            REDIS_RECONNECT_DELAY = None
    except Exception:
        REDIS_RECONNECT_DELAY = None

####################################
# Uvicorn
####################################

try:
    UVICORN_WORKERS = max(int(os.getenv('UVICORN_WORKERS', '1')), 1)
except (ValueError, TypeError):
    UVICORN_WORKERS = 1

####################################
# WEBSOCKET SUPPORT
####################################

ENABLE_WEBSOCKET_SUPPORT = os.getenv('ENABLE_WEBSOCKET_SUPPORT', 'True').lower() == 'true'


WEBSOCKET_MANAGER = os.getenv('WEBSOCKET_MANAGER', '')

WEBSOCKET_REDIS_OPTIONS = os.getenv('WEBSOCKET_REDIS_OPTIONS', '')


if WEBSOCKET_REDIS_OPTIONS == '':
    if REDIS_SOCKET_CONNECT_TIMEOUT:
        WEBSOCKET_REDIS_OPTIONS = {'socket_connect_timeout': REDIS_SOCKET_CONNECT_TIMEOUT}
    else:
        log.debug('No WEBSOCKET_REDIS_OPTIONS provided, defaulting to None')
        WEBSOCKET_REDIS_OPTIONS = None
else:
    try:
        WEBSOCKET_REDIS_OPTIONS = json.loads(WEBSOCKET_REDIS_OPTIONS)
    except Exception:
        log.warning('Invalid WEBSOCKET_REDIS_OPTIONS, defaulting to None')
        WEBSOCKET_REDIS_OPTIONS = None

WEBSOCKET_REDIS_URL = os.getenv('WEBSOCKET_REDIS_URL', REDIS_URL)
WEBSOCKET_REDIS_CLUSTER = os.getenv('WEBSOCKET_REDIS_CLUSTER', str(REDIS_CLUSTER)).lower() == 'true'

websocket_redis_lock_timeout = os.getenv('WEBSOCKET_REDIS_LOCK_TIMEOUT', '60')

try:
    WEBSOCKET_REDIS_LOCK_TIMEOUT = int(websocket_redis_lock_timeout)
except ValueError:
    WEBSOCKET_REDIS_LOCK_TIMEOUT = 60

WEBSOCKET_SENTINEL_HOSTS = os.getenv('WEBSOCKET_SENTINEL_HOSTS', '')
WEBSOCKET_SENTINEL_PORT = os.getenv('WEBSOCKET_SENTINEL_PORT', '26379')
WEBSOCKET_SERVER_LOGGING = os.getenv('WEBSOCKET_SERVER_LOGGING', 'False').lower() == 'true'
WEBSOCKET_SERVER_ENGINEIO_LOGGING = (
    os.getenv(
        'WEBSOCKET_SERVER_ENGINEIO_LOGGING',
        os.getenv('WEBSOCKET_SERVER_LOGGING', 'False'),
    ).lower()
    == 'true'
)
WEBSOCKET_SERVER_PING_TIMEOUT = os.getenv('WEBSOCKET_SERVER_PING_TIMEOUT', '20')
try:
    WEBSOCKET_SERVER_PING_TIMEOUT = int(WEBSOCKET_SERVER_PING_TIMEOUT)
except ValueError:
    WEBSOCKET_SERVER_PING_TIMEOUT = 20

WEBSOCKET_SERVER_PING_INTERVAL = os.getenv('WEBSOCKET_SERVER_PING_INTERVAL', '25')
try:
    WEBSOCKET_SERVER_PING_INTERVAL = int(WEBSOCKET_SERVER_PING_INTERVAL)
except ValueError:
    WEBSOCKET_SERVER_PING_INTERVAL = 25

WEBSOCKET_EVENT_CALLER_TIMEOUT = os.getenv('WEBSOCKET_EVENT_CALLER_TIMEOUT', '')

if WEBSOCKET_EVENT_CALLER_TIMEOUT == '':
    WEBSOCKET_EVENT_CALLER_TIMEOUT = None
else:
    try:
        WEBSOCKET_EVENT_CALLER_TIMEOUT = int(WEBSOCKET_EVENT_CALLER_TIMEOUT)
    except ValueError:
        WEBSOCKET_EVENT_CALLER_TIMEOUT = 300


REQUESTS_VERIFY = os.getenv('REQUESTS_VERIFY', 'True').lower() == 'true'

_aiohttp_timeout_raw = os.getenv('AIOHTTP_CLIENT_TIMEOUT', '')
try:
    AIOHTTP_CLIENT_TIMEOUT = int(_aiohttp_timeout_raw) if _aiohttp_timeout_raw else None
except (ValueError, TypeError):
    AIOHTTP_CLIENT_TIMEOUT = 300


AIOHTTP_CLIENT_SESSION_SSL = os.getenv('AIOHTTP_CLIENT_SESSION_SSL', 'True').lower() == 'true'

# When False (default), outbound HTTP requests do not follow 3xx redirects.
AIOHTTP_CLIENT_ALLOW_REDIRECTS = os.getenv('AIOHTTP_CLIENT_ALLOW_REDIRECTS', 'False').lower() == 'true'

# Optional User-Agent override for outbound web-loader fetches.  When set,
# SafeWebBaseLoader sends this value instead of the default python-requests UA
# which is aggressively blocked by Cloudflare, Wikipedia, and similar services.
USER_AGENT = os.getenv('USER_AGENT', '')

_model_list_timeout_raw = os.getenv(
    'AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST',
    os.getenv('AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST', '10'),
)
try:
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST = int(_model_list_timeout_raw) if _model_list_timeout_raw else None
except (ValueError, TypeError):
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST = 10

_tool_data_timeout_raw = os.getenv('AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA', '10')
try:
    AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA = int(_tool_data_timeout_raw) if _tool_data_timeout_raw else None
except (ValueError, TypeError):
    AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA = 10


AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL = os.getenv('AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL', 'True').lower() == 'true'

AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER = os.getenv('AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER', '')

if AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER == '':
    AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER = AIOHTTP_CLIENT_TIMEOUT
else:
    try:
        AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER = int(AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER)
    except Exception:
        AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER = AIOHTTP_CLIENT_TIMEOUT


####################################
# AIOHTTP Connection Pool
####################################

AIOHTTP_POOL_CONNECTIONS = os.getenv('AIOHTTP_POOL_CONNECTIONS', '')
if AIOHTTP_POOL_CONNECTIONS == '':
    AIOHTTP_POOL_CONNECTIONS = None
else:
    try:
        AIOHTTP_POOL_CONNECTIONS = int(AIOHTTP_POOL_CONNECTIONS)
    except ValueError:
        AIOHTTP_POOL_CONNECTIONS = None

AIOHTTP_POOL_CONNECTIONS_PER_HOST = os.getenv('AIOHTTP_POOL_CONNECTIONS_PER_HOST', '')
if AIOHTTP_POOL_CONNECTIONS_PER_HOST == '':
    AIOHTTP_POOL_CONNECTIONS_PER_HOST = None
else:
    try:
        AIOHTTP_POOL_CONNECTIONS_PER_HOST = int(AIOHTTP_POOL_CONNECTIONS_PER_HOST)
    except ValueError:
        AIOHTTP_POOL_CONNECTIONS_PER_HOST = None

AIOHTTP_POOL_DNS_TTL = os.getenv('AIOHTTP_POOL_DNS_TTL', '300')
try:
    AIOHTTP_POOL_DNS_TTL = int(AIOHTTP_POOL_DNS_TTL)
    if AIOHTTP_POOL_DNS_TTL < 0:
        AIOHTTP_POOL_DNS_TTL = 300
except ValueError:
    AIOHTTP_POOL_DNS_TTL = 300

RAG_EMBEDDING_TIMEOUT = os.getenv('RAG_EMBEDDING_TIMEOUT', '')

if RAG_EMBEDDING_TIMEOUT == '':
    RAG_EMBEDDING_TIMEOUT = None
else:
    try:
        RAG_EMBEDDING_TIMEOUT = int(RAG_EMBEDDING_TIMEOUT)
    except Exception:
        RAG_EMBEDDING_TIMEOUT = None


####################################
# Auth
####################################

WEBUI_AUTH = os.getenv('WEBUI_AUTH', 'True').lower() == 'true'

ENABLE_INITIAL_ADMIN_SIGNUP = os.getenv('ENABLE_INITIAL_ADMIN_SIGNUP', 'False').lower() == 'true'
ENABLE_SIGNUP_PASSWORD_CONFIRMATION = os.getenv('ENABLE_SIGNUP_PASSWORD_CONFIRMATION', 'False').lower() == 'true'

####################################
# Secret key & cookies
####################################

# WEBUI_JWT_SECRET_KEY is deprecated; use WEBUI_SECRET_KEY instead.
WEBUI_SECRET_KEY = os.getenv(
    'WEBUI_SECRET_KEY',
    os.getenv('WEBUI_JWT_SECRET_KEY', 't0p-s3cr3t'),
)

WEBUI_SESSION_COOKIE_SAME_SITE = os.getenv('WEBUI_SESSION_COOKIE_SAME_SITE', 'lax')
WEBUI_SESSION_COOKIE_SECURE = os.getenv('WEBUI_SESSION_COOKIE_SECURE', 'false').lower() == 'true'
WEBUI_AUTH_COOKIE_SAME_SITE = os.getenv('WEBUI_AUTH_COOKIE_SAME_SITE', WEBUI_SESSION_COOKIE_SAME_SITE)
WEBUI_AUTH_COOKIE_SECURE = (
    os.getenv(
        'WEBUI_AUTH_COOKIE_SECURE',
        os.getenv('WEBUI_SESSION_COOKIE_SECURE', 'false'),
    ).lower()
    == 'true'
)

if WEBUI_AUTH and WEBUI_SECRET_KEY == '':
    raise ValueError(ERROR_MESSAGES.ENV_VAR_NOT_FOUND)

ENABLE_COMPRESSION_MIDDLEWARE = os.getenv('ENABLE_COMPRESSION_MIDDLEWARE', 'True').lower() == 'true'

####################################
# Admin Account Runtime Creation
####################################

# Optional env vars for creating an admin account on startup
# Useful for headless/automated deployments
WEBUI_ADMIN_EMAIL = os.getenv('WEBUI_ADMIN_EMAIL', '')
WEBUI_ADMIN_PASSWORD = os.getenv('WEBUI_ADMIN_PASSWORD', '')
WEBUI_ADMIN_NAME = os.getenv('WEBUI_ADMIN_NAME', 'Admin')

WEBUI_AUTH_TRUSTED_EMAIL_HEADER = os.getenv('WEBUI_AUTH_TRUSTED_EMAIL_HEADER', None)
WEBUI_AUTH_TRUSTED_NAME_HEADER = os.getenv('WEBUI_AUTH_TRUSTED_NAME_HEADER', None)
WEBUI_AUTH_TRUSTED_GROUPS_HEADER = os.getenv('WEBUI_AUTH_TRUSTED_GROUPS_HEADER', None)
WEBUI_AUTH_TRUSTED_ROLE_HEADER = os.getenv('WEBUI_AUTH_TRUSTED_ROLE_HEADER', None)

# Custom header name for API key authentication.  Defaults to 'x-api-key'.
# Useful when Open WebUI sits behind a reverse proxy / API gateway that
# already uses the Authorization header for its own authentication — set
# this to a unique header (e.g. 'X-OpenWebUI-Key') so the middleware
# checks the custom header instead and avoids the 401 short-circuit.
CUSTOM_API_KEY_HEADER = os.getenv('CUSTOM_API_KEY_HEADER', 'x-api-key')

ENABLE_PASSWORD_VALIDATION = os.getenv('ENABLE_PASSWORD_VALIDATION', 'False').lower() == 'true'
PASSWORD_VALIDATION_REGEX_PATTERN = os.getenv(
    'PASSWORD_VALIDATION_REGEX_PATTERN',
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$',
)


try:
    PASSWORD_VALIDATION_REGEX_PATTERN = rf'{PASSWORD_VALIDATION_REGEX_PATTERN}'
    PASSWORD_VALIDATION_REGEX_PATTERN = re.compile(PASSWORD_VALIDATION_REGEX_PATTERN)
except Exception as e:
    log.error(f'Invalid PASSWORD_VALIDATION_REGEX_PATTERN: {e}')
    PASSWORD_VALIDATION_REGEX_PATTERN = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$')

PASSWORD_VALIDATION_HINT = os.getenv('PASSWORD_VALIDATION_HINT', '')


BYPASS_MODEL_ACCESS_CONTROL = os.getenv('BYPASS_MODEL_ACCESS_CONTROL', 'False').lower() == 'true'

# When enabled, skips pydub-based preprocessing (format conversion, compression,
# and chunked splitting) before sending files to processing engines. Useful when
# the upstream provider handles these steps or when ffmpeg is unavailable.
BYPASS_PYDUB_PREPROCESSING = os.getenv('BYPASS_PYDUB_PREPROCESSING', 'False').lower() == 'true'

# When disabled (default), the OpenAI catch-all proxy endpoint (/{path:path})
# is blocked. Enable only if you need direct passthrough to upstream OpenAI-
# compatible APIs for endpoints not natively handled by Open WebUI.
ENABLE_OPENAI_API_PASSTHROUGH = os.getenv('ENABLE_OPENAI_API_PASSTHROUGH', 'False').lower() == 'true'

WEBUI_AUTH_SIGNOUT_REDIRECT_URL = os.getenv('WEBUI_AUTH_SIGNOUT_REDIRECT_URL', None)

####################################
# OAUTH Configuration
####################################
ENABLE_OAUTH_EMAIL_FALLBACK = os.getenv('ENABLE_OAUTH_EMAIL_FALLBACK', 'False').lower() == 'true'

ENABLE_OAUTH_ID_TOKEN_COOKIE = os.getenv('ENABLE_OAUTH_ID_TOKEN_COOKIE', 'True').lower() == 'true'

OAUTH_CLIENT_INFO_ENCRYPTION_KEY = os.getenv('OAUTH_CLIENT_INFO_ENCRYPTION_KEY', WEBUI_SECRET_KEY)

OAUTH_SESSION_TOKEN_ENCRYPTION_KEY = os.getenv('OAUTH_SESSION_TOKEN_ENCRYPTION_KEY', WEBUI_SECRET_KEY)

# Maximum number of concurrent OAuth sessions per user per provider
# This prevents unbounded session growth while allowing multi-device usage
OAUTH_MAX_SESSIONS_PER_USER = int(os.getenv('OAUTH_MAX_SESSIONS_PER_USER', '10'))

# Token Exchange Configuration
# Allows external apps to exchange OAuth tokens for OpenWebUI tokens
ENABLE_OAUTH_TOKEN_EXCHANGE = os.getenv('ENABLE_OAUTH_TOKEN_EXCHANGE', 'False').lower() == 'true'

# Back-Channel Logout Configuration
# When enabled, exposes POST /oauth/backchannel-logout for IdP-initiated logout
# per OpenID Connect Back-Channel Logout 1.0 spec.
# Requires Redis for JWT revocation.
ENABLE_OAUTH_BACKCHANNEL_LOGOUT = os.getenv('ENABLE_OAUTH_BACKCHANNEL_LOGOUT', 'False').lower() == 'true'

####################################
# SCIM Configuration
####################################

ENABLE_SCIM = os.getenv('ENABLE_SCIM', os.getenv('SCIM_ENABLED', 'False')).lower() == 'true'
SCIM_TOKEN = os.getenv('SCIM_TOKEN', '')
SCIM_AUTH_PROVIDER = os.getenv('SCIM_AUTH_PROVIDER', '')

if ENABLE_SCIM and not SCIM_AUTH_PROVIDER:
    log.warning(
        'SCIM is enabled but SCIM_AUTH_PROVIDER is not set. '
        "Set SCIM_AUTH_PROVIDER to the OAuth provider name (e.g. 'microsoft', 'oidc') "
        'to enable externalId storage.'
    )

####################################
# LICENSE_KEY
####################################

LICENSE_KEY = os.getenv('LICENSE_KEY', '')

LICENSE_BLOB = None
LICENSE_BLOB_PATH = os.getenv('LICENSE_BLOB_PATH', DATA_DIR / 'l.data')
if LICENSE_BLOB_PATH and os.path.exists(LICENSE_BLOB_PATH):
    with open(LICENSE_BLOB_PATH, 'rb') as f:
        LICENSE_BLOB = f.read()

LICENSE_PUBLIC_KEY = os.getenv('LICENSE_PUBLIC_KEY', '')

pk = None
if LICENSE_PUBLIC_KEY:
    pk = serialization.load_pem_public_key(
        f"""
-----BEGIN PUBLIC KEY-----
{LICENSE_PUBLIC_KEY}
-----END PUBLIC KEY-----
""".encode()
    )


####################################
# WEBUI Identity
####################################

WEBUI_NAME = os.getenv('WEBUI_NAME', 'Open WebUI')
if WEBUI_NAME != 'Open WebUI':
    WEBUI_NAME += ' (Open WebUI)'

WEBUI_FAVICON_URL = 'https://openwebui.com/favicon.png'
WEBUI_BUILD_HASH = os.getenv('WEBUI_BUILD_HASH', 'dev-build')
TRUSTED_SIGNATURE_KEY = os.getenv('TRUSTED_SIGNATURE_KEY', '')

####################################
# Feature flags
####################################

SAFE_MODE = os.getenv('SAFE_MODE', 'False').lower() == 'true'
ENABLE_EASTER_EGGS = os.getenv('ENABLE_EASTER_EGGS', 'True').lower() == 'true'
ENABLE_STAR_SESSIONS_MIDDLEWARE = os.getenv('ENABLE_STAR_SESSIONS_MIDDLEWARE', 'False').lower() == 'true'
ENABLE_KB_EXEC = os.getenv('ENABLE_KB_EXEC', 'False').lower() == 'true'

ENABLE_PROFILE_IMAGE_URL_FORWARDING = os.getenv('ENABLE_PROFILE_IMAGE_URL_FORWARDING', 'True').lower() == 'true'
PROFILE_IMAGE_ALLOWED_MIME_TYPES = frozenset(
    t.strip()
    for t in os.getenv(
        'PROFILE_IMAGE_ALLOWED_MIME_TYPES',
        'image/png,image/jpeg,image/gif,image/webp',
    ).split(',')
    if t.strip()
)

####################################
# Forward Headers
####################################

ENABLE_FORWARD_USER_INFO_HEADERS = os.getenv('ENABLE_FORWARD_USER_INFO_HEADERS', 'False').lower() == 'true'

FORWARD_USER_INFO_HEADER_USER_NAME = os.getenv('FORWARD_USER_INFO_HEADER_USER_NAME', 'X-OpenWebUI-User-Name')
FORWARD_USER_INFO_HEADER_USER_ID = os.getenv('FORWARD_USER_INFO_HEADER_USER_ID', 'X-OpenWebUI-User-Id')
FORWARD_USER_INFO_HEADER_USER_EMAIL = os.getenv('FORWARD_USER_INFO_HEADER_USER_EMAIL', 'X-OpenWebUI-User-Email')
FORWARD_USER_INFO_HEADER_USER_ROLE = os.getenv('FORWARD_USER_INFO_HEADER_USER_ROLE', 'X-OpenWebUI-User-Role')
FORWARD_SESSION_INFO_HEADER_MESSAGE_ID = os.getenv('FORWARD_SESSION_INFO_HEADER_MESSAGE_ID', 'X-OpenWebUI-Message-Id')
FORWARD_SESSION_INFO_HEADER_CHAT_ID = os.getenv('FORWARD_SESSION_INFO_HEADER_CHAT_ID', 'X-OpenWebUI-Chat-Id')

####################################
# Progressive Web App
####################################

EXTERNAL_PWA_MANIFEST_URL = os.getenv('EXTERNAL_PWA_MANIFEST_URL', None)

####################################
# GROUP DEFAULTS
####################################

# Controls the default "Who can share to this group" setting for new groups.
# Env var values: "true" (anyone), "false" (no one), "members" (only group members).
_default_group_share = os.getenv('DEFAULT_GROUP_SHARE_PERMISSION', 'members').strip().lower()
DEFAULT_GROUP_SHARE_PERMISSION = 'members' if _default_group_share == 'members' else _default_group_share == 'true'

####################################
# MODELS
####################################

ENABLE_CUSTOM_MODEL_FALLBACK = os.getenv('ENABLE_CUSTOM_MODEL_FALLBACK', 'False').lower() == 'true'

MODELS_CACHE_TTL = os.getenv('MODELS_CACHE_TTL', '1')
if MODELS_CACHE_TTL == '':
    MODELS_CACHE_TTL = None
else:
    try:
        MODELS_CACHE_TTL = int(MODELS_CACHE_TTL)
    except Exception:
        MODELS_CACHE_TTL = 1


####################################
# CHAT
####################################

ENABLE_CHAT_RESPONSE_BASE64_IMAGE_URL_CONVERSION = (
    os.getenv('ENABLE_CHAT_RESPONSE_BASE64_IMAGE_URL_CONVERSION', 'False').lower() == 'true'
)

# When enabled, uses a hardcoded extension-to-MIME dictionary as a last-resort
# fallback when both mimetypes.guess_type() and file.meta.content_type fail to
# determine the content type. This can help on minimal container images (e.g.
# wolfi-base) that lack /etc/mime.types AND have legacy files without stored
# content_type metadata.
ENABLE_IMAGE_CONTENT_TYPE_EXTENSION_FALLBACK = (
    os.getenv('ENABLE_IMAGE_CONTENT_TYPE_EXTENSION_FALLBACK', 'False').lower() == 'true'
)

CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE = os.getenv('CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE', '1')

if CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE == '':
    CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE = 1
else:
    try:
        CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE = int(CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE)
    except Exception:
        CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE = 1


# Maximum tool-call iterations per chat response. Set to -1 for unlimited.
# The old CHAT_RESPONSE_MAX_TOOL_CALL_RETRIES name is accepted as a fallback.
CHAT_RESPONSE_MAX_TOOL_CALL_ITERATIONS = os.getenv(
    'CHAT_RESPONSE_MAX_TOOL_CALL_ITERATIONS',
    os.getenv('CHAT_RESPONSE_MAX_TOOL_CALL_RETRIES', '256'),
)

if CHAT_RESPONSE_MAX_TOOL_CALL_ITERATIONS == '':
    CHAT_RESPONSE_MAX_TOOL_CALL_ITERATIONS = 256
else:
    try:
        CHAT_RESPONSE_MAX_TOOL_CALL_ITERATIONS = int(CHAT_RESPONSE_MAX_TOOL_CALL_ITERATIONS)
    except Exception:
        CHAT_RESPONSE_MAX_TOOL_CALL_ITERATIONS = 256

# -1 means unlimited (no cap).
if CHAT_RESPONSE_MAX_TOOL_CALL_ITERATIONS == -1:
    CHAT_RESPONSE_MAX_TOOL_CALL_ITERATIONS = None


# WARNING: Experimental. Only enable if your upstream Responses API endpoint
# supports stateful sessions (i.e. server-side response storage with
# previous_response_id anchoring). Most proxies and third-party endpoints
# are stateless and will break if this is enabled.
ENABLE_RESPONSES_API_STATEFUL = os.getenv('ENABLE_RESPONSES_API_STATEFUL', 'False').lower() == 'true'


CHAT_STREAM_RESPONSE_CHUNK_MAX_BUFFER_SIZE = os.getenv('CHAT_STREAM_RESPONSE_CHUNK_MAX_BUFFER_SIZE', '')

if CHAT_STREAM_RESPONSE_CHUNK_MAX_BUFFER_SIZE == '':
    CHAT_STREAM_RESPONSE_CHUNK_MAX_BUFFER_SIZE = None
else:
    try:
        CHAT_STREAM_RESPONSE_CHUNK_MAX_BUFFER_SIZE = int(CHAT_STREAM_RESPONSE_CHUNK_MAX_BUFFER_SIZE)
    except Exception:
        CHAT_STREAM_RESPONSE_CHUNK_MAX_BUFFER_SIZE = None


####################################
# SENTENCE TRANSFORMERS
####################################


SENTENCE_TRANSFORMERS_BACKEND = os.getenv('SENTENCE_TRANSFORMERS_BACKEND', '')
if SENTENCE_TRANSFORMERS_BACKEND == '':
    SENTENCE_TRANSFORMERS_BACKEND = 'torch'


SENTENCE_TRANSFORMERS_MODEL_KWARGS = os.getenv('SENTENCE_TRANSFORMERS_MODEL_KWARGS', '')
if SENTENCE_TRANSFORMERS_MODEL_KWARGS == '':
    SENTENCE_TRANSFORMERS_MODEL_KWARGS = None
else:
    try:
        SENTENCE_TRANSFORMERS_MODEL_KWARGS = json.loads(SENTENCE_TRANSFORMERS_MODEL_KWARGS)
    except Exception:
        SENTENCE_TRANSFORMERS_MODEL_KWARGS = None


SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND = os.getenv('SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND', '')
if SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND == '':
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND = 'torch'


SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS = os.getenv('SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS', '')
if SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS == '':
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS = None
else:
    try:
        SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS = json.loads(SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS)
    except Exception:
        SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS = None

# Whether to apply sigmoid normalization to CrossEncoder reranking scores.
# When enabled (default), scores are normalized to 0-1 range for proper
# relevance threshold behavior with MS MARCO models.
SENTENCE_TRANSFORMERS_CROSS_ENCODER_SIGMOID_ACTIVATION_FUNCTION = (
    os.getenv('SENTENCE_TRANSFORMERS_CROSS_ENCODER_SIGMOID_ACTIVATION_FUNCTION', 'True').lower() == 'true'
)

####################################
# TOOLS/FUNCTIONS PIP OPTIONS
####################################

ENABLE_PIP_INSTALL_FRONTMATTER_REQUIREMENTS = (
    os.getenv('ENABLE_PIP_INSTALL_FRONTMATTER_REQUIREMENTS', 'True').lower() == 'true'
)

PIP_OPTIONS = os.getenv('PIP_OPTIONS', '').split()
PIP_PACKAGE_INDEX_OPTIONS = os.getenv('PIP_PACKAGE_INDEX_OPTIONS', '').split()


####################################
# OFFLINE_MODE
####################################

ENABLE_VERSION_UPDATE_CHECK = os.getenv('ENABLE_VERSION_UPDATE_CHECK', 'true').lower() == 'true'
OFFLINE_MODE = os.getenv('OFFLINE_MODE', 'false').lower() == 'true'

if OFFLINE_MODE:
    os.environ['HF_HUB_OFFLINE'] = '1'
    ENABLE_VERSION_UPDATE_CHECK = False

####################################
# Audit logging
####################################


ENABLE_AUDIT_STDOUT = os.getenv('ENABLE_AUDIT_STDOUT', 'False').lower() == 'true'
ENABLE_AUDIT_LOGS_FILE = os.getenv('ENABLE_AUDIT_LOGS_FILE', 'True').lower() == 'true'

# Where to store log file
# Defaults to the DATA_DIR/audit.log. To set AUDIT_LOGS_FILE_PATH you need to
# provide the whole path, like: /app/audit.log
AUDIT_LOGS_FILE_PATH = os.getenv('AUDIT_LOGS_FILE_PATH', f'{DATA_DIR}/audit.log')
# Maximum size of a file before rotating into a new log file
AUDIT_LOG_FILE_ROTATION_SIZE = os.getenv('AUDIT_LOG_FILE_ROTATION_SIZE', '10MB')

# Comma separated list of logger names to use for audit logging
# Default is "uvicorn.access" which is the access log for Uvicorn
# You can add more logger names to this list if you want to capture more logs
AUDIT_UVICORN_LOGGER_NAMES = os.getenv('AUDIT_UVICORN_LOGGER_NAMES', 'uvicorn.access').split(',')

# METADATA | REQUEST | REQUEST_RESPONSE
AUDIT_LOG_LEVEL = os.getenv('AUDIT_LOG_LEVEL', 'NONE').upper()
try:
    MAX_BODY_LOG_SIZE = int(os.getenv('MAX_BODY_LOG_SIZE') or 2048)
except ValueError:
    MAX_BODY_LOG_SIZE = 2048

# Comma separated list for urls to exclude from audit
AUDIT_EXCLUDED_PATHS = os.getenv('AUDIT_EXCLUDED_PATHS', '/chats,/chat,/folders').split(',')
AUDIT_EXCLUDED_PATHS = [path.strip() for path in AUDIT_EXCLUDED_PATHS]
AUDIT_EXCLUDED_PATHS = [path.lstrip('/') for path in AUDIT_EXCLUDED_PATHS]

# Comma separated list of urls to include in audit (whitelist mode)
# When set, only these paths are audited and AUDIT_EXCLUDED_PATHS is ignored
AUDIT_INCLUDED_PATHS = os.getenv('AUDIT_INCLUDED_PATHS', '').split(',')
AUDIT_INCLUDED_PATHS = [path.strip() for path in AUDIT_INCLUDED_PATHS]
AUDIT_INCLUDED_PATHS = [path.lstrip('/') for path in AUDIT_INCLUDED_PATHS if path]

# When enabled, GET requests are also audited (disabled by default to avoid log noise)
ENABLE_AUDIT_GET_REQUESTS = os.getenv('ENABLE_AUDIT_GET_REQUESTS', 'False').lower() == 'true'


####################################
# OPENTELEMETRY
####################################

ENABLE_OTEL = os.getenv('ENABLE_OTEL', 'False').lower() == 'true'
ENABLE_OTEL_TRACES = os.getenv('ENABLE_OTEL_TRACES', 'False').lower() == 'true'
ENABLE_OTEL_METRICS = os.getenv('ENABLE_OTEL_METRICS', 'False').lower() == 'true'
ENABLE_OTEL_LOGS = os.getenv('ENABLE_OTEL_LOGS', 'False').lower() == 'true'

OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4317')
OTEL_METRICS_EXPORTER_OTLP_ENDPOINT = os.getenv('OTEL_METRICS_EXPORTER_OTLP_ENDPOINT', OTEL_EXPORTER_OTLP_ENDPOINT)
OTEL_LOGS_EXPORTER_OTLP_ENDPOINT = os.getenv('OTEL_LOGS_EXPORTER_OTLP_ENDPOINT', OTEL_EXPORTER_OTLP_ENDPOINT)
OTEL_EXPORTER_OTLP_INSECURE = os.getenv('OTEL_EXPORTER_OTLP_INSECURE', 'False').lower() == 'true'
OTEL_METRICS_EXPORTER_OTLP_INSECURE = (
    os.getenv('OTEL_METRICS_EXPORTER_OTLP_INSECURE', str(OTEL_EXPORTER_OTLP_INSECURE)).lower() == 'true'
)
OTEL_LOGS_EXPORTER_OTLP_INSECURE = (
    os.getenv('OTEL_LOGS_EXPORTER_OTLP_INSECURE', str(OTEL_EXPORTER_OTLP_INSECURE)).lower() == 'true'
)
OTEL_SERVICE_NAME = os.getenv('OTEL_SERVICE_NAME', 'open-webui')
OTEL_RESOURCE_ATTRIBUTES = os.getenv('OTEL_RESOURCE_ATTRIBUTES', '')  # e.g. key1=val1,key2=val2
OTEL_TRACES_SAMPLER = os.getenv('OTEL_TRACES_SAMPLER', 'parentbased_always_on').lower()
OTEL_BASIC_AUTH_USERNAME = os.getenv('OTEL_BASIC_AUTH_USERNAME', '')
OTEL_BASIC_AUTH_PASSWORD = os.getenv('OTEL_BASIC_AUTH_PASSWORD', '')
OTEL_METRICS_EXPORT_INTERVAL_MILLIS = int(os.getenv('OTEL_METRICS_EXPORT_INTERVAL_MILLIS', '10000'))

OTEL_METRICS_BASIC_AUTH_USERNAME = os.getenv('OTEL_METRICS_BASIC_AUTH_USERNAME', OTEL_BASIC_AUTH_USERNAME)
OTEL_METRICS_BASIC_AUTH_PASSWORD = os.getenv('OTEL_METRICS_BASIC_AUTH_PASSWORD', OTEL_BASIC_AUTH_PASSWORD)
OTEL_LOGS_BASIC_AUTH_USERNAME = os.getenv('OTEL_LOGS_BASIC_AUTH_USERNAME', OTEL_BASIC_AUTH_USERNAME)
OTEL_LOGS_BASIC_AUTH_PASSWORD = os.getenv('OTEL_LOGS_BASIC_AUTH_PASSWORD', OTEL_BASIC_AUTH_PASSWORD)

OTEL_OTLP_SPAN_EXPORTER = os.getenv('OTEL_OTLP_SPAN_EXPORTER', 'grpc').lower()  # grpc or http

OTEL_METRICS_OTLP_SPAN_EXPORTER = os.getenv(
    'OTEL_METRICS_OTLP_SPAN_EXPORTER', OTEL_OTLP_SPAN_EXPORTER
).lower()  # grpc or http

OTEL_LOGS_OTLP_SPAN_EXPORTER = os.getenv(
    'OTEL_LOGS_OTLP_SPAN_EXPORTER', OTEL_OTLP_SPAN_EXPORTER
).lower()  # grpc or http

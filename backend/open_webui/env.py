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

# Sunway: loguru's `diagnose` prints the VALUE of every local variable in an exception
# traceback, and loguru defaults it to True. That dumped session JWTs to stdout — a
# socket `user-join` handler takes `data['auth']['token']`, so any unhandled error in
# that path wrote a live bearer token into the cluster log stack, where it is retained
# and readable by anyone with log access. Same disclosure class as a secret in an API
# response, with a wider audience.
#
# Off in prod (the image sets ENV=prod; dev.ps1 leaves it unset so local debugging keeps
# the variable dumps). `backtrace` stays on either way: it adds the surrounding frames,
# which is the useful half, and it does not print values. Set LOG_DIAGNOSE=true to force
# it on for a deliberate debugging window — expect secrets in the log if you do.
LOG_DIAGNOSE = os.getenv('LOG_DIAGNOSE', 'true' if ENV == 'dev' else 'false').lower() == 'true'

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

# Outbound HTTP timeout for model-provider calls. Upstream defaults to '' (no timeout),
# which lets a hung provider hold a request open forever; we bound it instead.
#
# The default was '180s' until 2026-08-07 — a typo. int('180s') raises, so the value
# silently fell through to the except branch and every deployment has actually been
# running 300, never the 180 that was intended and documented. Seconds, no unit suffix.
_aiohttp_timeout_raw = os.getenv('AIOHTTP_CLIENT_TIMEOUT', '300')
try:
    AIOHTTP_CLIENT_TIMEOUT = int(_aiohttp_timeout_raw) if _aiohttp_timeout_raw else None
except (ValueError, TypeError):
    AIOHTTP_CLIENT_TIMEOUT = 300


AIOHTTP_CLIENT_SESSION_SSL = os.getenv('AIOHTTP_CLIENT_SESSION_SSL', 'True').lower() == 'true'

# When False (default), outbound HTTP requests do not follow 3xx redirects.
AIOHTTP_CLIENT_ALLOW_REDIRECTS = os.getenv('AIOHTTP_CLIENT_ALLOW_REDIRECTS', 'False').lower() == 'true'

# Content-extraction (Docling/Tika) HTTP request timeout in seconds. Bounds how long
# a single extract call may block a worker thread, so a hung/slow extractor server
# can't pin it forever. Kept above DOCLING_SERVE_MAX_SYNC_WAIT (docling-serve's own sync
# cap) so the docling server's own cap fires first and returns a clean error.
try:
    CONTENT_EXTRACTION_REQUEST_TIMEOUT = int(os.getenv('CONTENT_EXTRACTION_REQUEST_TIMEOUT', '620'))
except (ValueError, TypeError):
    CONTENT_EXTRACTION_REQUEST_TIMEOUT = 620

# Sunway: use docling-serve's ASYNC API (submit -> poll -> fetch result) instead of the
# blocking sync /v1/convert/file. The sync endpoint holds one HTTP request open for the
# whole conversion and is bounded by docling-serve's DOCLING_SERVE_MAX_SYNC_WAIT (default
# 120s) — so large/OCR-heavy PDFs 504 mid-convert regardless of our client timeout. The
# async flow submits the job, long-polls task status, then fetches the result, so no single
# request is held for minutes and the 504-mid-convert class of failure disappears (the
# maintainers' recommended path for long jobs). Plain env -> takes effect on restart. ON by
# default: DoclingLoader retries synchronously whenever the async path gives no verdict (no
# async endpoint / connection / contract mismatch), so a docling-serve without (or with a
# differing) async API degrades gracefully. Set 'false' as a kill-switch to force sync.
DOCLING_ASYNC = os.getenv('DOCLING_ASYNC', 'True').lower() == 'true'
# Seconds between async status polls (uses docling-serve's long-poll `wait` param, so each
# poll blocks server-side up to this long). Total wait is bounded by the request timeout above.
try:
    DOCLING_ASYNC_POLL_INTERVAL = int(os.getenv('DOCLING_ASYNC_POLL_INTERVAL', '5'))
except (ValueError, TypeError):
    DOCLING_ASYNC_POLL_INTERVAL = 5
if DOCLING_ASYNC_POLL_INTERVAL < 1:
    DOCLING_ASYNC_POLL_INTERVAL = 1

# Max concurrent document extractions per process. Bounds how many uploads can be
# parsed/OCR'd at once so an upload burst can't exhaust the default thread pool.
try:
    CONTENT_EXTRACTION_MAX_CONCURRENCY = int(os.getenv('CONTENT_EXTRACTION_MAX_CONCURRENCY', '4'))
except (ValueError, TypeError):
    CONTENT_EXTRACTION_MAX_CONCURRENCY = 4

# Sunway: max concurrent EMBEDDING jobs per process. Extraction is bounded by
# CONTENT_EXTRACTION_MAX_CONCURRENCY, but embedding (save_docs_to_vector_db, run in a worker
# thread) had NO bound -- so a burst of large uploads (or cancelled-then-reuploaded files whose
# background embedding keeps running) stacks many concurrent bge-m3 embed jobs and thrashes
# CPU/RAM, risking a crash. This caps how many embed at once; the rest queue. Keep low on CPU
# (embedding is CPU-bound in-process); raise once embedding is offloaded to the GPU endpoint.
try:
    EMBEDDING_MAX_CONCURRENCY = int(os.getenv('EMBEDDING_MAX_CONCURRENCY', '6'))
except (ValueError, TypeError):
    EMBEDDING_MAX_CONCURRENCY = 2
if EMBEDDING_MAX_CONCURRENCY < 1:
    EMBEDDING_MAX_CONCURRENCY = 1

# Wall-clock cap (seconds) on a single in-process extraction. The HTTP engines have
# CONTENT_EXTRACTION_REQUEST_TIMEOUT, but the in-process loaders (pypdf, unstructured,
# csv, text) have no timeout of their own, so a pathological file could hang an
# extraction slot indefinitely. Set above CONTENT_EXTRACTION_REQUEST_TIMEOUT so the
# engine's own timeout fires first for a clean error; this is the backstop. Note: a
# timed-out worker thread cannot be force-killed and keeps running in the background,
# but the slot is released and the upload is marked failed.
try:
    CONTENT_EXTRACTION_TIMEOUT = int(os.getenv('CONTENT_EXTRACTION_TIMEOUT', '660'))
except (ValueError, TypeError):
    CONTENT_EXTRACTION_TIMEOUT = 660

# Max total extracted text (characters) accepted from a single file. Two jobs:
# (1) decompression-bomb guard -- docx/xlsx/pptx are ZIP containers and crafted PDFs
#     can expand to gigabytes of text; reject before that hits chunking/embedding/DB.
# (2) latency governor -- embedding time scales with char/chunk count, NOT file MB, so
#     this (not the MB cap) is the real ceiling on worst-case upload time.
# Sunway (2026-07-21): lowered 10M -> 3M. 10M was a *post-GPU* value; on the current
# in-process CPU bge-m3 (~2.8 chunks/s) it does NOT bound embedding -- a 5MB CSV
# (~64k rows, ~9M chars) sailed under it and took 6+ HOURS to embed. 3M chars ~= ~3k
# chunks ~= ~18 min worst-case on CPU, while still covering every real business doc (a
# 400-page PDF ~= ~0.7-1.2M chars; office docs are far smaller). It rejects only
# data-dump spreadsheets/CSVs, which are a poor RAG fit anyway. Raise back toward 10M
# once embedding is GPU-offloaded (see AUDIT-015/026). 0 disables. Reject (not truncate).
try:
    CONTENT_EXTRACTION_MAX_OUTPUT_CHARS = int(os.getenv('CONTENT_EXTRACTION_MAX_OUTPUT_CHARS', '3000000'))
except (ValueError, TypeError):
    CONTENT_EXTRACTION_MAX_OUTPUT_CHARS = 5000000

# Per-user file-upload rate limit (Sunway): every uploaded file is extracted + embedded,
# so one user's bulk-upload burst can saturate the shared GPU/embedding pipeline for
# everyone. Caps uploads per user over a rolling window. Plain env reads (take effect on
# restart). Set FILE_UPLOAD_RATE_LIMIT=0 to disable (e.g. during upload stress tests).
try:
    FILE_UPLOAD_RATE_LIMIT = int(os.getenv('FILE_UPLOAD_RATE_LIMIT', '60'))
except (ValueError, TypeError):
    FILE_UPLOAD_RATE_LIMIT = 60
try:
    FILE_UPLOAD_RATE_LIMIT_WINDOW = int(os.getenv('FILE_UPLOAD_RATE_LIMIT_WINDOW', '60'))
except (ValueError, TypeError):
    FILE_UPLOAD_RATE_LIMIT_WINDOW = 60

# Full-context injection budget (Sunway). When a file or KB is attached in "full context /
# use entire document" mode, its ENTIRE extracted text is injected into the prompt,
# bypassing retrieval. Unbounded, that overflows the model's context window -- worst on
# the SMALLEST served model (e.g. Qwen 128K). Above this many characters, full mode is
# transparently downgraded to normal chunked retrieval instead of overflowing. Size for
# your smallest model's window: 200000 chars ~= ~50K tokens, leaving headroom for chat
# history + the answer on a 128K model. Plain env read (restart to apply). 0 disables the
# guard (unbounded full context -- not recommended for a mixed/128K fleet).
try:
    RAG_FULL_CONTEXT_MAX_CHARS = int(os.getenv('RAG_FULL_CONTEXT_MAX_CHARS', '200000'))
except (ValueError, TypeError):
    RAG_FULL_CONTEXT_MAX_CHARS = 200000

# Sunway: skip embedding for SMALL chat attachments and serve them full-context instead.
# Embedding is the slow half of an upload; for a doc that fits RAG_FULL_CONTEXT_MAX_CHARS
# it's unnecessary work — the whole extracted text can be injected directly (the SOTA
# "attach a file to a chat" pattern), so the file is usable the instant extraction finishes.
# ONLY applies to chat attachments (never Knowledge Bases — those are the persistent
# retrieval corpus and always embed) and only when the extracted text fits the budget;
# larger files fall through to normal embed + RAG. process_file marks these with
# data['full_context']=True; retrieval (utils.get_sources_from_items) injects them whole.
# Plain env read (restart to apply). ON by default as hybrid full-context +
# selective RAG is the decided behaviour). Full-context re-sends the doc each turn, so it
# carries KV-cache/context-window load: set it 'false' per environment if an
# inference-concurrency stress test says the fleet can't take it.
RAG_CHAT_ATTACHMENT_FULL_CONTEXT = os.getenv('RAG_CHAT_ATTACHMENT_FULL_CONTEXT', 'True').lower() == 'true'

# Image-aware PDF routing (Sunway). The PDF fast path trusts pypdf's text layer, so a
# born-digital PDF with SCREENSHOTS / scanned figures pasted in passes as "digital" and
# the text baked into those images is never OCR'd (silently lost). When enabled, a
# digital-looking PDF that also embeds substantial raster images is instead routed to
# Docling with force_ocr=true so the image text is read. This TRADES SPEED FOR
# COMPLETENESS: force_ocr OCRs every page (much slower, and on the shared Docling GPU),
# vs the millisecond pypdf fast path. Tune the two thresholds against real sample docs --
# raising them reroutes fewer docs (faster, may miss some); lowering catches more (slower).
# Plain env reads (restart to apply).
RAG_PDF_IMAGE_ROUTE_ENABLED = os.getenv('RAG_PDF_IMAGE_ROUTE_ENABLED', 'True').lower() == 'true'
try:
    # Minimum embedded-image pixel area (width*height) to count as "substantial"; filters
    # out small logos/icons/bullets. 90000 ~= a 300x300 image.
    RAG_PDF_IMAGE_MIN_PIXELS = int(os.getenv('RAG_PDF_IMAGE_MIN_PIXELS', '90000'))
except (ValueError, TypeError):
    RAG_PDF_IMAGE_MIN_PIXELS = 90000
try:
    # How many substantial embedded images trigger the forced-OCR reroute. 1 = reroute any
    # digital PDF with a screenshot (most thorough, slowest); raise to cut Docling load.
    RAG_PDF_IMAGE_MIN_COUNT = int(os.getenv('RAG_PDF_IMAGE_MIN_COUNT', '1'))
except (ValueError, TypeError):
    RAG_PDF_IMAGE_MIN_COUNT = 1

# Sunway: hard page cap for PDFs, checked BEFORE any extraction engine runs (pypdf can
# count pages in milliseconds). This is the early, cheap guard that
# CONTENT_EXTRACTION_MAX_OUTPUT_CHARS cannot be: for image-bearing/scanned PDFs the char
# count is only known AFTER Docling OCR, so the char cap would reject a 400-page scan only
# after burning minutes of GPU. Page count is known up front, on every route.
# 400 covers effectively every internal business document (reports, policies, contracts,
# manuals); it also caps downstream embedding cost (~400pp is ~700 chunks vs ~10k at the
# 10M-char ceiling). Deliberately NOT set in dev.ps1 or the Helm manifest -- this default
# IS the policy; the env var exists only so prod can retune without a code change + image
# rebuild. 0 disables the cap.
try:
    RAG_PDF_MAX_PAGES = int(os.getenv('RAG_PDF_MAX_PAGES', '400'))
except (ValueError, TypeError):
    RAG_PDF_MAX_PAGES = 400

# Image OCR fallback (Sunway): when a selected model is NOT vision-capable
# (capabilities.vision = false in Admin > Models), uploaded images are run through
# the content-extraction engine (Docling OCR) and their extracted text is injected as
# context instead of an image_url the text-only model can't consume. Lets text models
# like DeepSeek "read" document images/screenshots. Purely visual images still need a
# vision model. Default on.
ENABLE_IMAGE_OCR_FALLBACK = os.getenv('ENABLE_IMAGE_OCR_FALLBACK', 'True').lower() == 'true'

# PDF fast-path: when the engine is Docling and this is enabled, born-digital PDFs
# are extracted with pypdf (milliseconds) instead of Docling, which only runs for
# scanned / low-text PDFs that actually need OCR. Default off -- enabling trades
# Docling's richer layout/table structure for speed on born-digital PDFs.
RAG_PDF_FAST_PATH = os.getenv('RAG_PDF_FAST_PATH', 'False').lower() == 'true'
try:
    RAG_PDF_FAST_PATH_MIN_CHARS_PER_PAGE = int(os.getenv('RAG_PDF_FAST_PATH_MIN_CHARS_PER_PAGE', '100'))
except (ValueError, TypeError):
    RAG_PDF_FAST_PATH_MIN_CHARS_PER_PAGE = 100

# PDF fast-path engine (Sunway A/B): which lightweight loader reads born-digital PDFs when
# RAG_PDF_FAST_PATH is on -- 'pypdf' (default) or 'markitdown'. Scanned/low-text PDFs still
# fall back to Docling for OCR. Seeds the runtime toggle store (flip live in the Admin UI).
RAG_PDF_FAST_PATH_ENGINE = os.getenv('RAG_PDF_FAST_PATH_ENGINE', 'pypdf').strip().lower()
if RAG_PDF_FAST_PATH_ENGINE not in ('pypdf', 'markitdown'):
    RAG_PDF_FAST_PATH_ENGINE = 'pypdf'

# Office fast-path (Sunway A/B): when the engine is Docling and this is on, born-digital
# OOXML office files (.docx/.xlsx/.pptx) are extracted by a lightweight loader instead of
# Docling. RAG_OFFICE_FAST_PATH_ENGINE picks which lightweight engine: 'unstructured' (the
# langchain Unstructured loaders already bundled) or 'markitdown' (Microsoft MarkItDown ->
# Markdown). Falls back to Docling on failure/empty text. These SEED the runtime toggle
# store (retrieval/loaders/extraction_ab.py), which the Admin UI flips WITHOUT a restart --
# so this env value is only the boot default. Legacy .doc/.xls/.ppt are unaffected (they
# already use local loaders). Default off.
RAG_OFFICE_FAST_PATH = os.getenv('RAG_OFFICE_FAST_PATH', 'False').lower() == 'true'
RAG_OFFICE_FAST_PATH_ENGINE = os.getenv('RAG_OFFICE_FAST_PATH_ENGINE', 'unstructured').strip().lower()
if RAG_OFFICE_FAST_PATH_ENGINE not in ('unstructured', 'markitdown'):
    RAG_OFFICE_FAST_PATH_ENGINE = 'unstructured'

# Image vision LLM (Sunway): route uploaded IMAGES through a vision LLM (e.g. Gemma
# served via vLLM/LiteLLM) so a text-only chat model gets BOTH the image's transcribed
# text AND a description of non-text visuals (photos, charts, diagrams) that OCR alone
# can't provide. Works with ENABLE_IMAGE_OCR_FALLBACK: that fallback routes images to the
# extraction pipeline; this decides an image is read by the vision LLM (and, when
# COMBINE_OCR is on and the engine is Docling, ALSO by Docling for faithful text). Only
# images are affected -- PDFs/documents still go to the configured engine. Active only
# when BASE_URL and MODEL are both set. Plain env reads -> take effect on restart.
RAG_IMAGE_VISION_LLM_BASE_URL = os.getenv('RAG_IMAGE_VISION_LLM_BASE_URL', '')
RAG_IMAGE_VISION_LLM_API_KEY = os.getenv('RAG_IMAGE_VISION_LLM_API_KEY', '')
RAG_IMAGE_VISION_LLM_MODEL = os.getenv('RAG_IMAGE_VISION_LLM_MODEL', '')
# Optional override of the extraction prompt. Empty -> loader picks a sensible default
# (transcribe+describe when vision-only, describe-only when Docling OCR is combined).
RAG_IMAGE_VISION_LLM_PROMPT = os.getenv('RAG_IMAGE_VISION_LLM_PROMPT', '')
# When true (and engine is Docling), also run Docling OCR for faithful text and prepend
# it; the vision LLM then only describes visuals. A VLM can misread exact text
# (digits/tables), so Docling stays authoritative for text-embedded images.
RAG_IMAGE_VISION_LLM_COMBINE_OCR = os.getenv('RAG_IMAGE_VISION_LLM_COMBINE_OCR', 'False').lower() == 'true'
try:
    RAG_IMAGE_VISION_LLM_MAX_TOKENS = int(os.getenv('RAG_IMAGE_VISION_LLM_MAX_TOKENS', '2048'))
except (ValueError, TypeError):
    RAG_IMAGE_VISION_LLM_MAX_TOKENS = 2048
# Extra JSON merged into the chat/completions body -- primarily to disable reasoning at
# request time, e.g. {"chat_template_kwargs": {"enable_thinking": false}}. The loader
# also strips leaked reasoning defensively, so this is best-effort hardening.
RAG_IMAGE_VISION_LLM_EXTRA_BODY = os.getenv('RAG_IMAGE_VISION_LLM_EXTRA_BODY', '')


# Per-chat System Prompt hardening (Sunway). The text a user types into Chat Controls
# arrives as a role=system message and is merged into the SAME system message as the
# admin/model prompt, joined by a newline — so the two become indistinguishable strings
# in the same role, with the user's text last. Position is not precedence: "disregard the
# above" in that box frequently wins.
#
# With isolation on, the user's text is instead fenced in a labelled <user_preferences>
# block that states it is user input rather than policy, and a short precedence reminder
# is appended AFTER it so the last word in the system message belongs to the operator.
# This does not make prompt injection impossible — nothing does — it removes the specific
# ambiguity that makes it trivial. Personalization still works: tone, format, persona and
# detail level all live happily inside the block.
#
# The char cap bounds a field that is re-sent on EVERY turn (a 4k blob is ~1k tokens per
# request, ~20k over a 20-turn chat, times 10K users). 4000 is far wider than any real
# persona needs; anything longer is a document, which is what file upload is for.
# 0 disables either guard. Plain env reads — take effect on restart.
ENABLE_CHAT_SYSTEM_PROMPT_ISOLATION = os.getenv('ENABLE_CHAT_SYSTEM_PROMPT_ISOLATION', 'True').lower() == 'true'

try:
    CHAT_SYSTEM_PROMPT_MAX_CHARS = int(os.getenv('CHAT_SYSTEM_PROMPT_MAX_CHARS', '4000'))
except (ValueError, TypeError):
    CHAT_SYSTEM_PROMPT_MAX_CHARS = 4000


# Sunway: apply the guardrails PII redaction to the STORED chat record, not only to the
# copy sent to the model provider (security review, to-be-reviewed-later §2).
#
# Why this exists. The guardrails filter rewrites the request body on its way to the
# provider, but the chat record is saved by a SEPARATE frontend call carrying the
# frontend's own unfiltered history. The two paths never met, so a real NRIC reached the
# production `chat` table, its backups and its exports while the provider only ever saw
# the redacted form. Worse, `notify_on_redaction` had already told the user "Sensitive
# data was removed before sending" — the platform was announcing a protection it was not
# delivering to storage.
#
# THE TRADE, taken deliberately: with this on, a user can no longer re-read exactly what
# they typed. Their own NRIC comes back as [REDACTED_NRIC] after a reload. In-flight the
# frontend still shows the original, so the change is visible only once the text has
# become a stored record — which is the point at which it is the thing being protected.
#
# Default ON because it is the PDPA-defensible posture, and a flag rather than hard-wired
# because "can users see their own raw input?" is a policy question that may be answered
# differently later. Plain env — takes effect on restart, no PersistentConfig trap.
ENABLE_STORAGE_REDACTION = os.getenv('ENABLE_STORAGE_REDACTION', 'True').lower() == 'true'


# Retention: max chats a user may keep (ALL roles incl. admins), enforced as a
# hard cap on chat creation ("delete one to create a new one"). 0 disables the
# cap. The 1-month rolling expiry sweep is a separate mechanism.
try:
    MAX_CHATS_PER_USER = int(os.getenv('MAX_CHATS_PER_USER', '30'))
except (ValueError, TypeError):
    MAX_CHATS_PER_USER = 30

# Retention sweep: rolling deletion of chats (and the files/vectors they own
# exclusively) whose last activity is older than CHAT_RETENTION_DAYS. 0 disables
# the sweep. INTERVAL throttles how often it runs (cluster-wide, via a Redis
# lock); BATCH caps chats purged per run so Qdrant/storage aren't hammered.
try:
    CHAT_RETENTION_DAYS = int(os.getenv('CHAT_RETENTION_DAYS', '30'))
except (ValueError, TypeError):
    CHAT_RETENTION_DAYS = 30
try:
    RETENTION_SWEEP_INTERVAL = int(os.getenv('RETENTION_SWEEP_INTERVAL', '3600'))
except (ValueError, TypeError):
    RETENTION_SWEEP_INTERVAL = 3600
try:
    RETENTION_SWEEP_BATCH = int(os.getenv('RETENTION_SWEEP_BATCH', '100'))
except (ValueError, TypeError):
    RETENTION_SWEEP_BATCH = 100

# Chat archive feature. Default on (upstream behavior). When false, users cannot
# archive chats — the archive endpoints reject it and the UI hides the controls;
# unarchiving an already-archived chat is still allowed so any can be recovered.
ENABLE_CHAT_ARCHIVE = os.getenv('ENABLE_CHAT_ARCHIVE', 'False').lower() == 'true'

# Sdeck (Presenton) MCP tool server. Default OFF: the team deferred the rollout to Sdeck
# phase 2, so the deck-generation tools must not reach users yet. When false, the catalogue
# attaches no toolIds to any model (model_catalogue.py), which is the whole mechanism -- a
# model only reaches an MCP server through its own meta.toolIds.
#
# NOTHING is removed by turning this off. The MCP connection stays configured in Admin
# Settings -> Integrations, Open WebUI's MCP client is upstream code that is not touched, and
# schat never had Sdeck-specific code of its own (see CLAUDE.md -- the whole integration is
# config on this side, and the code changes all live in the Sdeck repo). Phase 2 is this flag
# plus a restart.
ENABLE_SDECK_MCP = os.getenv('ENABLE_SDECK_MCP', 'False').lower() == 'true'

# The Sdeck MCP server's info.id, as configured in TOOL_SERVER_CONNECTIONS. model_catalogue.py
# builds each model's toolIds as `server:mcp:<this>`, and routers/tools.py resolves a tool
# server by exact info.id match -- so this must equal TOOL_SERVER_CONNECTIONS' info.id verbatim
# in every environment, or the model's toolIds silently point at a server that doesn't exist
# (no error; the tool just never appears). Previously hardcoded to "SDeck Staging" directly in
# model_catalogue.py, which meant production's manifest had to keep that literal (confusing,
# staging-named) string too. Parameterized 2026-09-17 so every environment can use the same
# plain "SDeck" id instead.
SDECK_MCP_SERVER_ID = os.getenv('SDECK_MCP_SERVER_ID', 'SDeck')

# Voice features (STT mic, TTS read-aloud, Call mode). Default on. When false the
# voice UI is hidden for EVERYONE incl. admins (the per-user chat.stt/tts/call
# permissions only hide it for non-admins). Code is kept — reversible by flipping
# this back to true.
ENABLE_VOICE = os.getenv('ENABLE_VOICE', 'False').lower() == 'true'

# Temporary Chat. Default on (upstream behavior). When false, every entry point is
# hidden/disabled for EVERYONE incl. admins (the per-user chat.temporary permission
# only hides it for non-admins): navbar toggle, Ctrl+Shift+' shortcut, the
# ?temporary-chat=true URL param, temporary_enforced auto-enable, and the
# "Temporary Chat by Default" setting. There is no server-side surface to disable —
# a temporary chat is simply a chat that is never persisted.
ENABLE_TEMPORARY_CHAT = os.getenv('ENABLE_TEMPORARY_CHAT', 'False').lower() == 'true'

# ENABLE_ADMIN_SETTINGS_UI RETIRED 2026-08-17 (hardening plan Items 7 and 9). The flag gated the
# Admin Settings page, which wrote PROCESS-GLOBAL config reachable by any tenant admin. That page
# is now deleted rather than gated: configuration comes from the Helm chart and model definitions
# from model_catalogue.py. A deleted surface needs no flag, and leaving one implies a capability
# that no longer exists. Anything still setting this in a values file is inert and can be dropped.

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

# Timeout (in seconds) for the MCP session.initialize() handshake.
# The handshake performs a list-tools round-trip and can take tens of
# seconds on cold-start servers or servers exposing many tools.
MCP_INITIALIZE_TIMEOUT = os.getenv('MCP_INITIALIZE_TIMEOUT', '10')
try:
    MCP_INITIALIZE_TIMEOUT = int(MCP_INITIALIZE_TIMEOUT)
except (ValueError, TypeError):
    MCP_INITIALIZE_TIMEOUT = 10


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
# No hardcoded fallback by design: the supported start scripts set/auto-generate it; unset is rejected below.
WEBUI_SECRET_KEY = os.getenv(
    'WEBUI_SECRET_KEY',
    os.getenv('WEBUI_JWT_SECRET_KEY', ''),
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
    raise SystemExit(
        'WEBUI_SECRET_KEY is not set. It is a hard requirement when authentication is enabled.\n'
        'The supported start methods set or auto-generate it for you: use start.sh (Linux/macOS), '
        'start_windows.bat (Windows), or `open-webui serve`.\n'
        'If you start the backend another way (e.g. invoking uvicorn directly, which is unsupported), '
        'you must set WEBUI_SECRET_KEY yourself to a long random value.\n'
        'See https://docs.openwebui.com/reference/env-configuration#webui_secret_key'
    )

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
BYPASS_RETRIEVAL_ACCESS_CONTROL = os.getenv('BYPASS_RETRIEVAL_ACCESS_CONTROL', 'False').lower() == 'true'

# When True, collection names that do not match any known file-*, user-memory-*,
# web-search-*, or knowledge-base collection are allowed through access control
# for non-admin users.  When False (default), unknown collection names are
# denied — closing the legacy unscoped namespace.
ENABLE_RETRIEVAL_UNSCOPED_COLLECTIONS = os.getenv('ENABLE_RETRIEVAL_UNSCOPED_COLLECTIONS', 'False').lower() == 'true'

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
# Sunway SChat.ai branding: use the configured WEBUI_NAME verbatim.
# (Upstream appends " (Open WebUI)" to any custom name — disabled for our rebrand.)

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

# Max stored length (bytes) of a data:image profile URI; bounds Postgres/Redis
# bloat from inline avatars and model icons. Unset (default) disables the cap.
_profile_image_max_data_uri_size = os.getenv('PROFILE_IMAGE_MAX_DATA_URI_SIZE', '').strip()
PROFILE_IMAGE_MAX_DATA_URI_SIZE = int(_profile_image_max_data_uri_size) if _profile_image_max_data_uri_size else None

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

# If set while ENABLE_FORWARD_USER_INFO_HEADERS is True, send one signed HS256 JWT
# (FORWARD_USER_INFO_HEADER_JWT) instead of separate X-OpenWebUI-User-* headers.
FORWARD_USER_INFO_HEADER_JWT_SECRET = (os.environ.get('FORWARD_USER_INFO_HEADER_JWT_SECRET') or '').strip() or None
FORWARD_USER_INFO_HEADER_JWT = os.environ.get('FORWARD_USER_INFO_HEADER_JWT', 'X-OpenWebUI-User-Jwt')
try:
    FORWARD_USER_INFO_HEADER_JWT_EXPIRES_SECONDS = int(
        os.environ.get('FORWARD_USER_INFO_HEADER_JWT_EXPIRES_SECONDS', '300')
    )
except ValueError:
    FORWARD_USER_INFO_HEADER_JWT_EXPIRES_SECONDS = 300

####################################
# Progressive Web App
####################################

EXTERNAL_PWA_MANIFEST_URL = os.getenv('EXTERNAL_PWA_MANIFEST_URL', None)

####################################
# Catalogue landing page
####################################

# Public URL of the catalogue this app is listed in. When set, a visitor with no
# session is sent here instead of being shown a sign-in page, after a SILENT SSO
# attempt (`prompt=none`) has established that they are not signed in upstream
# either. The catalogue owns logging people in; schat then picks the session up
# from the shared upstream IdP session without a second prompt.
#
# Leave empty to keep the built-in sign-in page (the previous behaviour).
#
# Must be an ABSOLUTE http(s) URL. A relative value is rejected below, because a
# same-origin value would bounce the visitor straight back here and loop.
#
# NOTE for whoever configures the catalogue: its link to this app must be a plain
# link, NOT an automatic redirect. schat → catalogue → schat would loop if both
# sides redirect automatically, and no guard on this side can prevent that.
LANDING_PAGE_URL = (os.environ.get('LANDING_PAGE_URL') or '').strip() or None
if LANDING_PAGE_URL and not LANDING_PAGE_URL.startswith(('http://', 'https://')):
    log.error(
        'LANDING_PAGE_URL=%r is not an absolute http(s) URL; ignoring it and falling '
        'back to the built-in sign-in page.',
        LANDING_PAGE_URL,
    )
    LANDING_PAGE_URL = None

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

# Sunway: hard cap on how many images generate_image may produce for a SINGLE chat
# request. The iteration limit above bounds tool-call *rounds*, not the number of
# parallel calls within a round — so a small model that runs away emitting dozens of
# generate_image calls in one turn (observed: Qwen3.6 35B A3B, "Exploring 34
# generate_image" and climbing) is otherwise unbounded, burning generations + files
# (each counts against retention). Excess image calls beyond this cap are dropped
# before execution. Plain env (re-read each restart). Set to -1 for unlimited.
IMAGE_GENERATION_MAX_PER_REQUEST = os.getenv('IMAGE_GENERATION_MAX_PER_REQUEST', '4')
try:
    IMAGE_GENERATION_MAX_PER_REQUEST = int(IMAGE_GENERATION_MAX_PER_REQUEST)
except Exception:
    IMAGE_GENERATION_MAX_PER_REQUEST = 4
if IMAGE_GENERATION_MAX_PER_REQUEST == -1:
    IMAGE_GENERATION_MAX_PER_REQUEST = None


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

# Sunway: default OFF (upstream default is 'true'). schat must not phone home to GitHub
# or surface upstream release numbers -- the product is versioned by SCHAT_VERSION.
ENABLE_VERSION_UPDATE_CHECK = os.getenv('ENABLE_VERSION_UPDATE_CHECK', 'false').lower() == 'true'
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


####################################
# MULTI-TENANCY (schat data-plane ↔ IAM control-plane)
####################################
#
# schat becomes multi-tenant by delegating tenant resolution to the in-house
# IAM microservice: it verifies the WorkOS token, confirms the user's
# membership in the requested business unit, and brokers that BU's data-store
# connection (Postgres DB, Qdrant collection prefix, object-store bucket/prefix).
#
# All of this is INERT unless ENABLE_MULTI_TENANCY is true. With the flag off,
# schat behaves exactly as the single-tenant fork does today (no engine
# registry, no tenant middleware, no per-tenant prefixing).
#
# See MULTITENANCY_ACTION_PLAN.md and IAM_INTEGRATION_GUIDE.md.

ENABLE_MULTI_TENANCY = os.getenv('ENABLE_MULTI_TENANCY', 'False').lower() == 'true'

# IAM control-plane service (the /resolve broker). TLS only in real envs.
IAM_BASE_URL = (os.environ.get('IAM_BASE_URL') or '').strip().rstrip('/') or None
# Service-to-service credentials schat presents on s2s endpoints. Keep in a
# secrets manager / env — never in code. The IAM service client must hold the
# scopes `tenant.resolve` and `tenant.connection.read`.
IAM_CLIENT_ID = (os.environ.get('IAM_CLIENT_ID') or '').strip() or None
IAM_CLIENT_SECRET = (os.environ.get('IAM_CLIENT_SECRET') or '').strip() or None
# Network timeout (seconds) for calls to IAM. Fail closed on timeout.
IAM_HTTP_TIMEOUT = float(os.getenv('IAM_HTTP_TIMEOUT', '10.0'))
# Verify TLS on the IAM connection. Corporate TLS interception in dev may need
# this false (mirrors AIOHTTP_CLIENT_SESSION_SSL); keep TRUE in prod.
IAM_VERIFY_SSL = os.getenv('IAM_VERIFY_SSL', 'True').lower() == 'true'
# How long (seconds) to cache a tenant's brokered connection bundle. Bundles
# change rarely — IAM is a cache-miss dependency, not a per-request hop.
TENANT_BUNDLE_CACHE_TTL = int(os.getenv('TENANT_BUNDLE_CACHE_TTL', '300'))
# Max number of per-tenant DB engines held in the registry before LRU eviction
# (each engine holds a small connection pool; keep the product under Postgres
# max_connections).
TENANT_ENGINE_CACHE_SIZE = int(os.getenv('TENANT_ENGINE_CACHE_SIZE', '50'))
# Per-tenant connection pool sizing. Every tenant gets its OWN pool.
#
# Default is a MINIMAL POOL (1 resident, bursting to 3) rather than no pool, and it
# only works because TENANT_ENGINE_IDLE_TIMEOUT below reclaims idle engines. That
# pairing is the whole design:
#
#   without idle eviction  -> resident connections scale with EVERY tenant ever
#                             touched, which is unbounded as tenants are added
#   with idle eviction     -> resident connections scale with tenants ACTIVE in the
#                             last TENANT_ENGINE_IDLE_TIMEOUT seconds
#
# With many tenants but few users each, "active right now" stays small however long
# the tenant list grows — so 1 resident connection per active tenant is ample, and
# a pooled checkout stays cheap (~3ms vs ~10ms for a fresh connect, measured).
#
# Keeping a pool also keeps a HARD CAP: requests beyond POOL_SIZE + MAX_OVERFLOW
# queue and wait (pool_timeout) instead of piling more connections onto Postgres.
# That backpressure is what protects `max_connections` during a traffic spike.
#
# Budget: (active tenants x POOL_SIZE) resident, peaking at
# (active tenants x (POOL_SIZE + MAX_OVERFLOW)), times the replica count — all of
# which must stay under Postgres `max_connections` (default 100).
#
# 0 selects NullPool instead: no pooled connections at all, connect per checkout.
# That removes idle connections entirely, but pays a connect on EVERY DB-touching
# request and removes the cap, so a concurrency spike can exhaust `max_connections`
# faster than pooling would. Appropriate for very spiky/serverless deployments, not
# for an interactive chat app.
TENANT_DB_POOL_SIZE = int(os.getenv('TENANT_DB_POOL_SIZE', '1'))
TENANT_DB_MAX_OVERFLOW = int(os.getenv('TENANT_DB_MAX_OVERFLOW', '2'))
# Dispose a tenant's engine after this many seconds with no request for it, which
# releases its pooled connections. 0 disables idle eviction (size-based LRU only).
#
# THIS IS WHAT MAKES THE POOL ABOVE VIABLE at high tenant counts, and it is
# load-bearing rather than an optimisation: SQLAlchemy's QueuePool never shrinks
# below pool_size on its own — only overflow connections close on return, and
# pool_recycle acts at checkout, not on idle time. Without this, a tenant someone
# opened once at 09:00 pins its connection until the pod restarts, and the total
# grows with every tenant ever visited.
#
# The value is a trade: shorter reclaims connections sooner but makes the first
# request after a quiet spell pay a fresh connect. 300s suits an interactive app —
# a user mid-session never notices it, an abandoned tenant frees up within minutes.
#
# Under NullPool (TENANT_DB_POOL_SIZE=0) there are no connections to reclaim, so
# this only bounds engine-object memory and can be much longer.
#
# Known gap: the sweep is lazy (it runs on tenant requests), so a completely idle
# pod reclaims nothing until the next request. `max_connections` is shared with
# every other service in the cluster, so if that residue matters, PgBouncer in
# front of Postgres is the real fix rather than a shorter timeout here.
TENANT_ENGINE_IDLE_TIMEOUT = int(os.getenv('TENANT_ENGINE_IDLE_TIMEOUT', '300'))
# Seconds to wait for the TCP connect + auth handshake to a tenant's Postgres.
#
# WITHOUT this the OS default applies (~127s of SYN retries on Linux), so a tenant
# whose host is wrong or firewalled HANGS the request for over two minutes instead
# of erroring — the browser just spins, and uvicorn has no request timeout to cut it
# short. Note pool_timeout does NOT cover this: that bounds waiting for a POOL SLOT,
# not the connect itself, so it never fires on a fresh connection.
#
# Same failure shape as an S3 endpoint with a missing port: reachable-looking host,
# nothing answering, no timeout, indefinite hang. Fail fast instead — a wrong
# connection should surface as an error in seconds.
TENANT_DB_CONNECT_TIMEOUT = int(os.getenv('TENANT_DB_CONNECT_TIMEOUT', '10'))
# TCP keepalive for tenant connections, so a SILENTLY dead peer (pod evicted, NAT
# entry dropped, blackholed route) is detected instead of the socket blocking on a
# read forever. connect_timeout only covers establishing the connection; these cover
# a connection that was fine and then quietly died. Detection takes roughly
# idle + (interval x count) seconds.
TENANT_DB_KEEPALIVES_IDLE = int(os.getenv('TENANT_DB_KEEPALIVES_IDLE', '30'))
TENANT_DB_KEEPALIVES_INTERVAL = int(os.getenv('TENANT_DB_KEEPALIVES_INTERVAL', '10'))
TENANT_DB_KEEPALIVES_COUNT = int(os.getenv('TENANT_DB_KEEPALIVES_COUNT', '3'))
# The header carrying the active business-unit slug on every REST/WS request.
TENANT_ID_HEADER = os.getenv('TENANT_ID_HEADER', 'X-Tenant-Id')

# --- WorkOS session-token verification (local JWKS) ---------------------------
# schat verifies the WorkOS JWT itself (RS256 against the JWKS) so entitlement
# stays a cache-miss hop, not a per-request one. These MUST match the IAM
# service's WORKOS_CLAIM_* config so both sides read the same claims.
WORKOS_JWKS_URL = (os.environ.get('WORKOS_JWKS_URL') or '').strip() or None
WORKOS_ISSUER = (os.environ.get('WORKOS_ISSUER') or '').strip() or None
WORKOS_AUDIENCE = (os.environ.get('WORKOS_AUDIENCE') or '').strip() or None
# Claim-name mapping (IAM defaults). Override in lockstep with IAM if the real
# WorkOS token uses different names — do NOT hardcode elsewhere.
WORKOS_CLAIM_USER_ID = os.getenv('WORKOS_CLAIM_USER_ID', 'sub')
WORKOS_CLAIM_ORG_ID = os.getenv('WORKOS_CLAIM_ORG_ID', 'org_id')
WORKOS_CLAIM_EMAIL = os.getenv('WORKOS_CLAIM_EMAIL', 'email')
WORKOS_CLAIM_NAME = os.getenv('WORKOS_CLAIM_NAME', 'name')

# --- WorkOS organizations, for pinning the silent sign-in probe ----------------
# A `prompt=none` probe only works if WorkOS can tell WHICH connection to check.
# Against the org-less `authkit` selector (our OAUTH_AUTHORIZE_PARAMS default) it
# cannot, so instead of failing cleanly with login_required it renders the WorkOS
# hosted login page — a visible prompt the user never asked for. Pinning
# `organization_id` routes the probe straight at the Microsoft AD connection,
# which either answers from the live session or errors.
#
# Same names and same domain split as the presenton deployment, so the two apps
# can be configured from one place.
WORKOS_ORGANIZATION_ID = (os.environ.get('WORKOS_ORGANIZATION_ID') or '').strip() or None
WORKOS_ORGANIZATION_ID_EDU = (os.environ.get('WORKOS_ORGANIZATION_ID_EDU') or '').strip() or None

# Email domain routed to the education tenant. Hardcoded rather than configurable:
# it is a fact about which AD org owns which domain, not a deployment choice, and
# an env var here would just be a second place for the two apps to disagree.
WORKOS_EDU_EMAIL_DOMAIN = 'sunway.edu.my'


# --- Sunway: security response header defaults --------------------------------
# Baseline security headers, defaulted IN CODE rather than left to each manifest.
#
# Why here and not the Helm values: upstream's utils/security_headers.py emits a
# header only when its env var is set, so an unset var means NO header and no
# warning. Every deployment surface (staging, a future production, and every dev
# machine — dev.ps1 seeds no flags by design) would have to remember all eight.
# That is the same failure mode as the 2026-07-31 feature-flag change recorded in
# CLAUDE.md, and it is not hypothetical here: the manifest's values.yaml has
# measurably drifted behind values.staging.yaml, and values.production.yaml is
# still missing most of its configuration.
#
# HOW THIS WORKS, and why security_headers.py is untouched: setdefault only writes
# when the key is absent, and set_security_headers() re-reads os.environ on every
# request. So the value below is a floor, a real env var still wins, and upstream's
# file keeps zero Sunway edits — nothing to reconcile on the next upstream-sync.
#
# HOW TO OPT OUT PER DEPLOYMENT — and NOT the way you would guess. An empty string
# does NOT work through the Helm chart: templates/configmap.yaml:68 skips any key
# whose value is "" (`ne (toString $value) ""`), so the variable ends up ABSENT from
# the container, setdefault then re-applies the value below, and the header comes
# back. The chart's own comment says there is no way to force an empty string from
# values. Verified the hard way on staging 2026-08-11: CONTENT_SECURITY_POLICY: ""
# in the overlay left the enforcing CSP live.
#
# Real options, in order of preference:
#   1. change the default here (needs an image build — this is the honest one);
#   2. set a deliberately inert VALUE in the overlay, e.g. a permissive CSP —
#      non-empty, so the chart keeps it;
#   3. add the var to the Deployment's own `env:` list, which is what the chart
#      comment recommends for the genuinely-empty case.
# On Windows dev, note `$env:X = ''` DELETES the variable rather than emptying it,
# so option 2 is the only one that works in dev.ps1 either.
#
# Deliberately NOT defaulted:
#   CROSS_ORIGIN_EMBEDDER_POLICY - "require-corp" blocks any cross-origin
#       subresource lacking its own CORP header, which includes MinIO presigned
#       image URLs and external images pasted into chat. Its only real benefit is
#       enabling SharedArrayBuffer, which schat does not use.
#   CACHE_CONTROL - applies to EVERY response including immutable JS/CSS bundles.
#   CONTENT_SECURITY_POLICY / _REPORT_ONLY - the only two that can break the app
#       outright (SvelteKit inline styles, wss:, MinIO + external images, srcdoc
#       artifact iframes) and the ones needing per-deployment tuning. Keep them in
#       the manifest, report-only first, and promote once the reports are quiet.
_SECURITY_HEADER_DEFAULTS = {
    'XCONTENT_TYPE': 'nosniff',
    # SAMEORIGIN, one of the two values the security brief names. DENY is also safe
    # today (nothing frames schat — the prompt=none silent SSO probe is a full-page
    # redirect, not a hidden iframe) but SAMEORIGIN leaves room for an
    # intranet-portal embed without another image build.
    'XFRAME_OPTIONS': 'SAMEORIGIN',
    'REFERRER_POLICY': 'strict-origin-when-cross-origin',
    # geolocation=(self) per the security brief's own example. NO SPACES AFTER THE
    # COMMAS — the regex in security_headers.py rejects "geolocation=(self),
    # microphone=()" and the failure is SILENT: it falls back to the literal string
    # "none", which is not a valid Permissions-Policy value, so browsers ignore the
    # header entirely while a scanner still reports it as present.
    'PERMISSIONS_POLICY': (
        'geolocation=(self),microphone=(),camera=(),payment=(),usb=(),midi=(),accelerometer=(),gyroscope=(),magnetometer=()'
    ),
    # same-origin is safe: there is no popup in any auth path — every branch of
    # src/routes/auth/+page.svelte navigates via window.location.href. Revisit if a
    # popup login or a Drive/OneDrive picker is ever enabled.
    'CROSS_ORIGIN_OPENER_POLICY': 'same-origin',
    'CROSS_ORIGIN_RESOURCE_POLICY': 'same-origin',
    # COEP: set to the brief's value on request, AGAINST the recommendation above.
    # require-corp blocks every cross-origin subresource that does not send its own
    # CORP header. Same-origin traffic is unaffected (uploaded files and model
    # avatars are proxied through /api/..., not fetched from MinIO directly), so the
    # exposure is external images referenced by URL in chat, and third-party
    # thumbnails in web-search results.
    #
    # 'credentialless', NOT 'require-corp'. Measured on staging 2026-08-11: with
    # require-corp, an image pasted into a chat as markdown from another host failed
    # with net::ERR_BLOCKED_BY_RESPONSE.NotSameOriginAfterDefaultedToSameOriginByCoep
    # and rendered as a broken placeholder. require-corp demands every cross-origin
    # subresource send its own CORP header, which public CDNs generally do not.
    #
    # credentialless keeps the isolation COEP exists for but fetches cross-origin
    # no-cors subresources WITHOUT credentials instead of requiring CORP — which is
    # exactly right here, since an external image in a chat message is public and
    # needs no cookies. Browsers that do not know the value treat it as unsafe-none,
    # i.e. they simply do not enforce COEP, so it degrades gracefully.
    #
    # Do NOT "fix" a future COEP breakage by going back to require-corp and adding
    # hosts somewhere — there is nowhere to add them; the remote server decides.
    'CROSS_ORIGIN_EMBEDDER_POLICY': 'credentialless',
    # CSP: REPORT-ONLY, reverted from enforcing after it took staging down.
    #
    # Measured 2026-08-11 with 'CONTENT_SECURITY_POLICY' (enforcing): the app served
    # only #splash-screen and never hydrated. Chrome blocked THREE inline scripts
    # under script-src 'self' — src/app.html:31 (resizeIframe), src/app.html:37
    # (theme initialiser), and (index):178, which is SvelteKit's hydration/start
    # script INJECTED AT BUILD TIME. The third is fatal and does not appear in
    # src/app.html at all, which is why reviewing only the source template wrongly
    # suggested the app would still boot.
    #
    # Hash-pinning does not rescue it: SvelteKit's start script embeds build-specific
    # module ids and hydration data, so its sha256 changes on every build.
    #
    # FURTHER violations found once report-only was live on staging 2026-08-11 — this
    # is the full list of what an enforcing policy would break, and it is longer than
    # the three scripts above:
    #
    #   4. connect-src was missing data: — fetcher.js:77 fetches
    #      data:image/jpeg;base64,... URLs on the image path. Fixed below by adding
    #      data: and blob: to connect-src.
    #   5. ARTIFACT inline scripts (about:srcdoc:45) violate script-src, and this one
    #      CANNOT be fixed by hashing or externalising: artifact HTML is generated by
    #      the model, so its hash differs every single response. Under an enforcing
    #      page-level CSP, interactive artifacts (buttons, charts, anything scripted)
    #      stop working. The only real answer is a SEPARATE policy for those iframes
    #      via the IFRAME_CSP env var (config.py:2653) — scope that as its own piece
    #      of work, do not try to widen this header to cover it.
    #   6. CORP blocks subresources requested BY artifact iframes (app.js, style.css
    #      failed with ERR_BLOCKED_BY_RESPONSE.NotSameOrigin) because a srcdoc frame
    #      has an opaque origin. Arguably desirable for a sandboxed preview; noted so
    #      it is not mistaken for a regression later.
    #
    # NOT caused by any of this: the "Failed to read a named property
    # 'addEventListener' ... Blocked a frame" SecurityError at Artifacts.svelte:42 was
    # present on staging before any of these headers existed.
    #
    # To make this enforcing later, items 1-4 must be handled AND item 5 moved to
    # IFRAME_CSP: move the two app.html blocks into a same-origin static file, and
    # wire SvelteKit's own CSP support (kit.csp in svelte.config.js) so its nonce
    # matches what this middleware sends. Adding 'unsafe-inline' to script-src would
    # also "work" but removes the main protection CSP exists for.
    #
    # Report-only still satisfies the brief's CSP row as a staged rollout, and still
    # surfaces violations. Passed through with no validation (security_headers.py:143).
    # 'unsafe-inline' on style-src is not optional — SvelteKit and Tailwind emit
    # inline styles; 'wasm-unsafe-eval' covers pyodide; wss: is the Socket.IO
    # channel; blob:/data: are srcdoc artifact iframes and generated images.
    'CONTENT_SECURITY_POLICY_REPORT_ONLY': (
        "default-src 'self'; "
        "img-src 'self' data: blob: https:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'wasm-unsafe-eval'; "
        "connect-src 'self' wss: https: data: blob:; "
        "frame-src 'self' blob: data:; "
        "worker-src 'self' blob:; "
        "font-src 'self' data:"
    ),
    # HSTS is NOT set: it is not on the security brief's list of eight, and adding
    # unrequested headers to a CAB change only widens the review surface. Re-add
    # 'HSTS': 'max-age=31536000;includeSubDomains' if the brief is extended.
}

for _header_var, _header_default in _SECURITY_HEADER_DEFAULTS.items():
    os.environ.setdefault(_header_var, _header_default)

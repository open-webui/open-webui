import importlib.metadata
import json
import logging
import os
import pkgutil
import sys
import shutil
from pathlib import Path
from typing import Optional

import markdown
from bs4 import BeautifulSoup
from open_webui.constants import ERROR_MESSAGES

####################################
# Load .env file
####################################

OPEN_WEBUI_DIR = Path(__file__).parent  # the path containing this file
print(OPEN_WEBUI_DIR)

BACKEND_DIR = OPEN_WEBUI_DIR.parent  # the path containing this file
BASE_DIR = BACKEND_DIR.parent  # the path containing the backend/

print(BACKEND_DIR)
print(BASE_DIR)

try:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(str(BASE_DIR / ".env")))
except ImportError:
    print("dotenv not installed, skipping...")

DOCKER = os.environ.get("DOCKER", "False").lower() == "true"

# device type embedding models - "cpu" (default), "cuda" (nvidia gpu required) or "mps" (apple silicon) - choosing this right can lead to better performance
USE_CUDA = os.environ.get("USE_CUDA_DOCKER", "false")

if USE_CUDA.lower() == "true":
    try:
        import torch

        assert torch.cuda.is_available(), "CUDA not available"
        DEVICE_TYPE = "cuda"
    except Exception as e:
        cuda_error = (
            "Error when testing CUDA but USE_CUDA_DOCKER is true. "
            f"Resetting USE_CUDA_DOCKER to false: {e}"
        )
        os.environ["USE_CUDA_DOCKER"] = "false"
        USE_CUDA = "false"
        DEVICE_TYPE = "cpu"
else:
    DEVICE_TYPE = "cpu"

try:
    import torch

    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        DEVICE_TYPE = "mps"
except Exception:
    pass

####################################
# LOGGING
####################################

log_levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]

GLOBAL_LOG_LEVEL = os.environ.get("GLOBAL_LOG_LEVEL", "").upper()
if GLOBAL_LOG_LEVEL in log_levels:
    logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL, force=True)
else:
    GLOBAL_LOG_LEVEL = "INFO"

log = logging.getLogger(__name__)
log.info(f"GLOBAL_LOG_LEVEL: {GLOBAL_LOG_LEVEL}")

if "cuda_error" in locals():
    log.exception(cuda_error)

log_sources = [
    "AUDIO",
    "COMFYUI",
    "CONFIG",
    "DB",
    "IMAGES",
    "MAIN",
    "MODELS",
    "OLLAMA",
    "OPENAI",
    "RAG",
    "WEBHOOK",
    "SOCKET",
    "OAUTH",
    "WORKER",
]

SRC_LOG_LEVELS = {}

for source in log_sources:
    log_env_var = source + "_LOG_LEVEL"
    SRC_LOG_LEVELS[source] = os.environ.get(log_env_var, "").upper()
    if SRC_LOG_LEVELS[source] not in log_levels:
        SRC_LOG_LEVELS[source] = GLOBAL_LOG_LEVEL
    log.info(f"{log_env_var}: {SRC_LOG_LEVELS[source]}")

log.setLevel(SRC_LOG_LEVELS["CONFIG"])


WEBUI_NAME = os.environ.get("WEBUI_NAME", "Pilot GenAI")
# if WEBUI_NAME != "Open WebUI":
#     WEBUI_NAME += " (Open WebUI)"

WEBUI_FAVICON_URL = "https://openwebui.com/favicon.png"

TRUSTED_SIGNATURE_KEY = os.environ.get("TRUSTED_SIGNATURE_KEY", "")

####################################
# ENV (dev,test,prod)
####################################

ENV = os.environ.get("ENV", "dev")

FROM_INIT_PY = os.environ.get("FROM_INIT_PY", "False").lower() == "true"

if FROM_INIT_PY:
    PACKAGE_DATA = {"version": importlib.metadata.version("open-webui")}
else:
    try:
        PACKAGE_DATA = json.loads((BASE_DIR / "package.json").read_text())
    except Exception:
        PACKAGE_DATA = {"version": "0.0.0"}


VERSION = PACKAGE_DATA["version"]


# Function to parse each section
def _safe_int_env(env_var: str, default: int, min_value: Optional[int] = None, max_value: Optional[int] = None) -> int:
    """Safely parse integer environment variable with validation.
    
    Args:
        env_var: Environment variable name
        default: Default value if env var is not set or invalid
        min_value: Optional minimum allowed value
        max_value: Optional maximum allowed value
        
    Returns:
        Parsed integer value, or default if parsing fails or value is out of range
    """
    try:
        value = int(os.environ.get(env_var, str(default)))
        if min_value is not None and value < min_value:
            log.warning(f"{env_var}={value} is below minimum {min_value}, using default {default}")
            return default
        if max_value is not None and value > max_value:
            log.warning(f"{env_var}={value} is above maximum {max_value}, using default {default}")
            return default
        return value
    except (ValueError, TypeError) as e:
        log.warning(f"Invalid {env_var} value '{os.environ.get(env_var)}': {e}. Using default {default}")
        return default


def parse_section(section):
    items = []
    for li in section.find_all("li"):
        # Extract raw HTML string
        raw_html = str(li)

        # Extract text without HTML tags
        text = li.get_text(separator=" ", strip=True)

        # Split into title and content
        parts = text.split(": ", 1)
        title = parts[0].strip() if len(parts) > 1 else ""
        content = parts[1].strip() if len(parts) > 1 else text

        items.append({"title": title, "content": content, "raw": raw_html})
    return items


try:
    changelog_path = BASE_DIR / "CHANGELOG.md"
    with open(str(changelog_path.absolute()), "r", encoding="utf8") as file:
        changelog_content = file.read()

except Exception:
    changelog_content = (pkgutil.get_data("open_webui", "CHANGELOG.md") or b"").decode()


# Convert markdown content to HTML
html_content = markdown.markdown(changelog_content)

# Parse the HTML content
soup = BeautifulSoup(html_content, "html.parser")

# Initialize JSON structure
changelog_json = {}

# Iterate over each version
for version in soup.find_all("h2"):
    version_number = version.get_text().strip().split(" - ")[0][1:-1]  # Remove brackets
    date = version.get_text().strip().split(" - ")[1]

    version_data = {"date": date}

    # Find the next sibling that is a h3 tag (section title)
    current = version.find_next_sibling()

    while current and current.name != "h2":
        if current.name == "h3":
            section_title = current.get_text().lower()  # e.g., "added", "fixed"
            section_items = parse_section(current.find_next_sibling("ul"))
            version_data[section_title] = section_items

        # Move to the next element
        current = current.find_next_sibling()

    changelog_json[version_number] = version_data


CHANGELOG = changelog_json

####################################
# SAFE_MODE
####################################

SAFE_MODE = os.environ.get("SAFE_MODE", "false").lower() == "true"

####################################
# ENABLE_FORWARD_USER_INFO_HEADERS
####################################

ENABLE_FORWARD_USER_INFO_HEADERS = (
    os.environ.get("ENABLE_FORWARD_USER_INFO_HEADERS", "False").lower() == "true"
)


####################################
# WEBUI_BUILD_HASH
####################################

WEBUI_BUILD_HASH = os.environ.get("WEBUI_BUILD_HASH", "dev-build")

####################################
# DATA/FRONTEND BUILD DIR
####################################

DATA_DIR = Path(os.getenv("DATA_DIR", BACKEND_DIR / "data")).resolve()

if FROM_INIT_PY:
    NEW_DATA_DIR = Path(os.getenv("DATA_DIR", OPEN_WEBUI_DIR / "data")).resolve()
    NEW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Check if the data directory exists in the package directory
    if DATA_DIR.exists() and DATA_DIR != NEW_DATA_DIR:
        log.info(f"Moving {DATA_DIR} to {NEW_DATA_DIR}")
        for item in DATA_DIR.iterdir():
            dest = NEW_DATA_DIR / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

        # Zip the data directory
        shutil.make_archive(DATA_DIR.parent / "open_webui_data", "zip", DATA_DIR)

        # Remove the old data directory
        shutil.rmtree(DATA_DIR)

    DATA_DIR = Path(os.getenv("DATA_DIR", OPEN_WEBUI_DIR / "data"))


STATIC_DIR = Path(os.getenv("STATIC_DIR", OPEN_WEBUI_DIR / "static"))

FONTS_DIR = Path(os.getenv("FONTS_DIR", OPEN_WEBUI_DIR / "static" / "fonts"))

FRONTEND_BUILD_DIR = Path(os.getenv("FRONTEND_BUILD_DIR", BASE_DIR / "build")).resolve()

if FROM_INIT_PY:
    FRONTEND_BUILD_DIR = Path(
        os.getenv("FRONTEND_BUILD_DIR", OPEN_WEBUI_DIR / "frontend")
    ).resolve()


####################################
# Database
####################################

# Check if the file exists
if os.path.exists(f"{DATA_DIR}/ollama.db"):
    # Rename the file
    os.rename(f"{DATA_DIR}/ollama.db", f"{DATA_DIR}/webui.db")
    log.info("Database migrated from Ollama-WebUI successfully.")
else:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR}/webui.db")

# Replace the postgres:// with postgresql://
if "postgres://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

DATABASE_SCHEMA = os.environ.get("DATABASE_SCHEMA", None)

DATABASE_POOL_SIZE = os.environ.get("DATABASE_POOL_SIZE", 0)

if DATABASE_POOL_SIZE == "":
    DATABASE_POOL_SIZE = 0
else:
    try:
        DATABASE_POOL_SIZE = int(DATABASE_POOL_SIZE)
    except Exception:
        DATABASE_POOL_SIZE = 0

DATABASE_POOL_MAX_OVERFLOW = os.environ.get("DATABASE_POOL_MAX_OVERFLOW", 0)

if DATABASE_POOL_MAX_OVERFLOW == "":
    DATABASE_POOL_MAX_OVERFLOW = 0
else:
    try:
        DATABASE_POOL_MAX_OVERFLOW = int(DATABASE_POOL_MAX_OVERFLOW)
    except Exception:
        DATABASE_POOL_MAX_OVERFLOW = 0

DATABASE_POOL_TIMEOUT = os.environ.get("DATABASE_POOL_TIMEOUT", 30)

if DATABASE_POOL_TIMEOUT == "":
    DATABASE_POOL_TIMEOUT = 30
else:
    try:
        DATABASE_POOL_TIMEOUT = int(DATABASE_POOL_TIMEOUT)
    except Exception:
        DATABASE_POOL_TIMEOUT = 30

DATABASE_POOL_RECYCLE = os.environ.get("DATABASE_POOL_RECYCLE", 3600)

if DATABASE_POOL_RECYCLE == "":
    DATABASE_POOL_RECYCLE = 3600
else:
    try:
        DATABASE_POOL_RECYCLE = int(DATABASE_POOL_RECYCLE)
    except Exception:
        DATABASE_POOL_RECYCLE = 3600

RESET_CONFIG_ON_START = (
    os.environ.get("RESET_CONFIG_ON_START", "False").lower() == "true"
)


ENABLE_REALTIME_CHAT_SAVE = (
    os.environ.get("ENABLE_REALTIME_CHAT_SAVE", "False").lower() == "true"
)

####################################
# REDIS
####################################

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Redis Sentinel configuration for high availability
# If REDIS_USE_SENTINEL is True, application will use Sentinel instead of direct Redis URL
REDIS_USE_SENTINEL = os.environ.get("REDIS_USE_SENTINEL", "False").lower() == "true"
# Sentinel hosts (comma-separated list, e.g., "redis-sentinel:26379" or "sentinel1:26379,sentinel2:26379")
REDIS_SENTINEL_HOSTS = os.environ.get("REDIS_SENTINEL_HOSTS", "")
# Master name that Sentinel monitors (default: "mymaster")
REDIS_SENTINEL_SERVICE_NAME = os.environ.get("REDIS_SENTINEL_SERVICE_NAME", "mymaster")
# Sentinel password (if required, optional)
REDIS_SENTINEL_PASSWORD = os.environ.get("REDIS_SENTINEL_PASSWORD", None)

# Redis connection pool configuration
# Higher values support more concurrent requests but use more memory
# Default: 100 connections (increased from 50 for high-concurrency environments)
# For multi-replica deployments, each pod maintains its own pool
REDIS_MAX_CONNECTIONS = _safe_int_env("REDIS_MAX_CONNECTIONS", 100, min_value=10, max_value=500)

####################################
# RAG THREAD POOL
####################################

# Thread pool size for RAG (Retrieval Augmented Generation) operations
# RAG operations include: embedding queries, vector search, context retrieval
# Each thread can handle one RAG operation at a time
# Higher values allow more concurrent RAG queries but use more memory/CPU
# Default: 50 threads per pod (supports ~50 concurrent RAG queries per pod)
# For 200 users across 4 pods: 50 × 4 = 200 concurrent RAG operations
# Note: Threads compete for CPU cores, so setting this higher than 2× CPU count
# provides diminishing returns and increases context switching overhead
# Recommended: 50-100 for 4 CPU pods, can go higher with PgBouncer for connection pooling
RAG_THREAD_POOL_SIZE = _safe_int_env("RAG_THREAD_POOL_SIZE", 50, min_value=5, max_value=200)

####################################
# JOB QUEUE (RQ - Redis Queue)
####################################

# Enable/disable job queue for distributed processing
# If False, falls back to FastAPI BackgroundTasks (in-memory, single pod only)
ENABLE_JOB_QUEUE = os.environ.get("ENABLE_JOB_QUEUE", "True").lower() == "true"

# Job timeout in seconds (default: 1 hour for large files)
try:
    JOB_TIMEOUT = int(os.environ.get("JOB_TIMEOUT", "3600"))
    if JOB_TIMEOUT < 60:
        log.warning(f"JOB_TIMEOUT={JOB_TIMEOUT} is too small (minimum 60 seconds), using default 3600")
        JOB_TIMEOUT = 3600
    elif JOB_TIMEOUT > 86400:
        log.warning(f"JOB_TIMEOUT={JOB_TIMEOUT} is too large (maximum 86400 seconds), using default 3600")
        JOB_TIMEOUT = 3600
except (ValueError, TypeError) as e:
    log.warning(f"Invalid JOB_TIMEOUT value '{os.environ.get('JOB_TIMEOUT')}': {e}. Using default 3600")
    JOB_TIMEOUT = 3600

# Maximum number of retries for failed jobs
try:
    JOB_MAX_RETRIES = int(os.environ.get("JOB_MAX_RETRIES", "3"))
    if JOB_MAX_RETRIES < 0:
        log.warning(f"JOB_MAX_RETRIES={JOB_MAX_RETRIES} cannot be negative, using default 3")
        JOB_MAX_RETRIES = 3
    elif JOB_MAX_RETRIES > 10:
        log.warning(f"JOB_MAX_RETRIES={JOB_MAX_RETRIES} is too large (maximum 10), using default 3")
        JOB_MAX_RETRIES = 3
except (ValueError, TypeError) as e:
    log.warning(f"Invalid JOB_MAX_RETRIES value '{os.environ.get('JOB_MAX_RETRIES')}': {e}. Using default 3")
    JOB_MAX_RETRIES = 3

# Retry delay in seconds
try:
    JOB_RETRY_DELAY = int(os.environ.get("JOB_RETRY_DELAY", "60"))
    if JOB_RETRY_DELAY < 1:
        log.warning(f"JOB_RETRY_DELAY={JOB_RETRY_DELAY} is too small (minimum 1 second), using default 60")
        JOB_RETRY_DELAY = 60
    elif JOB_RETRY_DELAY > 3600:
        log.warning(f"JOB_RETRY_DELAY={JOB_RETRY_DELAY} is too large (maximum 3600 seconds), using default 60")
        JOB_RETRY_DELAY = 60
except (ValueError, TypeError) as e:
    log.warning(f"Invalid JOB_RETRY_DELAY value '{os.environ.get('JOB_RETRY_DELAY')}': {e}. Using default 60")
    JOB_RETRY_DELAY = 60

# Job result TTL in seconds (default: 1 hour)
try:
    JOB_RESULT_TTL = int(os.environ.get("JOB_RESULT_TTL", "3600"))
    if JOB_RESULT_TTL < 0:
        log.warning(f"JOB_RESULT_TTL={JOB_RESULT_TTL} cannot be negative, using default 3600")
        JOB_RESULT_TTL = 3600
    elif JOB_RESULT_TTL > 604800:  # 7 days
        log.warning(f"JOB_RESULT_TTL={JOB_RESULT_TTL} is too large (maximum 604800 seconds), using default 3600")
        JOB_RESULT_TTL = 3600
except (ValueError, TypeError) as e:
    log.warning(f"Invalid JOB_RESULT_TTL value '{os.environ.get('JOB_RESULT_TTL')}': {e}. Using default 3600")
    JOB_RESULT_TTL = 3600

# Job failure TTL in seconds (default: 24 hours)
try:
    JOB_FAILURE_TTL = int(os.environ.get("JOB_FAILURE_TTL", "86400"))
    if JOB_FAILURE_TTL < 0:
        log.warning(f"JOB_FAILURE_TTL={JOB_FAILURE_TTL} cannot be negative, using default 86400")
        JOB_FAILURE_TTL = 86400
    elif JOB_FAILURE_TTL > 604800:  # 7 days
        log.warning(f"JOB_FAILURE_TTL={JOB_FAILURE_TTL} is too large (maximum 604800 seconds), using default 86400")
        JOB_FAILURE_TTL = 86400
except (ValueError, TypeError) as e:
    log.warning(f"Invalid JOB_FAILURE_TTL value '{os.environ.get('JOB_FAILURE_TTL')}': {e}. Using default 86400")
    JOB_FAILURE_TTL = 86400

####################################
# WEBUI_AUTH (Required for security)
####################################

WEBUI_AUTH = os.environ.get("WEBUI_AUTH", "True").lower() == "true"
WEBUI_AUTH_TRUSTED_EMAIL_HEADER = os.environ.get(
    "WEBUI_AUTH_TRUSTED_EMAIL_HEADER", None
)
WEBUI_AUTH_TRUSTED_NAME_HEADER = os.environ.get("WEBUI_AUTH_TRUSTED_NAME_HEADER", None)

BYPASS_MODEL_ACCESS_CONTROL = (
    os.environ.get("BYPASS_MODEL_ACCESS_CONTROL", "False").lower() == "true"
)

####################################
# WEBUI_SECRET_KEY
####################################

WEBUI_SECRET_KEY = os.environ.get(
    "WEBUI_SECRET_KEY",
    os.environ.get(
        "WEBUI_JWT_SECRET_KEY", "t0p-s3cr3t"
    ),  # DEPRECATED: remove at next major version
)

WEBUI_SESSION_COOKIE_SAME_SITE = os.environ.get("WEBUI_SESSION_COOKIE_SAME_SITE", "lax")

WEBUI_SESSION_COOKIE_SECURE = (
    os.environ.get("WEBUI_SESSION_COOKIE_SECURE", "false").lower() == "true"
)

WEBUI_AUTH_COOKIE_SAME_SITE = os.environ.get(
    "WEBUI_AUTH_COOKIE_SAME_SITE", WEBUI_SESSION_COOKIE_SAME_SITE
)

WEBUI_AUTH_COOKIE_SECURE = (
    os.environ.get(
        "WEBUI_AUTH_COOKIE_SECURE",
        os.environ.get("WEBUI_SESSION_COOKIE_SECURE", "false"),
    ).lower()
    == "true"
)

if WEBUI_AUTH and WEBUI_SECRET_KEY == "":
    raise ValueError(ERROR_MESSAGES.ENV_VAR_NOT_FOUND)

ENABLE_WEBSOCKET_SUPPORT = (
    os.environ.get("ENABLE_WEBSOCKET_SUPPORT", "True").lower() == "true"
)

WEBSOCKET_MANAGER = os.environ.get("WEBSOCKET_MANAGER", "")

WEBSOCKET_REDIS_URL = os.environ.get("WEBSOCKET_REDIS_URL", REDIS_URL)

AIOHTTP_CLIENT_TIMEOUT = os.environ.get("AIOHTTP_CLIENT_TIMEOUT", "")

if AIOHTTP_CLIENT_TIMEOUT == "":
    AIOHTTP_CLIENT_TIMEOUT = None
else:
    try:
        AIOHTTP_CLIENT_TIMEOUT = int(AIOHTTP_CLIENT_TIMEOUT)
    except Exception:
        AIOHTTP_CLIENT_TIMEOUT = 300

AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST = os.environ.get(
    "AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST", ""
)

if AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST == "":
    AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST = None
else:
    try:
        AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST = int(
            AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST
        )
    except Exception:
        AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST = 5

####################################
# OFFLINE_MODE
####################################

OFFLINE_MODE = os.environ.get("OFFLINE_MODE", "false").lower() == "true"

if OFFLINE_MODE:
    os.environ["HF_HUB_OFFLINE"] = "1"

####################################
# AUDIT LOGGING
####################################
ENABLE_AUDIT_LOGS = os.getenv("ENABLE_AUDIT_LOGS", "false").lower() == "true"
# Where to store log file
AUDIT_LOGS_FILE_PATH = f"{DATA_DIR}/audit.log"
# Maximum size of a file before rotating into a new log file
AUDIT_LOG_FILE_ROTATION_SIZE = os.getenv("AUDIT_LOG_FILE_ROTATION_SIZE", "10MB")
# METADATA | REQUEST | REQUEST_RESPONSE
AUDIT_LOG_LEVEL = os.getenv("AUDIT_LOG_LEVEL", "REQUEST_RESPONSE").upper()
try:
    MAX_BODY_LOG_SIZE = int(os.environ.get("MAX_BODY_LOG_SIZE") or 2048)
except ValueError:
    MAX_BODY_LOG_SIZE = 2048

# Comma separated list for urls to exclude from audit
AUDIT_EXCLUDED_PATHS = os.getenv("AUDIT_EXCLUDED_PATHS", "/chats,/chat,/folders").split(
    ","
)
AUDIT_EXCLUDED_PATHS = [path.strip() for path in AUDIT_EXCLUDED_PATHS]
AUDIT_EXCLUDED_PATHS = [path.lstrip("/") for path in AUDIT_EXCLUDED_PATHS]

####################################
# OPENTELEMETRY CONFIGURATION
####################################

# OpenTelemetry master switch
OTEL_ENABLED = os.environ.get("OTEL_ENABLED", "false").lower() == "true"

# Service identification
OTEL_SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", "open-webui")
OTEL_SERVICE_VERSION = VERSION  # Use existing VERSION from package.json

# OTLP exporter configuration (defaults to sidecar pattern)
OTEL_EXPORTER_OTLP_ENDPOINT = os.environ.get(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "http://localhost:4317"  # Standard OTEL Collector sidecar port
)
OTEL_EXPORTER_OTLP_PROTOCOL = os.environ.get(
    "OTEL_EXPORTER_OTLP_PROTOCOL",
    "grpc"
).lower()

# Sampling configuration
OTEL_TRACES_SAMPLER = os.environ.get("OTEL_TRACES_SAMPLER", "parentbased_traceidratio")
try:
    OTEL_TRACES_SAMPLER_ARG = float(os.environ.get("OTEL_TRACES_SAMPLER_ARG", "1.0"))
    if OTEL_TRACES_SAMPLER_ARG < 0.0 or OTEL_TRACES_SAMPLER_ARG > 1.0:
        log.warning(
            f"OTEL_TRACES_SAMPLER_ARG={OTEL_TRACES_SAMPLER_ARG} is out of range [0.0, 1.0], using default 1.0"
        )
        OTEL_TRACES_SAMPLER_ARG = 1.0
except (ValueError, TypeError) as e:
    log.warning(f"Invalid OTEL_TRACES_SAMPLER_ARG value: {e}. Using default 1.0")
    OTEL_TRACES_SAMPLER_ARG = 1.0

# Exporter configuration
OTEL_LOGS_EXPORTER = os.environ.get("OTEL_LOGS_EXPORTER", "none")  # We use Loguru
OTEL_METRICS_EXPORTER = os.environ.get("OTEL_METRICS_EXPORTER", "otlp")

# OpenTelemetry Instrumentation Configuration
OTEL_INSTRUMENTATION_FASTAPI_ENABLED = os.environ.get(
    "OTEL_INSTRUMENTATION_FASTAPI_ENABLED", "true"
).lower() == "true"

OTEL_INSTRUMENTATION_REQUESTS_ENABLED = os.environ.get(
    "OTEL_INSTRUMENTATION_REQUESTS_ENABLED", "true"
).lower() == "true"

# Exclude paths from FastAPI instrumentation (comma-separated)
OTEL_INSTRUMENTATION_FASTAPI_EXCLUDED_PATHS = [
    path.strip()
    for path in os.environ.get(
        "OTEL_INSTRUMENTATION_FASTAPI_EXCLUDED_PATHS", "/health,/health/db,/static"
    ).split(",")
    if path.strip()
]

# Capture request/response headers (comma-separated, empty = none)
OTEL_INSTRUMENTATION_FASTAPI_CAPTURE_HEADERS = [
    header.strip()
    for header in os.environ.get(
        "OTEL_INSTRUMENTATION_FASTAPI_CAPTURE_HEADERS", ""
    ).split(",")
    if header.strip()
]

import os
import sys
import logging
from base64 import b64encode
from bs4 import BeautifulSoup

from pathlib import Path
import json
import yaml

import markdown
import requests
import shutil

from secrets import token_bytes
from constants import ERROR_MESSAGES
import psycopg2
from psycopg2.extensions import register_adapter, AsIs
from psycopg2.extras import DictCursor
from psycopg2.sql import SQL, Identifier
from transformers import GPT2Tokenizer, BertTokenizer
import numpy as np
import tempfile


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

log_sources = [
    "AUDIO",
    "COMFYUI",
    "CONFIG",
    "DB",
    "IMAGES",
    "LITELLM",
    "MAIN",
    "MODELS",
    "OLLAMA",
    "OPENAI",
    "RAG",
    "WEBHOOK",
]

SRC_LOG_LEVELS = {}

for source in log_sources:
    log_env_var = source + "_LOG_LEVEL"
    SRC_LOG_LEVELS[source] = os.environ.get(log_env_var, "").upper()
    if SRC_LOG_LEVELS[source] not in log_levels:
        SRC_LOG_LEVELS[source] = GLOBAL_LOG_LEVEL
    log.info(f"{log_env_var}: {SRC_LOG_LEVELS[source]}")

log.setLevel(SRC_LOG_LEVELS["CONFIG"])

####################################
# Load .env file
####################################

try:
    from dotenv import load_dotenv, find_dotenv

    load_dotenv(find_dotenv("../.env"))
except ImportError:
    logging.warning("dotenv not installed, skipping...")

WEBUI_NAME = os.environ.get("WEBUI_NAME", "Open WebUI")
if WEBUI_NAME != "Open WebUI":
    WEBUI_NAME += " (Open WebUI)"

WEBUI_FAVICON_URL = "https://openwebui.com/favicon.png"

####################################
# ENV (dev,test,prod)
####################################

ENV = os.environ.get("ENV", "dev")

try:
    with open(f"../package.json", "r") as f:
        PACKAGE_DATA = json.load(f)
except:
    PACKAGE_DATA = {"version": "0.0.0"}

VERSION = PACKAGE_DATA["version"]


# Function to parse each section
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
    with open("../CHANGELOG.md", "r") as file:
        changelog_content = file.read()
except:
    changelog_content = ""

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
# DATA/FRONTEND BUILD DIR
####################################

LOCAL_DIR = str(Path(os.getcwd(),"../backend/data").resolve())
FRONTEND_BUILD_DIR = str(Path(os.getenv("FRONTEND_BUILD_DIR", "../build")))


####################################
# Static DIR
####################################

STATIC_DIR = str(Path(os.getenv("STATIC_DIR", "./static")).resolve())

frontend_favicon = f"{FRONTEND_BUILD_DIR}/favicon.png"
if os.path.exists(frontend_favicon):
    shutil.copyfile(frontend_favicon, f"{STATIC_DIR}/favicon.png")
else:
    logging.warning(f"Frontend favicon not found at {frontend_favicon}")

####################################
# CUSTOM_NAME
####################################

CUSTOM_NAME = os.environ.get("CUSTOM_NAME", "")

if CUSTOM_NAME:
    try:
        r = requests.get(f"https://api.openwebui.com/api/v1/custom/{CUSTOM_NAME}")
        data = r.json()
        if r.ok:
            if "logo" in data:
                WEBUI_FAVICON_URL = url = (
                    f"https://api.openwebui.com{data['logo']}"
                    if data["logo"][0] == "/"
                    else data["logo"]
                )

                r = requests.get(url, stream=True)
                if r.status_code == 200:
                    with open(f"{STATIC_DIR}/favicon.png", "wb") as f:
                        r.raw.decode_content = True
                        shutil.copyfileobj(r.raw, f)

            WEBUI_NAME = data["name"]
    except Exception as e:
        log.exception(e)
        pass
else:
    if WEBUI_NAME != "Open WebUI":
        WEBUI_NAME += " (AI Powered Personal Assistant)"

####################################
# DATA/FRONTEND BUILD DIR
####################################
# Nextcloud environment variables
HEADERS = {
        'OCS-APIRequest': 'true',
        'Content-Type': 'application/octet-stream',
    }
NEXTCLOUD_USERNAME = os.getenv("NEXTCLOUD_USERNAME")  
NEXTCLOUD_PASSWORD = os.getenv("NEXTCLOUD_PASSWORD")
NEXTCLOUD_URL = "http://localhost:6060/"

DATA_DIR = os.getenv("DATA_DIR")

response = requests.request("PROPFIND", DATA_DIR, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD),headers=HEADERS)
if not (200 <= response.status_code <= 299):
    response = requests.request("MKCOL", DATA_DIR, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD),headers=HEADERS)
    print("Directory 'data' created successfully." if response.status_code == 201 else f"Failed to create directory 'data'. Status code: {response.status_code}")
else :
    print("Directory 'data' already exists.")
    
FRONTEND_BUILD_DIR = str(Path(os.getenv("FRONTEND_BUILD_DIR", "../build")))
 
try:
    # Read config.json from Nextcloud directory
    response = requests.get(f"{DATA_DIR}/config.json", auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD),headers=HEADERS)
    
    if response.status_code == 200:
        CONFIG_DATA = response.json()
    else:
        print(f"Failed to fetch config.json. Status code: {response.status_code}")
        CONFIG_DATA = {}
except Exception as e:
    # Handle exceptions
    print(f"An error occurred: {e}")
    CONFIG_DATA = {}

####################################
# File Upload DIR 
####################################

UPLOAD_DIR = f"{DATA_DIR}/uploads"
response = requests.request("PROPFIND", UPLOAD_DIR, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD),headers=HEADERS)
if not (200 <= response.status_code <= 299):
    response = requests.request("MKCOL", UPLOAD_DIR, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD),headers=HEADERS)
    print("Directory 'uploads' created successfully." if response.status_code == 201 else f"Failed to create directory 'uploads'. Status code: {response.status_code}")
else :
    print("Directory 'uploads' already exists.")


####################################
# Cache DIR
####################################

CACHE_DIR = f"{DATA_DIR}/cache"
response = requests.request("PROPFIND", CACHE_DIR, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD),headers=HEADERS)
if not (200 <= response.status_code <= 299):
    response = requests.request("MKCOL", CACHE_DIR, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD),headers=HEADERS)
    print("Directory 'cache' created successfully." if response.status_code == 201 else f"Failed to create directory 'uploads'. Status code: {response.status_code}")
else :
    print("Directory 'cache' already exists.")


####################################
# Docs DIR
####################################

DOCS_DIR = f"{DATA_DIR}/docs"
response = requests.request("PROPFIND", DOCS_DIR, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD),headers=HEADERS)
if not (200 <= response.status_code <= 299):
    response = requests.request("MKCOL", DOCS_DIR, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD),headers=HEADERS)
    print("Directory 'docs' created successfully." if response.status_code == 201 else f"Failed to create directory 'uploads'. Status code: {response.status_code}")
else :
    print("Directory 'docs' already exists.")


####################################
# LITELLM_CONFIG
####################################


def create_config_file(file_path):
    directory = os.path.dirname(file_path)

    # Check if directory exists, if not, create it
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Data to write into the YAML file
    config_data = {
        "general_settings": {},
        "litellm_settings": {},
        "model_list": [],
        "router_settings": {},
    }

    # Write data to YAML file
    with open(file_path, "w") as file:
        yaml.dump(config_data, file)


LITELLM_CONFIG_PATH = f"{LOCAL_DIR}/litellm/config.yaml"

if not os.path.exists(LITELLM_CONFIG_PATH):
    log.info("Config file doesn't exist. Creating...")
    create_config_file(LITELLM_CONFIG_PATH)
    log.info("Config file created successfully.")



#################################### 
# OLLAMA_BASE_URL
####################################

OLLAMA_API_BASE_URL = os.environ.get(
    "OLLAMA_API_BASE_URL", "http://localhost:11434/api"
)

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "")
K8S_FLAG = os.environ.get("K8S_FLAG", "")
USE_OLLAMA_DOCKER = os.environ.get("USE_OLLAMA_DOCKER", "false")

if OLLAMA_BASE_URL == "" and OLLAMA_API_BASE_URL != "":
    OLLAMA_BASE_URL = (
        OLLAMA_API_BASE_URL[:-4]
        if OLLAMA_API_BASE_URL.endswith("/api")
        else OLLAMA_API_BASE_URL
    )

if ENV == "prod":
    if OLLAMA_BASE_URL == "/ollama" and not K8S_FLAG:
        if USE_OLLAMA_DOCKER.lower() == "true":
            # if you use all-in-one docker container (Open WebUI + Ollama)
            # with the docker build arg USE_OLLAMA=true (--build-arg="USE_OLLAMA=true") this only works with http://localhost:11434
            OLLAMA_BASE_URL = "http://localhost:11434"
        else:
            OLLAMA_BASE_URL = "http://host.docker.internal:11434"
    elif K8S_FLAG:
        OLLAMA_BASE_URL = "http://ollama-service.open-webui.svc.cluster.local:11434"


OLLAMA_BASE_URLS = os.environ.get("OLLAMA_BASE_URLS", "")
OLLAMA_BASE_URLS = OLLAMA_BASE_URLS if OLLAMA_BASE_URLS != "" else OLLAMA_BASE_URL

OLLAMA_BASE_URLS = [url.strip() for url in OLLAMA_BASE_URLS.split(";")]


####################################
# OPENAI_API
####################################

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_API_BASE_URL = os.environ.get("OPENAI_API_BASE_URL", "")


if OPENAI_API_BASE_URL == "":
    OPENAI_API_BASE_URL = "https://api.openai.com/v1"

OPENAI_API_KEYS = os.environ.get("OPENAI_API_KEYS", "")
OPENAI_API_KEYS = OPENAI_API_KEYS if OPENAI_API_KEYS != "" else OPENAI_API_KEY

OPENAI_API_KEYS = [url.strip() for url in OPENAI_API_KEYS.split(";")]


OPENAI_API_BASE_URLS = os.environ.get("OPENAI_API_BASE_URLS", "")
OPENAI_API_BASE_URLS = (
    OPENAI_API_BASE_URLS if OPENAI_API_BASE_URLS != "" else OPENAI_API_BASE_URL
)

OPENAI_API_BASE_URLS = [
    url.strip() if url != "" else "https://api.openai.com/v1"
    for url in OPENAI_API_BASE_URLS.split(";")
]

OPENAI_API_KEY = ""

try:
    OPENAI_API_KEY = OPENAI_API_KEYS[
        OPENAI_API_BASE_URLS.index("https://api.openai.com/v1")
    ]
except:
    pass

OPENAI_API_BASE_URL = "https://api.openai.com/v1"


####################################
# WEBUI
####################################

ENABLE_SIGNUP = os.environ.get("ENABLE_SIGNUP", "True").lower() == "true"
DEFAULT_MODELS = os.environ.get("DEFAULT_MODELS", None)


DEFAULT_PROMPT_SUGGESTIONS = (
    CONFIG_DATA["ui"]["prompt_suggestions"]
    if "ui" in CONFIG_DATA
    and "prompt_suggestions" in CONFIG_DATA["ui"]
    and type(CONFIG_DATA["ui"]["prompt_suggestions"]) is list
    else [
        {
            "title": ["Help me study", "vocabulary for a college entrance exam"],
            "content": "Help me study vocabulary: write a sentence for me to fill in the blank, and I'll try to pick the correct option.",
        },
        {
            "title": ["Give me ideas", "for what to do with my kids' art"],
            "content": "What are 5 creative things I could do with my kids' art? I don't want to throw them away, but it's also so much clutter.",
        },
        {
            "title": ["Tell me a fun fact", "about the Roman Empire"],
            "content": "Tell me a random fun fact about the Roman Empire",
        },
        {
            "title": ["Show me a code snippet", "of a website's sticky header"],
            "content": "Show me a code snippet of a website's sticky header in CSS and JavaScript.",
        },
        {
            "title": [
                "Explain options trading",
                "if I'm familiar with buying and selling stocks",
            ],
            "content": "Explain options trading in simple terms if I'm familiar with buying and selling stocks.",
        },
        {
            "title": ["Overcome procrastination", "give me tips"],
            "content": "Could you start by asking me about instances when I procrastinate the most and then give me some suggestions to overcome it?",
        },
    ]
)


DEFAULT_USER_ROLE = os.getenv("DEFAULT_USER_ROLE", "pending")

USER_PERMISSIONS_CHAT_DELETION = (
    os.environ.get("USER_PERMISSIONS_CHAT_DELETION", "True").lower() == "true"
)

USER_PERMISSIONS = {"chat": {"deletion": USER_PERMISSIONS_CHAT_DELETION}}

ENABLE_MODEL_FILTER = os.environ.get("ENABLE_MODEL_FILTER", "False").lower() == "true"
MODEL_FILTER_LIST = os.environ.get("MODEL_FILTER_LIST", "")
MODEL_FILTER_LIST = [model.strip() for model in MODEL_FILTER_LIST.split(";")]

WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

ENABLE_ADMIN_EXPORT = os.environ.get("ENABLE_ADMIN_EXPORT", "True").lower() == "true"

####################################
# WEBUI_VERSION
####################################

WEBUI_VERSION = os.environ.get("WEBUI_VERSION", "v1.0.0-alpha.100")

####################################
# WEBUI_AUTH (Required for security)
####################################

WEBUI_AUTH = True
WEBUI_AUTH_TRUSTED_EMAIL_HEADER = os.environ.get(
    "WEBUI_AUTH_TRUSTED_EMAIL_HEADER", None
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

if WEBUI_AUTH and WEBUI_SECRET_KEY == "":
    raise ValueError(ERROR_MESSAGES.ENV_VAR_NOT_FOUND)

####################################
# Postgres/RAG Setup 
####################################
POSTGRES_CONNECTION_STRING = f"dbname='{os.environ.get('POSTGRES_DB')}' user='{os.environ.get('POSTGRES_USER')}' host='{os.environ.get('POSTGRES_HOST')}'  password='{os.environ.get('POSTGRES_PASSWORD')}' port='{os.environ.get('POSTGRES_PORT')}'"
pg_connection = psycopg2.connect(POSTGRES_CONNECTION_STRING)
# this uses the model defined in the Dockerfile ENV variable. If you dont use docker or docker based deployments such as k8s, the default embedding model will be used (sentence-transformers/all-MiniLM-L6-v2)

RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))
RAG_RELEVANCE_THRESHOLD = float(os.environ.get("RAG_RELEVANCE_THRESHOLD", "0.0"))

ENABLE_RAG_HYBRID_SEARCH = (
    os.environ.get("ENABLE_RAG_HYBRID_SEARCH", "").lower() == "true"
)

def adapt_numpy_array(arr):
    return AsIs(arr)

register_adapter(np.ndarray, adapt_numpy_array)

PDF_EXTRACT_IMAGES = os.environ.get("PDF_EXTRACT_IMAGES", "False").lower() == "true"

RAG_EMBEDDING_MODEL_AUTO_UPDATE = (
    os.environ.get("RAG_EMBEDDING_MODEL_AUTO_UPDATE", "").lower() == "true"
)

RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE = (
    os.environ.get("RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE", "").lower() == "true"
)

RAG_RERANKING_MODEL = os.environ.get("RAG_RERANKING_MODEL", "")
if not RAG_RERANKING_MODEL == "":
    log.info(f"Reranking model set: {RAG_RERANKING_MODEL}"),

RAG_RERANKING_MODEL_AUTO_UPDATE = (
    os.environ.get("RAG_RERANKING_MODEL_AUTO_UPDATE", "").lower() == "true"
)

RAG_RERANKING_MODEL_TRUST_REMOTE_CODE = (
    os.environ.get("RAG_RERANKING_MODEL_TRUST_REMOTE_CODE", "").lower() == "true"
)

# device type embedding models - "cpu" (default), "cuda" (nvidia gpu required) or "mps" (apple silicon) - choosing this right can lead to better performance
USE_CUDA = os.environ.get("USE_CUDA_DOCKER", "false")

if USE_CUDA.lower() == "true":
    DEVICE_TYPE = "cuda"
else:
    DEVICE_TYPE = "cpu"
    
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 100

CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "1500"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "100"))

DEFAULT_RAG_TEMPLATE = """Use the following context as your learned knowledge, inside <context></context> XML tags.
<context>
    [context]
</context>

When answer to user:
- If you don't know, just say that you don't know.
- If you don't know when you are not sure, ask for clarification.
Avoid mentioning that you obtained the information from the context.
And answer according to the language of the user's question.

Given the context information, answer the query.
Query: [query]"""

RAG_TEMPLATE = os.environ.get("RAG_TEMPLATE", DEFAULT_RAG_TEMPLATE)

RAG_OPENAI_API_BASE_URL = os.getenv("RAG_OPENAI_API_BASE_URL", OPENAI_API_BASE_URL)
RAG_OPENAI_API_KEY = os.getenv("RAG_OPENAI_API_KEY", OPENAI_API_KEY)

ENABLE_LOCAL_WEB_FETCH = os.getenv("ENABLE_LOCAL_WEB_FETCH", "False").lower() == "true"

####################################
# Transcribe
####################################

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_MODEL_DIR = os.getenv("WHISPER_MODEL_DIR", f"{LOCAL_DIR}/cache//whisper/models")
WHISPER_MODEL_AUTO_UPDATE = (
    os.environ.get("WHISPER_MODEL_AUTO_UPDATE", "").lower() == "true"
)


####################################
# Images
####################################

IMAGE_GENERATION_ENGINE = os.getenv("IMAGE_GENERATION_ENGINE", "")

ENABLE_IMAGE_GENERATION = (
    os.environ.get("ENABLE_IMAGE_GENERATION", "").lower() == "true"
)
AUTOMATIC1111_BASE_URL = os.getenv("AUTOMATIC1111_BASE_URL", "")

COMFYUI_BASE_URL = os.getenv("COMFYUI_BASE_URL", "")

IMAGES_OPENAI_API_BASE_URL = os.getenv(
    "IMAGES_OPENAI_API_BASE_URL", OPENAI_API_BASE_URL
)
IMAGES_OPENAI_API_KEY = os.getenv("IMAGES_OPENAI_API_KEY", OPENAI_API_KEY)

IMAGE_SIZE = os.getenv("IMAGE_SIZE", "512x512")

IMAGE_STEPS = int(os.getenv("IMAGE_STEPS", 50))

IMAGE_GENERATION_MODEL = os.getenv("IMAGE_GENERATION_MODEL", "")

####################################
# Audio
####################################

AUDIO_OPENAI_API_BASE_URL = os.getenv("AUDIO_OPENAI_API_BASE_URL", OPENAI_API_BASE_URL)
AUDIO_OPENAI_API_KEY = os.getenv("AUDIO_OPENAI_API_KEY", OPENAI_API_KEY)

####################################
# LiteLLM
####################################


ENABLE_LITELLM = os.environ.get("ENABLE_LITELLM", "True").lower() == "true"

LITELLM_PROXY_PORT = int(os.getenv("LITELLM_PROXY_PORT", "14365"))
if LITELLM_PROXY_PORT < 0 or LITELLM_PROXY_PORT > 65535:
    raise ValueError("Invalid port number for LITELLM_PROXY_PORT")
LITELLM_PROXY_HOST = os.getenv("LITELLM_PROXY_HOST", "127.0.0.1")


####################################
# Database
####################################

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR}/webui.db")

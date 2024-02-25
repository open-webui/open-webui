import os
import chromadb
from chromadb import Settings
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


try:
    from dotenv import load_dotenv, find_dotenv

    load_dotenv(find_dotenv("../.env"))
except ImportError:
    print("dotenv not installed, skipping...")

WEBUI_NAME = "Open WebUI"
shutil.copyfile("../build/favicon.png", "./static/favicon.png")

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
# CUSTOM_NAME
####################################

CUSTOM_NAME = os.environ.get("CUSTOM_NAME", "")
if CUSTOM_NAME:
    try:
        r = requests.get(f"https://api.openwebui.com/api/v1/custom/{CUSTOM_NAME}")
        data = r.json()
        if r.ok:
            if "logo" in data:
                url = (
                    f"https://api.openwebui.com{data['logo']}"
                    if data["logo"][0] == "/"
                    else data["logo"]
                )

                r = requests.get(url, stream=True)
                if r.status_code == 200:
                    with open("./static/favicon.png", "wb") as f:
                        r.raw.decode_content = True
                        shutil.copyfileobj(r.raw, f)

            WEBUI_NAME = data["name"]
    except Exception as e:
        print(e)
        pass


####################################
# DATA/FRONTEND BUILD DIR
####################################

DATA_DIR = str(Path(os.getenv("DATA_DIR", "./data")).resolve())
FRONTEND_BUILD_DIR = str(Path(os.getenv("FRONTEND_BUILD_DIR", "../build")))

try:
    with open(f"{DATA_DIR}/config.json", "r") as f:
        CONFIG_DATA = json.load(f)
except:
    CONFIG_DATA = {}

####################################
# File Upload DIR
####################################

UPLOAD_DIR = f"{DATA_DIR}/uploads"
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


####################################
# Cache DIR
####################################

CACHE_DIR = f"{DATA_DIR}/cache"
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)


####################################
# Docs DIR
####################################

DOCS_DIR = f"{DATA_DIR}/docs"
Path(DOCS_DIR).mkdir(parents=True, exist_ok=True)


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


LITELLM_CONFIG_PATH = f"{DATA_DIR}/litellm/config.yaml"

if not os.path.exists(LITELLM_CONFIG_PATH):
    print("Config file doesn't exist. Creating...")
    create_config_file(LITELLM_CONFIG_PATH)
    print("Config file created successfully.")


####################################
# OLLAMA_API_BASE_URL
####################################

OLLAMA_API_BASE_URL = os.environ.get(
    "OLLAMA_API_BASE_URL", "http://localhost:11434/api"
)

if ENV == "prod":
    if OLLAMA_API_BASE_URL == "/ollama/api":
        OLLAMA_API_BASE_URL = "http://host.docker.internal:11434/api"

####################################
# OPENAI_API
####################################

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_API_BASE_URL = os.environ.get("OPENAI_API_BASE_URL", "")

if OPENAI_API_BASE_URL == "":
    OPENAI_API_BASE_URL = "https://api.openai.com/v1"


####################################
# WEBUI
####################################

ENABLE_SIGNUP = os.environ.get("ENABLE_SIGNUP", True)
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
    ]
)


DEFAULT_USER_ROLE = os.getenv("DEFAULT_USER_ROLE", "pending")
USER_PERMISSIONS = {"chat": {"deletion": True}}


####################################
# WEBUI_VERSION
####################################

WEBUI_VERSION = os.environ.get("WEBUI_VERSION", "v1.0.0-alpha.100")

####################################
# WEBUI_AUTH (Required for security)
####################################

WEBUI_AUTH = True

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
# RAG
####################################

CHROMA_DATA_PATH = f"{DATA_DIR}/vector_db"
# this uses the model defined in the Dockerfile ENV variable. If you dont use docker or docker based deployments such as k8s, the default embedding model will be used (all-MiniLM-L6-v2)
RAG_EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
# device type ebbeding models - "cpu" (default), "cuda" (nvidia gpu required) or "mps" (apple silicon) - choosing this right can lead to better performance
RAG_EMBEDDING_MODEL_DEVICE_TYPE = os.environ.get(
    "RAG_EMBEDDING_MODEL_DEVICE_TYPE", "cpu"
)
CHROMA_CLIENT = chromadb.PersistentClient(
    path=CHROMA_DATA_PATH,
    settings=Settings(allow_reset=True, anonymized_telemetry=False),
)
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 100


RAG_TEMPLATE = """Use the following context as your learned knowledge, inside <context></context> XML tags.
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

####################################
# Transcribe
####################################

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_MODEL_DIR = os.getenv("WHISPER_MODEL_DIR", f"{CACHE_DIR}/whisper/models")


####################################
# Images
####################################

AUTOMATIC1111_BASE_URL = os.getenv("AUTOMATIC1111_BASE_URL", "")

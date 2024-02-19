import os
import chromadb
from chromadb import Settings
from secrets import token_bytes
from base64 import b64encode
from constants import ERROR_MESSAGES
from pathlib import Path

try:
    from dotenv import load_dotenv, find_dotenv

    load_dotenv(find_dotenv("../.env"))
except ImportError:
    print("dotenv not installed, skipping...")


####################################
# ENV (dev,test,prod)
####################################

ENV = os.environ.get("ENV", "dev")


####################################
# DATA/FRONTEND BUILD DIR
####################################

DATA_DIR = str(Path(os.getenv("DATA_DIR", "./data")).resolve())
FRONTEND_BUILD_DIR = str(Path(os.getenv("FRONTEND_BUILD_DIR", "../build")))

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
DEFAULT_PROMPT_SUGGESTIONS = os.environ.get(
    "DEFAULT_PROMPT_SUGGESTIONS",
    [
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
    ],
)
DEFAULT_USER_ROLE = "pending"
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
EMBED_MODEL = "all-MiniLM-L6-v2"
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

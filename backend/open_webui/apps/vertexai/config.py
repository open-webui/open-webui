import os

from open_webui.config import PersistentConfig

ENABLE_VERTEXAI_API = PersistentConfig(
    "ENABLE_VERTEXAI_API",
    "vertexai.enable",
    os.environ.get("ENABLE_VERTEXAI_API", "True").lower() == "true",
)

VERTEXAI_API_BASE_URL = os.environ.get("VERTEXAI_API_BASE_URL", "")

VERTEXAI_SERVICE_ACCOUNT_JSON = os.environ.get("VERTEXAI_SERVICE_ACCOUNT_JSON", "")

if VERTEXAI_SERVICE_ACCOUNT_JSON == "":
    VERTEXAI_API_BASE_URL = ""
else:
    if VERTEXAI_API_BASE_URL == "":
        if os.environ.get("GOOGLE_PROJECT_ID","") and os.environ.get("GOOGLE_ENDPOINT_ID",""):
            PROJECT_ID = os.environ.get("GOOGLE_PROJECT_ID")
            ENDPOINT_ID = os.environ.get("GOOGLE_ENDPOINT_ID") 
            VERTEXAI_API_BASE_URL = f"https://us-west1-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/us-west1/endpoints/{ENDPOINT_ID}"
        
VERTEXAI_SERVICE_ACCOUNT_JSON = PersistentConfig(
    "VERTEXAI_SERVICE_ACCOUNT_JSON",
    "vertexai.service_account",
    VERTEXAI_SERVICE_ACCOUNT_JSON
)


VERTEXAI_API_BASE_URLS = os.environ.get("VERTEXAI_API_BASE_URLS", "")
VERTEXAI_API_BASE_URLS = (
    VERTEXAI_API_BASE_URLS if VERTEXAI_API_BASE_URLS != "" else VERTEXAI_API_BASE_URL
)

VERTEXAI_API_BASE_URLS = [
    url.strip() if url != "" else VERTEXAI_API_BASE_URL
    for url in VERTEXAI_API_BASE_URLS.split(";")
]
VERTEXAI_API_BASE_URLS = PersistentConfig(
    "VERTEXAI_API_BASE_URLS", "VERTEXAI.api_base_urls", VERTEXAI_API_BASE_URLS
)

VERTEXAI_API_ACCESS_TOKEN = os.environ.get('VERTEXAI_API_ACCESS_TOKEN','')
VERTEXAI_API_ACCESS_TOKEN = PersistentConfig(
    "VERTEXAI_API_ACCESS_TOKEN", "VERTEXAI.api_access_token", VERTEXAI_API_ACCESS_TOKEN
)

VERTEXAI_MODEL_LIST = {
    "llama-3.2-1b": "llama-3.2-1b"
}
 
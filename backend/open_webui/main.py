import asyncio
import inspect
import json
import logging
import mimetypes
import os
import shutil
import sys
import time
import random
import re
from uuid import uuid4


from contextlib import asynccontextmanager
from urllib.parse import urlencode, parse_qs, urlparse
from pydantic import BaseModel
from sqlalchemy import text

from typing import Optional
from aiocache import cached
import aiohttp
import anyio.to_thread
import requests
from redis import Redis


from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
    applications,
    BackgroundTasks,
)
from fastapi.openapi.docs import get_swagger_ui_html

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from starlette_compress import CompressMiddleware

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response, StreamingResponse
from starlette.datastructures import Headers

from starsessions import (
    SessionMiddleware as StarSessionsMiddleware,
    SessionAutoloadMiddleware,
)
from starsessions.stores.redis import RedisStore

from open_webui.utils import logger
from open_webui.utils.audit import AuditLevel, AuditLoggingMiddleware
from open_webui.utils.logger import start_logger
from open_webui.socket.main import (
    app as socket_app,
    periodic_usage_pool_cleanup,
    get_event_emitter,
    get_models_in_use,
    get_active_user_ids,
)
from open_webui.routers import (
    audio,
    billing,
    images,
    ollama,
    openai,
    retrieval,
    pipelines,
    tasks,
    auths,
    channels,
    chats,
    announcements,
    notes,
    folders,
    configs,
    groups,
    files,
    functions,
    memories,
    models,
    knowledge,
    prompts,
    evaluations,
    tools,
    users,
    user_models,
    utils,
    scim,
)

from open_webui.routers.retrieval import (
    get_embedding_function,
    get_reranking_function,
    get_ef,
    get_rf,
)

from open_webui.internal.db import Session, engine

from open_webui.models.functions import Functions
from open_webui.models.models import Models
from open_webui.models.users import UserModel, Users
from open_webui.models.chats import Chats
from open_webui.models.user_model_credentials import UserModelCredentials

from open_webui.config import (
    # Ollama
    ENABLE_OLLAMA_API,
    OLLAMA_BASE_URLS,
    OLLAMA_API_CONFIGS,
    # OpenAI
    ENABLE_OPENAI_API,
    OPENAI_API_BASE_URLS,
    OPENAI_API_KEYS,
    OPENAI_API_CONFIGS,
    # Direct Connections
    ENABLE_DIRECT_CONNECTIONS,
    # Model list
    ENABLE_BASE_MODELS_CACHE,
    # Thread pool size for FastAPI/AnyIO
    THREAD_POOL_SIZE,
    # Tool Server Configs
    TOOL_SERVER_CONNECTIONS,
    # Code Execution
    ENABLE_CODE_EXECUTION,
    CODE_EXECUTION_ENGINE,
    CODE_EXECUTION_JUPYTER_URL,
    CODE_EXECUTION_JUPYTER_AUTH,
    CODE_EXECUTION_JUPYTER_AUTH_TOKEN,
    CODE_EXECUTION_JUPYTER_AUTH_PASSWORD,
    CODE_EXECUTION_JUPYTER_TIMEOUT,
    ENABLE_CODE_INTERPRETER,
    CODE_INTERPRETER_ENGINE,
    CODE_INTERPRETER_PROMPT_TEMPLATE,
    CODE_INTERPRETER_JUPYTER_URL,
    CODE_INTERPRETER_JUPYTER_AUTH,
    CODE_INTERPRETER_JUPYTER_AUTH_TOKEN,
    CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD,
    CODE_INTERPRETER_JUPYTER_TIMEOUT,
    # Image
    AUTOMATIC1111_API_AUTH,
    AUTOMATIC1111_BASE_URL,
    AUTOMATIC1111_CFG_SCALE,
    AUTOMATIC1111_SAMPLER,
    AUTOMATIC1111_SCHEDULER,
    COMFYUI_BASE_URL,
    COMFYUI_API_KEY,
    COMFYUI_WORKFLOW,
    COMFYUI_WORKFLOW_NODES,
    ENABLE_IMAGE_GENERATION,
    ENABLE_IMAGE_PROMPT_GENERATION,
    IMAGE_GENERATION_ENGINE,
    IMAGE_GENERATION_MODEL,
    IMAGE_SIZE,
    IMAGE_STEPS,
    IMAGES_OPENAI_API_BASE_URL,
    IMAGES_OPENAI_API_VERSION,
    IMAGES_OPENAI_API_KEY,
    IMAGES_GEMINI_API_BASE_URL,
    IMAGES_GEMINI_API_KEY,
    # Audio
    AUDIO_STT_ENGINE,
    AUDIO_STT_MODEL,
    AUDIO_STT_SUPPORTED_CONTENT_TYPES,
    AUDIO_STT_OPENAI_API_BASE_URL,
    AUDIO_STT_OPENAI_API_KEY,
    AUDIO_STT_AZURE_API_KEY,
    AUDIO_STT_AZURE_REGION,
    AUDIO_STT_AZURE_LOCALES,
    AUDIO_STT_AZURE_BASE_URL,
    AUDIO_STT_AZURE_MAX_SPEAKERS,
    AUDIO_TTS_ENGINE,
    AUDIO_TTS_MODEL,
    AUDIO_TTS_VOICE,
    AUDIO_TTS_OPENAI_API_BASE_URL,
    AUDIO_TTS_OPENAI_API_KEY,
    AUDIO_TTS_OPENAI_PARAMS,
    AUDIO_TTS_API_KEY,
    AUDIO_TTS_SPLIT_ON,
    AUDIO_TTS_AZURE_SPEECH_REGION,
    AUDIO_TTS_AZURE_SPEECH_BASE_URL,
    AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT,
    PLAYWRIGHT_WS_URL,
    PLAYWRIGHT_TIMEOUT,
    FIRECRAWL_API_BASE_URL,
    FIRECRAWL_API_KEY,
    WEB_LOADER_ENGINE,
    WEB_LOADER_CONCURRENT_REQUESTS,
    WHISPER_MODEL,
    WHISPER_VAD_FILTER,
    WHISPER_LANGUAGE,
    DEEPGRAM_API_KEY,
    WHISPER_MODEL_AUTO_UPDATE,
    WHISPER_MODEL_DIR,
    # Retrieval
    RAG_TEMPLATE,
    DEFAULT_RAG_TEMPLATE,
    RAG_FULL_CONTEXT,
    BYPASS_EMBEDDING_AND_RETRIEVAL,
    RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
    RAG_RERANKING_ENGINE,
    RAG_RERANKING_MODEL,
    RAG_EXTERNAL_RERANKER_URL,
    RAG_EXTERNAL_RERANKER_API_KEY,
    RAG_RERANKING_MODEL_AUTO_UPDATE,
    RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
    RAG_EMBEDDING_ENGINE,
    RAG_EMBEDDING_BATCH_SIZE,
    RAG_TOP_K,
    RAG_TOP_K_RERANKER,
    RAG_RELEVANCE_THRESHOLD,
    RAG_HYBRID_BM25_WEIGHT,
    RAG_ALLOWED_FILE_EXTENSIONS,
    RAG_FILE_MAX_COUNT,
    RAG_FILE_MAX_SIZE,
    FILE_IMAGE_COMPRESSION_WIDTH,
    FILE_IMAGE_COMPRESSION_HEIGHT,
    RAG_OPENAI_API_BASE_URL,
    RAG_OPENAI_API_KEY,
    RAG_AZURE_OPENAI_BASE_URL,
    RAG_AZURE_OPENAI_API_KEY,
    RAG_AZURE_OPENAI_API_VERSION,
    RAG_OLLAMA_BASE_URL,
    RAG_OLLAMA_API_KEY,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CONTENT_EXTRACTION_ENGINE,
    DATALAB_MARKER_API_KEY,
    DATALAB_MARKER_API_BASE_URL,
    DATALAB_MARKER_ADDITIONAL_CONFIG,
    DATALAB_MARKER_SKIP_CACHE,
    DATALAB_MARKER_FORCE_OCR,
    DATALAB_MARKER_PAGINATE,
    DATALAB_MARKER_STRIP_EXISTING_OCR,
    DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION,
    DATALAB_MARKER_FORMAT_LINES,
    DATALAB_MARKER_OUTPUT_FORMAT,
    MINERU_API_MODE,
    MINERU_API_URL,
    MINERU_API_KEY,
    MINERU_PARAMS,
    DATALAB_MARKER_USE_LLM,
    EXTERNAL_DOCUMENT_LOADER_URL,
    EXTERNAL_DOCUMENT_LOADER_API_KEY,
    TIKA_SERVER_URL,
    DOCLING_SERVER_URL,
    DOCLING_PARAMS,
    DOCLING_DO_OCR,
    DOCLING_FORCE_OCR,
    DOCLING_OCR_ENGINE,
    DOCLING_OCR_LANG,
    DOCLING_PDF_BACKEND,
    DOCLING_TABLE_MODE,
    DOCLING_PIPELINE,
    DOCLING_DO_PICTURE_DESCRIPTION,
    DOCLING_PICTURE_DESCRIPTION_MODE,
    DOCLING_PICTURE_DESCRIPTION_LOCAL,
    DOCLING_PICTURE_DESCRIPTION_API,
    DOCUMENT_INTELLIGENCE_ENDPOINT,
    DOCUMENT_INTELLIGENCE_KEY,
    MISTRAL_OCR_API_KEY,
    RAG_TEXT_SPLITTER,
    TIKTOKEN_ENCODING_NAME,
    PDF_EXTRACT_IMAGES,
    YOUTUBE_LOADER_LANGUAGE,
    YOUTUBE_LOADER_PROXY_URL,
    # Retrieval (Web Search)
    ENABLE_WEB_SEARCH,
    WEB_SEARCH_ENGINE,
    BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL,
    BYPASS_WEB_SEARCH_WEB_LOADER,
    WEB_SEARCH_RESULT_COUNT,
    WEB_SEARCH_CONCURRENT_REQUESTS,
    WEB_SEARCH_TRUST_ENV,
    WEB_SEARCH_DOMAIN_FILTER_LIST,
    OLLAMA_CLOUD_WEB_SEARCH_API_KEY,
    JINA_API_KEY,
    SEARCHAPI_API_KEY,
    SEARCHAPI_ENGINE,
    SERPAPI_API_KEY,
    SERPAPI_ENGINE,
    SEARXNG_QUERY_URL,
    YACY_QUERY_URL,
    YACY_USERNAME,
    YACY_PASSWORD,
    SERPER_API_KEY,
    SERPLY_API_KEY,
    SERPSTACK_API_KEY,
    SERPSTACK_HTTPS,
    TAVILY_API_KEY,
    TAVILY_EXTRACT_DEPTH,
    BING_SEARCH_V7_ENDPOINT,
    BING_SEARCH_V7_SUBSCRIPTION_KEY,
    BRAVE_SEARCH_API_KEY,
    EXA_API_KEY,
    PERPLEXITY_API_KEY,
    PERPLEXITY_MODEL,
    PERPLEXITY_SEARCH_CONTEXT_USAGE,
    SOUGOU_API_SID,
    SOUGOU_API_SK,
    KAGI_SEARCH_API_KEY,
    MOJEEK_SEARCH_API_KEY,
    BOCHA_SEARCH_API_KEY,
    GOOGLE_PSE_API_KEY,
    GOOGLE_PSE_ENGINE_ID,
    GOOGLE_DRIVE_CLIENT_ID,
    GOOGLE_DRIVE_API_KEY,
    ENABLE_ONEDRIVE_INTEGRATION,
    ONEDRIVE_CLIENT_ID_PERSONAL,
    ONEDRIVE_CLIENT_ID_BUSINESS,
    ONEDRIVE_SHAREPOINT_URL,
    ONEDRIVE_SHAREPOINT_TENANT_ID,
    ENABLE_ONEDRIVE_PERSONAL,
    ENABLE_ONEDRIVE_BUSINESS,
    ENABLE_RAG_HYBRID_SEARCH,
    ENABLE_RAG_LOCAL_WEB_FETCH,
    ENABLE_WEB_LOADER_SSL_VERIFICATION,
    ENABLE_GOOGLE_DRIVE_INTEGRATION,
    UPLOAD_DIR,
    EXTERNAL_WEB_SEARCH_URL,
    EXTERNAL_WEB_SEARCH_API_KEY,
    EXTERNAL_WEB_LOADER_URL,
    EXTERNAL_WEB_LOADER_API_KEY,
    # WebUI
    WEBUI_AUTH,
    WEBUI_NAME,
    WEBUI_BANNERS,
    WEBHOOK_URL,
    ADMIN_EMAIL,
    SHOW_ADMIN_DETAILS,
    JWT_EXPIRES_IN,
    ENABLE_SIGNUP,
    ENABLE_LOGIN_FORM,
    ENABLE_API_KEY,
    ENABLE_API_KEY_ENDPOINT_RESTRICTIONS,
    API_KEY_ALLOWED_ENDPOINTS,
    ENABLE_CHANNELS,
    ENABLE_NOTES,
    ENABLE_COMMUNITY_SHARING,
    ENABLE_MESSAGE_RATING,
    ENABLE_USER_WEBHOOKS,
    ENABLE_EVALUATION_ARENA_MODELS,
    BYPASS_ADMIN_ACCESS_CONTROL,
    USER_PERMISSIONS,
    DEFAULT_USER_ROLE,
    PENDING_USER_OVERLAY_CONTENT,
    PENDING_USER_OVERLAY_TITLE,
    DEFAULT_PROMPT_SUGGESTIONS,
    DEFAULT_MODELS,
    DEFAULT_ARENA_MODEL,
    MODEL_ORDER_LIST,
    EVALUATION_ARENA_MODELS,
    # WebUI (OAuth)
    ENABLE_OAUTH_ROLE_MANAGEMENT,
    OAUTH_ROLES_CLAIM,
    OAUTH_EMAIL_CLAIM,
    OAUTH_PICTURE_CLAIM,
    OAUTH_USERNAME_CLAIM,
    OAUTH_ALLOWED_ROLES,
    OAUTH_ADMIN_ROLES,
    # WebUI (LDAP)
    ENABLE_LDAP,
    LDAP_SERVER_LABEL,
    LDAP_SERVER_HOST,
    LDAP_SERVER_PORT,
    LDAP_ATTRIBUTE_FOR_MAIL,
    LDAP_ATTRIBUTE_FOR_USERNAME,
    LDAP_SEARCH_FILTERS,
    LDAP_SEARCH_BASE,
    LDAP_APP_DN,
    LDAP_APP_PASSWORD,
    LDAP_USE_TLS,
    LDAP_CA_CERT_FILE,
    LDAP_VALIDATE_CERT,
    LDAP_CIPHERS,
    # LDAP Group Management
    ENABLE_LDAP_GROUP_MANAGEMENT,
    ENABLE_LDAP_GROUP_CREATION,
    LDAP_ATTRIBUTE_FOR_GROUPS,
    # Misc
    ENV,
    CACHE_DIR,
    STATIC_DIR,
    FRONTEND_BUILD_DIR,
    CORS_ALLOW_ORIGIN,
    DEFAULT_LOCALE,
    OAUTH_PROVIDERS,
    WEBUI_URL,
    RESPONSE_WATERMARK,
    # Admin
    ENABLE_ADMIN_CHAT_ACCESS,
    BYPASS_ADMIN_ACCESS_CONTROL,
    ENABLE_ADMIN_EXPORT,
    # Tasks
    TASK_MODEL,
    TASK_MODEL_EXTERNAL,
    ENABLE_TAGS_GENERATION,
    ENABLE_TITLE_GENERATION,
    ENABLE_FOLLOW_UP_GENERATION,
    ENABLE_SEARCH_QUERY_GENERATION,
    ENABLE_RETRIEVAL_QUERY_GENERATION,
    ENABLE_AUTOCOMPLETE_GENERATION,
    TITLE_GENERATION_PROMPT_TEMPLATE,
    FOLLOW_UP_GENERATION_PROMPT_TEMPLATE,
    TAGS_GENERATION_PROMPT_TEMPLATE,
    IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE,
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    QUERY_GENERATION_PROMPT_TEMPLATE,
    AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE,
    AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH,
    AppConfig,
    reset_config,
)
from open_webui.env import (
    LICENSE_KEY,
    AUDIT_EXCLUDED_PATHS,
    AUDIT_LOG_LEVEL,
    CHANGELOG,
    REDIS_URL,
    REDIS_CLUSTER,
    REDIS_KEY_PREFIX,
    REDIS_SENTINEL_HOSTS,
    REDIS_SENTINEL_PORT,
    GLOBAL_LOG_LEVEL,
    MAX_BODY_LOG_SIZE,
    SAFE_MODE,
    SRC_LOG_LEVELS,
    VERSION,
    INSTANCE_ID,
    WEBUI_BUILD_HASH,
    WEBUI_SECRET_KEY,
    WEBUI_SESSION_COOKIE_SAME_SITE,
    WEBUI_SESSION_COOKIE_SECURE,
    ENABLE_SIGNUP_PASSWORD_CONFIRMATION,
    EMAIL_SMTP_SERVER,
    EMAIL_SMTP_PORT,
    EMAIL_SMTP_USERNAME,
    EMAIL_SMTP_PASSWORD,
    EMAIL_SMTP_FROM,
    EMAIL_VERIFICATION_CODE_TTL,
    EMAIL_VERIFICATION_SEND_INTERVAL,
    EMAIL_VERIFICATION_MAX_ATTEMPTS,
    WEBUI_AUTH_TRUSTED_EMAIL_HEADER,
    WEBUI_AUTH_TRUSTED_NAME_HEADER,
    WEBUI_AUTH_SIGNOUT_REDIRECT_URL,
    # SCIM
    SCIM_ENABLED,
    SCIM_TOKEN,
    ENABLE_COMPRESSION_MIDDLEWARE,
    ENABLE_WEBSOCKET_SUPPORT,
    BYPASS_MODEL_ACCESS_CONTROL,
    RESET_CONFIG_ON_START,
    ENABLE_VERSION_UPDATE_CHECK,
    ENABLE_OTEL,
    EXTERNAL_PWA_MANIFEST_URL,
    AIOHTTP_CLIENT_SESSION_SSL,
    ENABLE_STAR_SESSIONS_MIDDLEWARE,

    CHAT_DEBUG_FLAG,
)


from open_webui.utils.models import (
    get_all_models,
    get_all_base_models,
    check_model_access,
    get_filtered_models,
    transform_user_model_if_needed,
)
from open_webui.utils.email_utils import EmailVerificationManager
from open_webui.utils.chat import (
    generate_chat_completion as chat_completion_handler,
    chat_completed as chat_completed_handler,
    chat_action as chat_action_handler,
)
from open_webui.utils.misc import get_message_list
from open_webui.utils.summary import (
    summarize,
    compute_token_count,
    build_ordered_messages,
    get_recent_messages_by_user_id,
)
from open_webui.utils.embeddings import generate_embeddings
from open_webui.utils.middleware import process_chat_payload, process_chat_response
from open_webui.utils.access_control import has_access

from open_webui.utils.auth import (
    get_license_data,
    get_http_authorization_cred,
    decode_token,
    get_admin_user,
    get_verified_user,
)
from open_webui.utils.plugin import install_tool_and_function_dependencies
from open_webui.utils.oauth import (
    OAuthManager,
    OAuthClientManager,
    decrypt_data,
    OAuthClientInformationFull,
)
from open_webui.utils.security_headers import SecurityHeadersMiddleware
from open_webui.utils.redis import get_redis_connection

from open_webui.tasks import (
    redis_task_command_listener,
    list_task_ids_by_item_id,
    create_task,
    stop_task,
    list_tasks,
)  # Import from tasks.py

from open_webui.utils.redis import get_sentinels_from_env


from open_webui.constants import ERROR_MESSAGES


if SAFE_MODE:
    print("SAFE MODE ENABLED")
    Functions.deactivate_all_functions()

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except (HTTPException, StarletteHTTPException) as ex:
            if ex.status_code == 404:
                if path.endswith(".js"):
                    # Return 404 for javascript files
                    raise ex
                else:
                    return await super().get_response("index.html", scope)
            else:
                raise ex


print(
    rf"""
 ██████╗ ██████╗ ███████╗███╗   ██╗    ██╗    ██╗███████╗██████╗ ██╗   ██╗██╗
██╔═══██╗██╔══██╗██╔════╝████╗  ██║    ██║    ██║██╔════╝██╔══██╗██║   ██║██║
██║   ██║██████╔╝█████╗  ██╔██╗ ██║    ██║ █╗ ██║█████╗  ██████╔╝██║   ██║██║
██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║    ██║███╗██║██╔══╝  ██╔══██╗██║   ██║██║
╚██████╔╝██║     ███████╗██║ ╚████║    ╚███╔███╔╝███████╗██████╔╝╚██████╔╝██║
 ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝     ╚══╝╚══╝ ╚══════╝╚═════╝  ╚═════╝ ╚═╝


v{VERSION} - building the best AI user interface.
{f"Commit: {WEBUI_BUILD_HASH}" if WEBUI_BUILD_HASH != "dev-build" else ""}
https://github.com/open-webui/open-webui
"""
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.instance_id = INSTANCE_ID
    start_logger()

    if RESET_CONFIG_ON_START:
        reset_config()

    if LICENSE_KEY:
        get_license_data(app, LICENSE_KEY)

    # This should be blocking (sync) so functions are not deactivated on first /get_models calls
    # when the first user lands on the / route.
    log.info("Installing external dependencies of functions and tools...")
    install_tool_and_function_dependencies()

    app.state.redis = get_redis_connection(
        redis_url=REDIS_URL,
        redis_sentinels=get_sentinels_from_env(
            REDIS_SENTINEL_HOSTS, REDIS_SENTINEL_PORT
        ),
        redis_cluster=REDIS_CLUSTER,
        async_mode=True,
    )
    app.state.email_verification_manager = EmailVerificationManager(app.state.redis)
    app.state.reset_verification_manager = EmailVerificationManager(
        app.state.redis, prefix="reset:code"
    )

    if app.state.redis is not None:
        app.state.redis_task_command_listener = asyncio.create_task(
            redis_task_command_listener(app)
        )

    if THREAD_POOL_SIZE and THREAD_POOL_SIZE > 0:
        limiter = anyio.to_thread.current_default_thread_limiter()
        limiter.total_tokens = THREAD_POOL_SIZE

    asyncio.create_task(periodic_usage_pool_cleanup())

    if app.state.config.ENABLE_BASE_MODELS_CACHE:
        await get_all_models(
            Request(
                # Creating a mock request object to pass to get_all_models
                {
                    "type": "http",
                    "asgi.version": "3.0",
                    "asgi.spec_version": "2.0",
                    "method": "GET",
                    "path": "/internal",
                    "query_string": b"",
                    "headers": Headers({}).raw,
                    "client": ("127.0.0.1", 12345),
                    "server": ("127.0.0.1", 80),
                    "scheme": "http",
                    "app": app,
                }
            ),
            None,
        )

    yield

    if hasattr(app.state, "redis_task_command_listener"):
        app.state.redis_task_command_listener.cancel()


app = FastAPI(
    title="Cakumi",
    docs_url="/docs" if ENV == "dev" else None,
    openapi_url="/openapi.json" if ENV == "dev" else None,
    redoc_url=None,
    lifespan=lifespan,
)

# For Cakumi OIDC/OAuth2
oauth_manager = OAuthManager(app)
app.state.oauth_manager = oauth_manager

# For Integrations
oauth_client_manager = OAuthClientManager(app)
app.state.oauth_client_manager = oauth_client_manager

app.state.instance_id = None
app.state.config = AppConfig(
    redis_url=REDIS_URL,
    redis_sentinels=get_sentinels_from_env(REDIS_SENTINEL_HOSTS, REDIS_SENTINEL_PORT),
    redis_cluster=REDIS_CLUSTER,
    redis_key_prefix=REDIS_KEY_PREFIX,
)
app.state.redis = None
app.state.reset_verification_manager = None

app.state.WEBUI_NAME = WEBUI_NAME
app.state.LICENSE_METADATA = None


########################################
#
# OPENTELEMETRY
#
########################################

if ENABLE_OTEL:
    from open_webui.utils.telemetry.setup import setup as setup_opentelemetry

    setup_opentelemetry(app=app, db_engine=engine)


########################################
#
# OLLAMA
#
########################################


app.state.config.ENABLE_OLLAMA_API = ENABLE_OLLAMA_API
app.state.config.OLLAMA_BASE_URLS = OLLAMA_BASE_URLS
app.state.config.OLLAMA_API_CONFIGS = OLLAMA_API_CONFIGS

app.state.OLLAMA_MODELS = {}

########################################
#
# OPENAI
#
########################################

app.state.config.ENABLE_OPENAI_API = ENABLE_OPENAI_API
app.state.config.OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS
app.state.config.OPENAI_API_KEYS = OPENAI_API_KEYS
app.state.config.OPENAI_API_CONFIGS = OPENAI_API_CONFIGS

app.state.OPENAI_MODELS = {}

########################################
#
# TOOL SERVERS
#
########################################

app.state.config.TOOL_SERVER_CONNECTIONS = TOOL_SERVER_CONNECTIONS
app.state.TOOL_SERVERS = []

########################################
#
# DIRECT CONNECTIONS
#
########################################

app.state.config.ENABLE_DIRECT_CONNECTIONS = ENABLE_DIRECT_CONNECTIONS

########################################
#
# SCIM
#
########################################

app.state.SCIM_ENABLED = SCIM_ENABLED
app.state.SCIM_TOKEN = SCIM_TOKEN

########################################
#
# MODELS
#
########################################

app.state.config.ENABLE_BASE_MODELS_CACHE = ENABLE_BASE_MODELS_CACHE
app.state.BASE_MODELS = []

########################################
#
# WEBUI
#
########################################

app.state.config.WEBUI_URL = WEBUI_URL
app.state.config.ENABLE_SIGNUP = ENABLE_SIGNUP
app.state.config.ENABLE_LOGIN_FORM = ENABLE_LOGIN_FORM

app.state.config.ENABLE_API_KEY = ENABLE_API_KEY
app.state.config.ENABLE_API_KEY_ENDPOINT_RESTRICTIONS = (
    ENABLE_API_KEY_ENDPOINT_RESTRICTIONS
)
app.state.config.API_KEY_ALLOWED_ENDPOINTS = API_KEY_ALLOWED_ENDPOINTS

app.state.config.JWT_EXPIRES_IN = JWT_EXPIRES_IN

app.state.config.SHOW_ADMIN_DETAILS = SHOW_ADMIN_DETAILS
app.state.config.ADMIN_EMAIL = ADMIN_EMAIL

app.state.email_verification_enabled = True
app.state.email_verification_config = {
    "ttl": EMAIL_VERIFICATION_CODE_TTL,
    "send_interval": EMAIL_VERIFICATION_SEND_INTERVAL,
    "max_attempts": EMAIL_VERIFICATION_MAX_ATTEMPTS,
    "smtp": {
        "server": EMAIL_SMTP_SERVER,
        "port": EMAIL_SMTP_PORT,
        "username": EMAIL_SMTP_USERNAME,
        "password": EMAIL_SMTP_PASSWORD,
        "from_email": EMAIL_SMTP_FROM,
    },
}


app.state.config.DEFAULT_MODELS = DEFAULT_MODELS
app.state.config.DEFAULT_PROMPT_SUGGESTIONS = DEFAULT_PROMPT_SUGGESTIONS
app.state.config.DEFAULT_USER_ROLE = DEFAULT_USER_ROLE

app.state.config.PENDING_USER_OVERLAY_CONTENT = PENDING_USER_OVERLAY_CONTENT
app.state.config.PENDING_USER_OVERLAY_TITLE = PENDING_USER_OVERLAY_TITLE

app.state.config.RESPONSE_WATERMARK = RESPONSE_WATERMARK

app.state.config.USER_PERMISSIONS = USER_PERMISSIONS
app.state.config.WEBHOOK_URL = WEBHOOK_URL
app.state.config.BANNERS = WEBUI_BANNERS
app.state.config.MODEL_ORDER_LIST = MODEL_ORDER_LIST


app.state.config.ENABLE_CHANNELS = ENABLE_CHANNELS
app.state.config.ENABLE_NOTES = ENABLE_NOTES
app.state.config.ENABLE_COMMUNITY_SHARING = ENABLE_COMMUNITY_SHARING
app.state.config.ENABLE_MESSAGE_RATING = ENABLE_MESSAGE_RATING
app.state.config.ENABLE_USER_WEBHOOKS = ENABLE_USER_WEBHOOKS

app.state.config.ENABLE_EVALUATION_ARENA_MODELS = ENABLE_EVALUATION_ARENA_MODELS
app.state.config.EVALUATION_ARENA_MODELS = EVALUATION_ARENA_MODELS

app.state.config.OAUTH_USERNAME_CLAIM = OAUTH_USERNAME_CLAIM
app.state.config.OAUTH_PICTURE_CLAIM = OAUTH_PICTURE_CLAIM
app.state.config.OAUTH_EMAIL_CLAIM = OAUTH_EMAIL_CLAIM

app.state.config.ENABLE_OAUTH_ROLE_MANAGEMENT = ENABLE_OAUTH_ROLE_MANAGEMENT
app.state.config.OAUTH_ROLES_CLAIM = OAUTH_ROLES_CLAIM
app.state.config.OAUTH_ALLOWED_ROLES = OAUTH_ALLOWED_ROLES
app.state.config.OAUTH_ADMIN_ROLES = OAUTH_ADMIN_ROLES

app.state.config.ENABLE_LDAP = ENABLE_LDAP
app.state.config.LDAP_SERVER_LABEL = LDAP_SERVER_LABEL
app.state.config.LDAP_SERVER_HOST = LDAP_SERVER_HOST
app.state.config.LDAP_SERVER_PORT = LDAP_SERVER_PORT
app.state.config.LDAP_ATTRIBUTE_FOR_MAIL = LDAP_ATTRIBUTE_FOR_MAIL
app.state.config.LDAP_ATTRIBUTE_FOR_USERNAME = LDAP_ATTRIBUTE_FOR_USERNAME
app.state.config.LDAP_APP_DN = LDAP_APP_DN
app.state.config.LDAP_APP_PASSWORD = LDAP_APP_PASSWORD
app.state.config.LDAP_SEARCH_BASE = LDAP_SEARCH_BASE
app.state.config.LDAP_SEARCH_FILTERS = LDAP_SEARCH_FILTERS
app.state.config.LDAP_USE_TLS = LDAP_USE_TLS
app.state.config.LDAP_CA_CERT_FILE = LDAP_CA_CERT_FILE
app.state.config.LDAP_VALIDATE_CERT = LDAP_VALIDATE_CERT
app.state.config.LDAP_CIPHERS = LDAP_CIPHERS

# For LDAP Group Management
app.state.config.ENABLE_LDAP_GROUP_MANAGEMENT = ENABLE_LDAP_GROUP_MANAGEMENT
app.state.config.ENABLE_LDAP_GROUP_CREATION = ENABLE_LDAP_GROUP_CREATION
app.state.config.LDAP_ATTRIBUTE_FOR_GROUPS = LDAP_ATTRIBUTE_FOR_GROUPS


app.state.AUTH_TRUSTED_EMAIL_HEADER = WEBUI_AUTH_TRUSTED_EMAIL_HEADER
app.state.AUTH_TRUSTED_NAME_HEADER = WEBUI_AUTH_TRUSTED_NAME_HEADER
app.state.WEBUI_AUTH_SIGNOUT_REDIRECT_URL = WEBUI_AUTH_SIGNOUT_REDIRECT_URL
app.state.EXTERNAL_PWA_MANIFEST_URL = EXTERNAL_PWA_MANIFEST_URL

app.state.USER_COUNT = None

app.state.TOOLS = {}
app.state.TOOL_CONTENTS = {}

app.state.FUNCTIONS = {}
app.state.FUNCTION_CONTENTS = {}

########################################
#
# RETRIEVAL
#
########################################


app.state.config.TOP_K = RAG_TOP_K
app.state.config.TOP_K_RERANKER = RAG_TOP_K_RERANKER
app.state.config.RELEVANCE_THRESHOLD = RAG_RELEVANCE_THRESHOLD
app.state.config.HYBRID_BM25_WEIGHT = RAG_HYBRID_BM25_WEIGHT


app.state.config.ALLOWED_FILE_EXTENSIONS = RAG_ALLOWED_FILE_EXTENSIONS
app.state.config.FILE_MAX_SIZE = RAG_FILE_MAX_SIZE
app.state.config.FILE_MAX_COUNT = RAG_FILE_MAX_COUNT
app.state.config.FILE_IMAGE_COMPRESSION_WIDTH = FILE_IMAGE_COMPRESSION_WIDTH
app.state.config.FILE_IMAGE_COMPRESSION_HEIGHT = FILE_IMAGE_COMPRESSION_HEIGHT


app.state.config.RAG_FULL_CONTEXT = RAG_FULL_CONTEXT
app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL = BYPASS_EMBEDDING_AND_RETRIEVAL
app.state.config.ENABLE_RAG_HYBRID_SEARCH = ENABLE_RAG_HYBRID_SEARCH
app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION = ENABLE_WEB_LOADER_SSL_VERIFICATION

app.state.config.CONTENT_EXTRACTION_ENGINE = CONTENT_EXTRACTION_ENGINE
app.state.config.DATALAB_MARKER_API_KEY = DATALAB_MARKER_API_KEY
app.state.config.DATALAB_MARKER_API_BASE_URL = DATALAB_MARKER_API_BASE_URL
app.state.config.DATALAB_MARKER_ADDITIONAL_CONFIG = DATALAB_MARKER_ADDITIONAL_CONFIG
app.state.config.DATALAB_MARKER_SKIP_CACHE = DATALAB_MARKER_SKIP_CACHE
app.state.config.DATALAB_MARKER_FORCE_OCR = DATALAB_MARKER_FORCE_OCR
app.state.config.DATALAB_MARKER_PAGINATE = DATALAB_MARKER_PAGINATE
app.state.config.DATALAB_MARKER_STRIP_EXISTING_OCR = DATALAB_MARKER_STRIP_EXISTING_OCR
app.state.config.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION = (
    DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION
)
app.state.config.DATALAB_MARKER_FORMAT_LINES = DATALAB_MARKER_FORMAT_LINES
app.state.config.DATALAB_MARKER_USE_LLM = DATALAB_MARKER_USE_LLM
app.state.config.DATALAB_MARKER_OUTPUT_FORMAT = DATALAB_MARKER_OUTPUT_FORMAT
app.state.config.EXTERNAL_DOCUMENT_LOADER_URL = EXTERNAL_DOCUMENT_LOADER_URL
app.state.config.EXTERNAL_DOCUMENT_LOADER_API_KEY = EXTERNAL_DOCUMENT_LOADER_API_KEY
app.state.config.TIKA_SERVER_URL = TIKA_SERVER_URL
app.state.config.DOCLING_SERVER_URL = DOCLING_SERVER_URL
app.state.config.DOCLING_PARAMS = DOCLING_PARAMS
app.state.config.DOCLING_DO_OCR = DOCLING_DO_OCR
app.state.config.DOCLING_FORCE_OCR = DOCLING_FORCE_OCR
app.state.config.DOCLING_OCR_ENGINE = DOCLING_OCR_ENGINE
app.state.config.DOCLING_OCR_LANG = DOCLING_OCR_LANG
app.state.config.DOCLING_PDF_BACKEND = DOCLING_PDF_BACKEND
app.state.config.DOCLING_TABLE_MODE = DOCLING_TABLE_MODE
app.state.config.DOCLING_PIPELINE = DOCLING_PIPELINE
app.state.config.DOCLING_DO_PICTURE_DESCRIPTION = DOCLING_DO_PICTURE_DESCRIPTION
app.state.config.DOCLING_PICTURE_DESCRIPTION_MODE = DOCLING_PICTURE_DESCRIPTION_MODE
app.state.config.DOCLING_PICTURE_DESCRIPTION_LOCAL = DOCLING_PICTURE_DESCRIPTION_LOCAL
app.state.config.DOCLING_PICTURE_DESCRIPTION_API = DOCLING_PICTURE_DESCRIPTION_API
app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT = DOCUMENT_INTELLIGENCE_ENDPOINT
app.state.config.DOCUMENT_INTELLIGENCE_KEY = DOCUMENT_INTELLIGENCE_KEY
app.state.config.MISTRAL_OCR_API_KEY = MISTRAL_OCR_API_KEY
app.state.config.MINERU_API_MODE = MINERU_API_MODE
app.state.config.MINERU_API_URL = MINERU_API_URL
app.state.config.MINERU_API_KEY = MINERU_API_KEY
app.state.config.MINERU_PARAMS = MINERU_PARAMS

app.state.config.TEXT_SPLITTER = RAG_TEXT_SPLITTER
app.state.config.TIKTOKEN_ENCODING_NAME = TIKTOKEN_ENCODING_NAME

app.state.config.CHUNK_SIZE = CHUNK_SIZE
app.state.config.CHUNK_OVERLAP = CHUNK_OVERLAP

app.state.config.RAG_EMBEDDING_ENGINE = RAG_EMBEDDING_ENGINE
app.state.config.RAG_EMBEDDING_MODEL = RAG_EMBEDDING_MODEL
app.state.config.RAG_EMBEDDING_BATCH_SIZE = RAG_EMBEDDING_BATCH_SIZE

app.state.config.RAG_RERANKING_ENGINE = RAG_RERANKING_ENGINE
app.state.config.RAG_RERANKING_MODEL = RAG_RERANKING_MODEL
app.state.config.RAG_EXTERNAL_RERANKER_URL = RAG_EXTERNAL_RERANKER_URL
app.state.config.RAG_EXTERNAL_RERANKER_API_KEY = RAG_EXTERNAL_RERANKER_API_KEY

app.state.config.RAG_TEMPLATE = RAG_TEMPLATE

app.state.config.RAG_OPENAI_API_BASE_URL = RAG_OPENAI_API_BASE_URL
app.state.config.RAG_OPENAI_API_KEY = RAG_OPENAI_API_KEY

app.state.config.RAG_AZURE_OPENAI_BASE_URL = RAG_AZURE_OPENAI_BASE_URL
app.state.config.RAG_AZURE_OPENAI_API_KEY = RAG_AZURE_OPENAI_API_KEY
app.state.config.RAG_AZURE_OPENAI_API_VERSION = RAG_AZURE_OPENAI_API_VERSION

app.state.config.RAG_OLLAMA_BASE_URL = RAG_OLLAMA_BASE_URL
app.state.config.RAG_OLLAMA_API_KEY = RAG_OLLAMA_API_KEY

app.state.config.PDF_EXTRACT_IMAGES = PDF_EXTRACT_IMAGES

app.state.config.YOUTUBE_LOADER_LANGUAGE = YOUTUBE_LOADER_LANGUAGE
app.state.config.YOUTUBE_LOADER_PROXY_URL = YOUTUBE_LOADER_PROXY_URL


app.state.config.ENABLE_WEB_SEARCH = ENABLE_WEB_SEARCH
app.state.config.WEB_SEARCH_ENGINE = WEB_SEARCH_ENGINE
app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST = WEB_SEARCH_DOMAIN_FILTER_LIST
app.state.config.WEB_SEARCH_RESULT_COUNT = WEB_SEARCH_RESULT_COUNT
app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS = WEB_SEARCH_CONCURRENT_REQUESTS

app.state.config.WEB_LOADER_ENGINE = WEB_LOADER_ENGINE
app.state.config.WEB_LOADER_CONCURRENT_REQUESTS = WEB_LOADER_CONCURRENT_REQUESTS

app.state.config.WEB_SEARCH_TRUST_ENV = WEB_SEARCH_TRUST_ENV
app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL = (
    BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
)
app.state.config.BYPASS_WEB_SEARCH_WEB_LOADER = BYPASS_WEB_SEARCH_WEB_LOADER

app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION = ENABLE_GOOGLE_DRIVE_INTEGRATION
app.state.config.ENABLE_ONEDRIVE_INTEGRATION = ENABLE_ONEDRIVE_INTEGRATION

app.state.config.OLLAMA_CLOUD_WEB_SEARCH_API_KEY = OLLAMA_CLOUD_WEB_SEARCH_API_KEY
app.state.config.SEARXNG_QUERY_URL = SEARXNG_QUERY_URL
app.state.config.YACY_QUERY_URL = YACY_QUERY_URL
app.state.config.YACY_USERNAME = YACY_USERNAME
app.state.config.YACY_PASSWORD = YACY_PASSWORD
app.state.config.GOOGLE_PSE_API_KEY = GOOGLE_PSE_API_KEY
app.state.config.GOOGLE_PSE_ENGINE_ID = GOOGLE_PSE_ENGINE_ID
app.state.config.BRAVE_SEARCH_API_KEY = BRAVE_SEARCH_API_KEY
app.state.config.KAGI_SEARCH_API_KEY = KAGI_SEARCH_API_KEY
app.state.config.MOJEEK_SEARCH_API_KEY = MOJEEK_SEARCH_API_KEY
app.state.config.BOCHA_SEARCH_API_KEY = BOCHA_SEARCH_API_KEY
app.state.config.SERPSTACK_API_KEY = SERPSTACK_API_KEY
app.state.config.SERPSTACK_HTTPS = SERPSTACK_HTTPS
app.state.config.SERPER_API_KEY = SERPER_API_KEY
app.state.config.SERPLY_API_KEY = SERPLY_API_KEY
app.state.config.TAVILY_API_KEY = TAVILY_API_KEY
app.state.config.SEARCHAPI_API_KEY = SEARCHAPI_API_KEY
app.state.config.SEARCHAPI_ENGINE = SEARCHAPI_ENGINE
app.state.config.SERPAPI_API_KEY = SERPAPI_API_KEY
app.state.config.SERPAPI_ENGINE = SERPAPI_ENGINE
app.state.config.JINA_API_KEY = JINA_API_KEY
app.state.config.BING_SEARCH_V7_ENDPOINT = BING_SEARCH_V7_ENDPOINT
app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY = BING_SEARCH_V7_SUBSCRIPTION_KEY
app.state.config.EXA_API_KEY = EXA_API_KEY
app.state.config.PERPLEXITY_API_KEY = PERPLEXITY_API_KEY
app.state.config.PERPLEXITY_MODEL = PERPLEXITY_MODEL
app.state.config.PERPLEXITY_SEARCH_CONTEXT_USAGE = PERPLEXITY_SEARCH_CONTEXT_USAGE
app.state.config.SOUGOU_API_SID = SOUGOU_API_SID
app.state.config.SOUGOU_API_SK = SOUGOU_API_SK
app.state.config.EXTERNAL_WEB_SEARCH_URL = EXTERNAL_WEB_SEARCH_URL
app.state.config.EXTERNAL_WEB_SEARCH_API_KEY = EXTERNAL_WEB_SEARCH_API_KEY
app.state.config.EXTERNAL_WEB_LOADER_URL = EXTERNAL_WEB_LOADER_URL
app.state.config.EXTERNAL_WEB_LOADER_API_KEY = EXTERNAL_WEB_LOADER_API_KEY


app.state.config.PLAYWRIGHT_WS_URL = PLAYWRIGHT_WS_URL
app.state.config.PLAYWRIGHT_TIMEOUT = PLAYWRIGHT_TIMEOUT
app.state.config.FIRECRAWL_API_BASE_URL = FIRECRAWL_API_BASE_URL
app.state.config.FIRECRAWL_API_KEY = FIRECRAWL_API_KEY
app.state.config.TAVILY_EXTRACT_DEPTH = TAVILY_EXTRACT_DEPTH

app.state.EMBEDDING_FUNCTION = None
app.state.RERANKING_FUNCTION = None
app.state.ef = None
app.state.rf = None

app.state.YOUTUBE_LOADER_TRANSLATION = None


try:
    app.state.ef = get_ef(
        app.state.config.RAG_EMBEDDING_ENGINE,
        app.state.config.RAG_EMBEDDING_MODEL,
        RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    )
    if (
        app.state.config.ENABLE_RAG_HYBRID_SEARCH
        and not app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL
    ):
        app.state.rf = get_rf(
            app.state.config.RAG_RERANKING_ENGINE,
            app.state.config.RAG_RERANKING_MODEL,
            app.state.config.RAG_EXTERNAL_RERANKER_URL,
            app.state.config.RAG_EXTERNAL_RERANKER_API_KEY,
            RAG_RERANKING_MODEL_AUTO_UPDATE,
        )
    else:
        app.state.rf = None
except Exception as e:
    log.error(f"Error updating models: {e}")
    pass


app.state.EMBEDDING_FUNCTION = get_embedding_function(
    app.state.config.RAG_EMBEDDING_ENGINE,
    app.state.config.RAG_EMBEDDING_MODEL,
    embedding_function=app.state.ef,
    url=(
        app.state.config.RAG_OPENAI_API_BASE_URL
        if app.state.config.RAG_EMBEDDING_ENGINE == "openai"
        else (
            app.state.config.RAG_OLLAMA_BASE_URL
            if app.state.config.RAG_EMBEDDING_ENGINE == "ollama"
            else app.state.config.RAG_AZURE_OPENAI_BASE_URL
        )
    ),
    key=(
        app.state.config.RAG_OPENAI_API_KEY
        if app.state.config.RAG_EMBEDDING_ENGINE == "openai"
        else (
            app.state.config.RAG_OLLAMA_API_KEY
            if app.state.config.RAG_EMBEDDING_ENGINE == "ollama"
            else app.state.config.RAG_AZURE_OPENAI_API_KEY
        )
    ),
    embedding_batch_size=app.state.config.RAG_EMBEDDING_BATCH_SIZE,
    azure_api_version=(
        app.state.config.RAG_AZURE_OPENAI_API_VERSION
        if app.state.config.RAG_EMBEDDING_ENGINE == "azure_openai"
        else None
    ),
)

app.state.RERANKING_FUNCTION = get_reranking_function(
    app.state.config.RAG_RERANKING_ENGINE,
    app.state.config.RAG_RERANKING_MODEL,
    reranking_function=app.state.rf,
)

########################################
#
# CODE EXECUTION
#
########################################

app.state.config.ENABLE_CODE_EXECUTION = ENABLE_CODE_EXECUTION
app.state.config.CODE_EXECUTION_ENGINE = CODE_EXECUTION_ENGINE
app.state.config.CODE_EXECUTION_JUPYTER_URL = CODE_EXECUTION_JUPYTER_URL
app.state.config.CODE_EXECUTION_JUPYTER_AUTH = CODE_EXECUTION_JUPYTER_AUTH
app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN = CODE_EXECUTION_JUPYTER_AUTH_TOKEN
app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD = (
    CODE_EXECUTION_JUPYTER_AUTH_PASSWORD
)
app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT = CODE_EXECUTION_JUPYTER_TIMEOUT

app.state.config.ENABLE_CODE_INTERPRETER = ENABLE_CODE_INTERPRETER
app.state.config.CODE_INTERPRETER_ENGINE = CODE_INTERPRETER_ENGINE
app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE = CODE_INTERPRETER_PROMPT_TEMPLATE

app.state.config.CODE_INTERPRETER_JUPYTER_URL = CODE_INTERPRETER_JUPYTER_URL
app.state.config.CODE_INTERPRETER_JUPYTER_AUTH = CODE_INTERPRETER_JUPYTER_AUTH
app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN = (
    CODE_INTERPRETER_JUPYTER_AUTH_TOKEN
)
app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD = (
    CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD
)
app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT = CODE_INTERPRETER_JUPYTER_TIMEOUT

########################################
#
# IMAGES
#
########################################

app.state.config.IMAGE_GENERATION_ENGINE = IMAGE_GENERATION_ENGINE
app.state.config.ENABLE_IMAGE_GENERATION = ENABLE_IMAGE_GENERATION
app.state.config.ENABLE_IMAGE_PROMPT_GENERATION = ENABLE_IMAGE_PROMPT_GENERATION

app.state.config.IMAGES_OPENAI_API_BASE_URL = IMAGES_OPENAI_API_BASE_URL
app.state.config.IMAGES_OPENAI_API_VERSION = IMAGES_OPENAI_API_VERSION
app.state.config.IMAGES_OPENAI_API_KEY = IMAGES_OPENAI_API_KEY

app.state.config.IMAGES_GEMINI_API_BASE_URL = IMAGES_GEMINI_API_BASE_URL
app.state.config.IMAGES_GEMINI_API_KEY = IMAGES_GEMINI_API_KEY

app.state.config.IMAGE_GENERATION_MODEL = IMAGE_GENERATION_MODEL

app.state.config.AUTOMATIC1111_BASE_URL = AUTOMATIC1111_BASE_URL
app.state.config.AUTOMATIC1111_API_AUTH = AUTOMATIC1111_API_AUTH
app.state.config.AUTOMATIC1111_CFG_SCALE = AUTOMATIC1111_CFG_SCALE
app.state.config.AUTOMATIC1111_SAMPLER = AUTOMATIC1111_SAMPLER
app.state.config.AUTOMATIC1111_SCHEDULER = AUTOMATIC1111_SCHEDULER
app.state.config.COMFYUI_BASE_URL = COMFYUI_BASE_URL
app.state.config.COMFYUI_API_KEY = COMFYUI_API_KEY
app.state.config.COMFYUI_WORKFLOW = COMFYUI_WORKFLOW
app.state.config.COMFYUI_WORKFLOW_NODES = COMFYUI_WORKFLOW_NODES

app.state.config.IMAGE_SIZE = IMAGE_SIZE
app.state.config.IMAGE_STEPS = IMAGE_STEPS


########################################
#
# AUDIO
#
########################################

app.state.config.STT_ENGINE = AUDIO_STT_ENGINE
app.state.config.STT_MODEL = AUDIO_STT_MODEL
app.state.config.STT_SUPPORTED_CONTENT_TYPES = AUDIO_STT_SUPPORTED_CONTENT_TYPES

app.state.config.STT_OPENAI_API_BASE_URL = AUDIO_STT_OPENAI_API_BASE_URL
app.state.config.STT_OPENAI_API_KEY = AUDIO_STT_OPENAI_API_KEY

app.state.config.WHISPER_MODEL = WHISPER_MODEL
app.state.config.WHISPER_VAD_FILTER = WHISPER_VAD_FILTER
app.state.config.DEEPGRAM_API_KEY = DEEPGRAM_API_KEY

app.state.config.AUDIO_STT_AZURE_API_KEY = AUDIO_STT_AZURE_API_KEY
app.state.config.AUDIO_STT_AZURE_REGION = AUDIO_STT_AZURE_REGION
app.state.config.AUDIO_STT_AZURE_LOCALES = AUDIO_STT_AZURE_LOCALES
app.state.config.AUDIO_STT_AZURE_BASE_URL = AUDIO_STT_AZURE_BASE_URL
app.state.config.AUDIO_STT_AZURE_MAX_SPEAKERS = AUDIO_STT_AZURE_MAX_SPEAKERS

app.state.config.TTS_ENGINE = AUDIO_TTS_ENGINE

app.state.config.TTS_MODEL = AUDIO_TTS_MODEL
app.state.config.TTS_VOICE = AUDIO_TTS_VOICE

app.state.config.TTS_OPENAI_API_BASE_URL = AUDIO_TTS_OPENAI_API_BASE_URL
app.state.config.TTS_OPENAI_API_KEY = AUDIO_TTS_OPENAI_API_KEY
app.state.config.TTS_OPENAI_PARAMS = AUDIO_TTS_OPENAI_PARAMS

app.state.config.TTS_API_KEY = AUDIO_TTS_API_KEY
app.state.config.TTS_SPLIT_ON = AUDIO_TTS_SPLIT_ON


app.state.config.TTS_AZURE_SPEECH_REGION = AUDIO_TTS_AZURE_SPEECH_REGION
app.state.config.TTS_AZURE_SPEECH_BASE_URL = AUDIO_TTS_AZURE_SPEECH_BASE_URL
app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT = AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT


app.state.faster_whisper_model = None
app.state.speech_synthesiser = None
app.state.speech_speaker_embeddings_dataset = None


########################################
#
# TASKS
#
########################################


app.state.config.TASK_MODEL = TASK_MODEL
app.state.config.TASK_MODEL_EXTERNAL = TASK_MODEL_EXTERNAL


app.state.config.ENABLE_SEARCH_QUERY_GENERATION = ENABLE_SEARCH_QUERY_GENERATION
app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION = ENABLE_RETRIEVAL_QUERY_GENERATION
app.state.config.ENABLE_AUTOCOMPLETE_GENERATION = ENABLE_AUTOCOMPLETE_GENERATION
app.state.config.ENABLE_TAGS_GENERATION = ENABLE_TAGS_GENERATION
app.state.config.ENABLE_TITLE_GENERATION = ENABLE_TITLE_GENERATION
app.state.config.ENABLE_FOLLOW_UP_GENERATION = ENABLE_FOLLOW_UP_GENERATION


app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE = TITLE_GENERATION_PROMPT_TEMPLATE
app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE = TAGS_GENERATION_PROMPT_TEMPLATE
app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE = (
    IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE
)
app.state.config.FOLLOW_UP_GENERATION_PROMPT_TEMPLATE = (
    FOLLOW_UP_GENERATION_PROMPT_TEMPLATE
)

app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = (
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
)
app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE = QUERY_GENERATION_PROMPT_TEMPLATE
app.state.config.AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE = (
    AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE
)
app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH = (
    AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH
)


########################################
#
# WEBUI
#
########################################

app.state.MODELS = {}


class RedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check if the request is a GET request
        if request.method == "GET":
            path = request.url.path
            query_params = dict(parse_qs(urlparse(str(request.url)).query))

            redirect_params = {}

            # Check for the specific watch path and the presence of 'v' parameter
            if path.endswith("/watch") and "v" in query_params:
                # Extract the first 'v' parameter
                youtube_video_id = query_params["v"][0]
                redirect_params["youtube"] = youtube_video_id

            if "shared" in query_params and len(query_params["shared"]) > 0:
                # PWA share_target support

                text = query_params["shared"][0]
                if text:
                    urls = re.match(r"https://\S+", text)
                    if urls:
                        from open_webui.retrieval.loaders.youtube import _parse_video_id

                        if youtube_video_id := _parse_video_id(urls[0]):
                            redirect_params["youtube"] = youtube_video_id
                        else:
                            redirect_params["load-url"] = urls[0]
                    else:
                        redirect_params["q"] = text

            if redirect_params:
                redirect_url = f"/?{urlencode(redirect_params)}"
                return RedirectResponse(url=redirect_url)

        # Proceed with the normal flow of other requests
        response = await call_next(request)
        return response


# Add the middleware to the app
if ENABLE_COMPRESSION_MIDDLEWARE:
    app.add_middleware(CompressMiddleware)

app.add_middleware(RedirectMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


@app.middleware("http")
async def commit_session_after_request(request: Request, call_next):
    response = await call_next(request)
    # log.debug("Commit session after request")
    Session.commit()
    return response


@app.middleware("http")
async def check_url(request: Request, call_next):
    start_time = int(time.time())
    request.state.token = get_http_authorization_cred(
        request.headers.get("Authorization")
    )

    request.state.enable_api_key = app.state.config.ENABLE_API_KEY
    response = await call_next(request)
    process_time = int(time.time()) - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http")
async def inspect_websocket(request: Request, call_next):
    if (
        "/ws/socket.io" in request.url.path
        and request.query_params.get("transport") == "websocket"
    ):
        upgrade = (request.headers.get("Upgrade") or "").lower()
        connection = (request.headers.get("Connection") or "").lower().split(",")
        # Check that there's the correct headers for an upgrade, else reject the connection
        # This is to work around this upstream issue: https://github.com/miguelgrinberg/python-engineio/issues/367
        if upgrade != "websocket" or "upgrade" not in connection:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid WebSocket upgrade request"},
            )
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/ws", socket_app)


app.include_router(ollama.router, prefix="/ollama", tags=["ollama"])
app.include_router(openai.router, prefix="/openai", tags=["openai"])


app.include_router(pipelines.router, prefix="/api/v1/pipelines", tags=["pipelines"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(images.router, prefix="/api/v1/images", tags=["images"])

app.include_router(audio.router, prefix="/api/v1/audio", tags=["audio"])
app.include_router(retrieval.router, prefix="/api/v1/retrieval", tags=["retrieval"])

app.include_router(configs.router, prefix="/api/v1/configs", tags=["configs"])

app.include_router(auths.router, prefix="/api/v1/auths", tags=["auths"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

app.include_router(
    user_models.router, prefix="/api/v1/user/models", tags=["user_models"]
)
app.include_router(channels.router, prefix="/api/v1/channels", tags=["channels"])
app.include_router(announcements.router, prefix="/api/v1/announcements", tags=["announcements"])
app.include_router(chats.router, prefix="/api/v1/chats", tags=["chats"])
app.include_router(notes.router, prefix="/api/v1/notes", tags=["notes"])


app.include_router(models.router, prefix="/api/v1/models", tags=["models"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"])
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])
app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])

app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])
app.include_router(memories.router, prefix="/api/v1/memories", tags=["memories"])
app.include_router(folders.router, prefix="/api/v1/folders", tags=["folders"])
app.include_router(groups.router, prefix="/api/v1/groups", tags=["groups"])
app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
app.include_router(functions.router, prefix="/api/v1/functions", tags=["functions"])
app.include_router(
    evaluations.router, prefix="/api/v1/evaluations", tags=["evaluations"]
)
app.include_router(utils.router, prefix="/api/v1/utils", tags=["utils"])

# SCIM 2.0 API for identity management
if SCIM_ENABLED:
    app.include_router(scim.router, prefix="/api/v1/scim/v2", tags=["scim"])


try:
    audit_level = AuditLevel(AUDIT_LOG_LEVEL)
except ValueError as e:
    logger.error(f"Invalid audit level: {AUDIT_LOG_LEVEL}. Error: {e}")
    audit_level = AuditLevel.NONE

if audit_level != AuditLevel.NONE:
    app.add_middleware(
        AuditLoggingMiddleware,
        audit_level=audit_level,
        excluded_paths=AUDIT_EXCLUDED_PATHS,
        max_body_size=MAX_BODY_LOG_SIZE,
    )
##################################
#
# Chat Endpoints
#
##################################


@app.get("/api/models")
@app.get("/api/v1/models")  # Experimental: Compatibility with OpenAI API
async def get_models(
    request: Request, refresh: bool = False, user=Depends(get_verified_user)
):
    all_models = await get_all_models(request, refresh=refresh, user=user)

    models = []
    for model in all_models:
        # Filter out filter pipelines
        if "pipeline" in model and model["pipeline"].get("type", None) == "filter":
            continue

        try:
            model_tags = [
                tag.get("name")
                for tag in model.get("info", {}).get("meta", {}).get("tags", [])
            ]
            tags = [tag.get("name") for tag in model.get("tags", [])]

            tags = list(set(model_tags + tags))
            model["tags"] = [{"name": tag} for tag in tags]
        except Exception as e:
            log.debug(f"Error processing model tags: {e}")
            model["tags"] = []
            pass

        models.append(model)

    model_order_list = request.app.state.config.MODEL_ORDER_LIST
    if model_order_list:
        model_order_dict = {model_id: i for i, model_id in enumerate(model_order_list)}
        # Sort models by order list priority, with fallback for those not in the list
        models.sort(
            key=lambda model: (
                model_order_dict.get(model.get("id", ""), float("inf")),
                (model.get("name", "") or ""),
            )
        )

    models = get_filtered_models(models, user)

    log.debug(
        f"/api/models returned filtered models accessible to the user: {json.dumps([model.get('id') for model in models])}"
    )
    return {"data": models}


@app.get("/api/models/base")
async def get_base_models(request: Request, user=Depends(get_admin_user)):
    models = await get_all_base_models(request, user=user)
    return {"data": models}


##################################
# Embeddings
##################################


@app.post("/api/embeddings")
@app.post("/api/v1/embeddings")  # Experimental: Compatibility with OpenAI API
async def embeddings(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    """
    OpenAI-compatible embeddings endpoint.

    This handler:
      - Performs user/model checks and dispatches to the correct backend.
      - Supports OpenAI, Ollama, arena models, pipelines, and any compatible provider.

    Args:
        request (Request): Request context.
        form_data (dict): OpenAI-like payload (e.g., {"model": "...", "input": [...]})
        user (UserModel): Authenticated user.

    Returns:
        dict: OpenAI-compatible embeddings response.
    """
    # Make sure models are loaded in app state
    if not request.app.state.MODELS:
        await get_all_models(request, user=user)
    # Use generic dispatcher in utils.embeddings
    return await generate_embeddings(request, form_data, user)


@app.post("/api/chat/completions")
@app.post("/api/v1/chat/completions")  # Experimental: Compatibility with OpenAI API
async def chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
):
    """
    聊天完成接口 - 处理用户与 AI 模型的对话请求

    核心功能:
    1. 模型验证: 检查模型是否存在及用户访问权限
    2. 元数据构建: 提取 chat_id, message_id, session_id 等上下文信息
    3. Payload 处理: 通过 process_chat_payload 处理消息、工具调用、文件等
    4. 聊天执行: 调用 chat_completion_handler 与 LLM 交互
    5. 响应处理: 通过 process_chat_response 处理流式/非流式响应
    6. 异步任务: 如果有 session_id，创建后台任务异步执行

    Args:
        request: FastAPI Request 对象
        form_data: 聊天请求数据，包含:
            - model: 模型 ID
            - messages: 对话历史 (OpenAI 格式)
            - chat_id: 聊天会话 ID
            - id: 消息 ID
            - session_id: 会话 ID (用于异步任务)
            - tool_ids: 工具 ID 列表
            - files: 附加文件列表
            - stream: 是否流式响应
        user: 已验证的用户对象

    Returns:
        - 同步模式: 返回 LLM 响应 (流式 StreamingResponse 或完整 JSON)
        - 异步模式: 返回 {"status": True, "task_id": "xxx"}

    Raises:
        HTTPException 400: 模型不存在、无访问权限、参数错误
        HTTPException 404: Chat 不存在

    处理流程:
    1. 加载所有模型到 app.state.MODELS
    2. 验证模型访问权限 (check_model_access)
    3. 构建 metadata (包含 user_id, chat_id, tool_ids 等)
    4. 定义 process_chat 内部函数:
       - 调用 process_chat_payload (处理 Pipeline/Filter/Tools)
       - 调用 chat_completion_handler (与 LLM 交互)
       - 更新数据库消息记录
       - 调用 process_chat_response (处理响应、事件发射)
    5. 根据是否有 session_id 决定同步/异步执行
    """
    # === 1. 初始化阶段：加载模型列表 ===
    if not request.app.state.MODELS:
        await get_all_models(request, user=user)  # 从数据库和后端服务加载所有可用模型

    # === 2. 提取请求参数 ===
    form_data = await transform_user_model_if_needed(form_data, user)
    model_id = form_data.get("model", None)  # 用户选择的模型 ID (如 "gpt-4")
    model_item = form_data.pop("model_item", {})  # 模型元数据 (包含 direct 标志)
    tasks = form_data.pop("background_tasks", None)  # 后台任务列表

    metadata = {}
    try:
        # === 3. 模型验证与权限检查 ===
        if not model_item.get("direct", False):
            # 标准模式：使用平台内置模型
            if model_id not in request.app.state.MODELS:
                raise Exception(f"Model not found: {model_id}")
 
            model = request.app.state.MODELS[model_id]  # 从缓存获取模型配置
            model_info = Models.get_model_by_id(model_id)  # 从数据库获取模型详细信息

            # 检查用户是否有权限访问该模型
            if not BYPASS_MODEL_ACCESS_CONTROL and (
                user.role != "admin" or not BYPASS_ADMIN_ACCESS_CONTROL
            ):
                try:
                    check_model_access(user, model)  # 检查 RBAC 权限
                except Exception as e:
                    raise e
        else:
            # Direct 模式：用户直接传入 OpenAI API 等外部模型配置
            model = model_item
            model_info = None

            request.state.direct = True  # 标记为直连模式
            request.state.model = model

        # === 4. 提取模型参数 ===
        model_info_params = (
            model_info.params.model_dump() if model_info and model_info.params else {}
        )

        # 流式响应分块大小 (用于控制 SSE 推送频率)
        stream_delta_chunk_size = form_data.get("params", {}).get(
            "stream_delta_chunk_size"
        )
        # 推理标签 (用于标记 AI 的思考过程，如 <think>...</think>)
        reasoning_tags = form_data.get("params", {}).get("reasoning_tags")

        # 模型参数优先级高于请求参数
        if model_info_params.get("stream_delta_chunk_size"):
            stream_delta_chunk_size = model_info_params.get("stream_delta_chunk_size")

        if model_info_params.get("reasoning_tags") is not None:
            reasoning_tags = model_info_params.get("reasoning_tags")

        # === 5. 构建元数据 (metadata) - 贯穿整个处理流程的上下文 ===
        metadata = {
            "user_id": user.id,
            "chat_id": form_data.pop("chat_id", None),  # 聊天会话 ID
            "message_id": form_data.pop("id", None),  # 当前消息 ID
            "session_id": form_data.pop("session_id", None),  # WebSocket 会话 ID (异步任务)
            "filter_ids": form_data.pop("filter_ids", []),  # Pipeline Filter ID 列表
            "tool_ids": form_data.get("tool_ids", None),  # 工具/函数调用 ID 列表
            "tool_servers": form_data.pop("tool_servers", None),  # 外部工具服务器配置
            "files": form_data.get("files", None),  # 用户上传的文件列表
            "features": form_data.get("features", {}),  # 功能开关 (如 web_search)
            "variables": form_data.get("variables", {}),  # 模板变量
            "model": model,  # 模型配置对象
            "direct": model_item.get("direct", False),  # 是否直连模式
            "params": {
                "stream_delta_chunk_size": stream_delta_chunk_size,
                "reasoning_tags": reasoning_tags,
                "function_calling": (
                    "native"  # 原生函数调用 (如 OpenAI Function Calling)
                    if (
                        form_data.get("params", {}).get("function_calling") == "native"
                        or model_info_params.get("function_calling") == "native"
                    )
                    else "default"  # 默认模式 (通过 Prompt 实现)
                ),
            },
        }

        # === 6. 权限二次验证：检查用户是否拥有该 chat ===
        if metadata.get("chat_id") and (user and user.role != "admin"):
            if not metadata["chat_id"].startswith("local:"):  # local: 前缀表示临时会话
                chat = Chats.get_chat_by_id_and_user_id(metadata["chat_id"], user.id)
                if chat is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=ERROR_MESSAGES.DEFAULT(),
                    )

        # === 7. 保存元数据到请求状态和 form_data ===
        request.state.metadata = metadata  # 供其他中间件/处理器访问
        form_data["metadata"] = metadata  # 传递给下游处理函数

    except Exception as e:
        log.debug(f"Error processing chat metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # === 8. 定义内部处理函数 process_chat ===
    async def process_chat(request, form_data, user, metadata, model):
        """处理完整的聊天流程：Payload 处理 → LLM 调用 → 响应处理"""

        async def ensure_initial_summary():
            """
            如果是新聊天，其中没有summary，获得最近的若干次互动，生成一次摘要并保存。
            触发条件：非 local 会话，无已有摘要。
            """

            # 获取 chat_id（跳过本地会话）
            chat_id = metadata.get("chat_id")
            if not chat_id or str(chat_id).startswith("local:"):
                return

            try:
                # 检查是否已有摘要
                old_summary = Chats.get_summary_by_user_id_and_chat_id(user.id, chat_id)
                if CHAT_DEBUG_FLAG:
                    print(f"[summary:init] chat_id={chat_id} 现有摘要={bool(old_summary)}")
                if old_summary:
                    if CHAT_DEBUG_FLAG:
                        print(f"[summary:init] chat_id={chat_id} 已存在摘要，跳过生成")
                    return

                # 获取消息列表
                # 如果历史消息非常多（比如刚导入的），只取最近的 N 条可能会丢失早期上下文
                # 策略：分块生成摘要。先取较早的消息生成基础摘要，再结合最近消息生成最终摘要
                
                # 1. 获取全量消息（按时间排序）
                all_messages = get_recent_messages_by_user_id(user.id, chat_id, -1) # -1 表示获取全部
                
                if CHAT_DEBUG_FLAG:
                    print(f"[summary:init] chat_id={chat_id} 全量消息数={len(all_messages)}")

                if not all_messages:
                    if CHAT_DEBUG_FLAG:
                        print(f"[summary:init] chat_id={chat_id} 无可用消息，跳过生成")
                    return

                # 2. 如果消息量适中 (< 200)，直接生成
                if len(all_messages) <= 200:
                    messages_for_summary = all_messages
                    model_id = form_data.get("model")
                    summary_text = summarize(messages_for_summary, None, model=model_id)
                else:
                    # 3. 如果消息量很大，进行分块压缩
                    # 这里的策略是：
                    # a. 取前 50% 的消息（或者前 N 条），生成一个 "Initial Summary"
                    # b. 将这个 Initial Summary 作为 existing_summary，配合后半部分消息生成最终摘要
                    
                    if CHAT_DEBUG_FLAG:
                        print(f"[summary:init] chat_id={chat_id} 消息过多，执行分块摘要策略...")
                    
                    # 简单的二分法：旧消息块 (除最后100条外) + 新消息块 (最后100条)
                    # 这样能保证最近的对话被精细处理，而久远的对话被压缩
                    split_idx = max(len(all_messages) - 100, 0)
                    older_messages = all_messages[:split_idx]
                    recent_messages = all_messages[split_idx:]
                    
                    model_id = form_data.get("model")
                    
                    # 第一步：压缩旧消息
                    # 注意：如果旧消息依然过多（>500），summarize 内部会截取最后 max_messages（默认120），
                    # 所以对于超大导入，我们可能需要循环压缩。但为了性能，这里暂只做一次“旧历史压缩”。
                    # 为了让 summarize 能够处理更多旧消息，我们可以临时调大 max_messages 限制，
                    # 或者分批调用。鉴于性能，我们只取旧消息的“精华片段”（比如每隔几条取一条，或者只取两端）。
                    # 简化方案：直接把 older_messages 传给 summarize，让它内部去切片/截断
                    # TODO: 真正完美的方案是循环 reduce，但耗时太久。
                    
                    if CHAT_DEBUG_FLAG:
                        print(f"[summary:init] 生成旧历史摘要 (msgs={len(older_messages)})...")
                    base_summary = summarize(older_messages, None, model=model_id)
                    
                    if CHAT_DEBUG_FLAG:
                        print(f"[summary:init] 生成最终摘要 (base_summary_len={len(base_summary)}, recent_msgs={len(recent_messages)})...")
                    # 第二步：基于旧摘要 + 最近消息生成最终摘要
                    summary_text = summarize(recent_messages, old_summary=base_summary, model=model_id)
                    
                    messages_for_summary = recent_messages # 用于后续计算 last_id 等

                last_id = messages_for_summary[-1].get("id") if messages_for_summary else None
                recent_ids = [m.get("id") for m in messages_for_summary[-20:] if m.get("id")]  # 记录最近20条消息为冷启动消息

                if CHAT_DEBUG_FLAG:
                    print(
                        f"[summary:init] chat_id={chat_id} 生成首条摘要，msg_count={len(messages_for_summary)}, last_id={last_id}, recent_ids={len(recent_ids)}"
                    )

                    print("[summary:init]: messages_for_summary")
                    for i in messages_for_summary:
                        print(i['role'], "  ", i['content'][:100])

                res = Chats.set_summary_by_user_id_and_chat_id(
                    user.id,
                    chat_id,
                    summary_text,
                    last_id,
                    int(time.time()),
                    recent_message_ids=recent_ids,
                )
                if not res:
                    if CHAT_DEBUG_FLAG:
                        print(f"[summary:init] chat_id={chat_id} 写入摘要失败")
            except Exception as e:
                log.exception(f"initial summary failed: {e}")

        try:
            await ensure_initial_summary()

            # 8.1 Payload 预处理：执行 Pipeline Filters、工具注入、RAG 检索等
            # remark：并不涉及消息的持久化，只涉及发送给 LLM 前，上下文的封装
            form_data, metadata, events = await process_chat_payload(
                request, form_data, user, metadata, model
            )

            # 8.2 调用 LLM 完成对话 (核心)
            response = await chat_completion_handler(request, form_data, user, chatting_completion = True)

            # 8.3 更新数据库：保存模型 ID 到消息记录
            if metadata.get("chat_id") and metadata.get("message_id"):
                try:
                    if not metadata["chat_id"].startswith("local:"):
                        Chats.upsert_message_to_chat_by_id_and_message_id(
                            metadata["chat_id"],
                            metadata["message_id"],
                            {
                                "model": model_id,
                            },
                        )
                except:
                    pass

            # 8.4 响应后处理：执行后置 Pipeline、事件发射、任务回调等
            return await process_chat_response(
                request, response, form_data, user, metadata, model, events, tasks
            )

        # 8.5 异常处理：取消任务
        except asyncio.CancelledError:
            log.info("Chat processing was cancelled")
            try:
                event_emitter = get_event_emitter(metadata)
                await event_emitter(
                    {"type": "chat:tasks:cancel"},  # 通知前端任务已取消
                )
            except Exception as e:
                pass

        # 8.6 异常处理：记录错误到数据库并通知前端
        except Exception as e:
            log.exception(f"Error processing chat payload: {e}")
            if metadata.get("chat_id") and metadata.get("message_id"):
                try:
                    # 将错误信息保存到消息记录
                    if not metadata["chat_id"].startswith("local:"):
                        Chats.upsert_message_to_chat_by_id_and_message_id(
                            metadata["chat_id"],
                            metadata["message_id"],
                            {
                                "error": {"content": str(e)},
                            },
                        )

                    # 通过 WebSocket 发送错误事件到前端
                    event_emitter = get_event_emitter(metadata)
                    await event_emitter(
                        {
                            "type": "chat:message:error",
                            "data": {"error": {"content": str(e)}},
                        }
                    )
                    await event_emitter(
                        {"type": "chat:tasks:cancel"},
                    )

                except:
                    pass

        # 8.7 清理资源：断开 MCP 客户端连接
        finally:
            try:
                if mcp_clients := metadata.get("mcp_clients"):
                    for client in mcp_clients.values():
                        await client.disconnect()  # 断开 Model Context Protocol 客户端
            except Exception as e:
                log.debug(f"Error cleaning up: {e}")
                pass

    # === 9. 决定执行模式：异步任务 vs 同步执行 ===
    if (
        metadata.get("session_id")
        and metadata.get("chat_id")
        and metadata.get("message_id")
    ):
        # 异步模式：创建后台任务，立即返回 task_id 给前端
        # 前端通过 WebSocket 监听任务状态和流式响应
        task_id, _ = await create_task(
            request.app.state.redis,
            process_chat(request, form_data, user, metadata, model),
            id=metadata["chat_id"],
        )
        return {"status": True, "task_id": task_id}
    else:
        # 同步模式：直接执行并返回响应 (流式或完整)
        return await process_chat(request, form_data, user, metadata, model)


# Alias for chat_completion (Legacy)
generate_chat_completions = chat_completion
generate_chat_completion = chat_completion


@app.post("/api/chat/tutorial")
async def chat_completion_tutorial(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    """
    最小可正常工作的示例：复用核心聊天链路，支持直连/历史消息/流式返回。

    - 入参与 /api/chat/completions 基本兼容，但不做额外后台任务。
    - 若提供 chat_id/message_id，会读取历史消息并可触发 WS 事件；否则直接返回 SSE。
    """
    # 直连兼容
    model_item = form_data.pop("model_item", {})
    if model_item.get("direct"):
        request.state.direct = True
        request.state.model = model_item

    # 确保模型可用
    if not request.app.state.MODELS:
        await get_all_models(request, user=user)

    model_id = form_data.get("model") or next(iter(request.app.state.MODELS.keys()))
    if model_id not in request.app.state.MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Model not found"
        )
    model = request.app.state.MODELS[model_id]
    if user.role == "user":
        check_model_access(user, model)

    # 取消息历史：优先用传入 messages，否则按 chat_id 取全量
    messages = form_data.get("messages") or []
    chat_id = form_data.get("chat_id")
    message_id = form_data.get("id") or form_data.get("message_id")
    if not messages and chat_id:
        messages_map = Chats.get_messages_map_by_chat_id(chat_id)
        if messages_map:
            if message_id and message_id in messages_map:
                messages = get_message_list(messages_map, message_id)
            else:
                messages = list(messages_map.values())

    # 准备 metadata，便于复用后续事件/DB 逻辑
    metadata = {
        "user_id": user.id,
        "chat_id": chat_id,
        "message_id": message_id,
        "session_id": form_data.get("session_id"),
        "model": model,
        "direct": model_item.get("direct", False),
        "params": {},
    }
    request.state.metadata = metadata
    form_data["metadata"] = metadata

    # 核心链路：预处理 -> 调模型 -> 流式/非流式响应处理
    form_data["model"] = model_id
    form_data["messages"] = messages
    form_data["stream"] = True  # 强制流式，便于示例

    form_data, metadata, events = await process_chat_payload(
        request, form_data, user, metadata, model
    )
    response = await chat_completion_handler(request, form_data, user)
    return await process_chat_response(
        request, response, form_data, user, metadata, model, events, tasks=None
    )


@app.post("/api/chat/completed")
async def chat_completed(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    try:
        model_item = form_data.pop("model_item", {})

        if model_item.get("direct", False):
            request.state.direct = True
            request.state.model = model_item

        return await chat_completed_handler(request, form_data, user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@app.post("/api/chat/actions/{action_id}")
async def chat_action(
    request: Request, action_id: str, form_data: dict, user=Depends(get_verified_user)
):
    try:
        model_item = form_data.pop("model_item", {})

        if model_item.get("direct", False):
            request.state.direct = True
            request.state.model = model_item

        return await chat_action_handler(request, action_id, form_data, user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@app.post("/api/tasks/stop/{task_id}")
async def stop_task_endpoint(
    request: Request, task_id: str, user=Depends(get_verified_user)
):
    try:
        result = await stop_task(request.app.state.redis, task_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@app.get("/api/tasks")
async def list_tasks_endpoint(request: Request, user=Depends(get_verified_user)):
    return {"tasks": await list_tasks(request.app.state.redis)}


@app.get("/api/tasks/chat/{chat_id}")
async def list_tasks_by_chat_id_endpoint(
    request: Request, chat_id: str, user=Depends(get_verified_user)
):
    chat = Chats.get_chat_by_id(chat_id)
    if chat is None or chat.user_id != user.id:
        return {"task_ids": []}

    task_ids = await list_task_ids_by_item_id(request.app.state.redis, chat_id)

    log.debug(f"Task IDs for chat {chat_id}: {task_ids}")
    return {"task_ids": task_ids}


##################################
#
# Config Endpoints
#
##################################


@app.get("/api/config")
async def get_app_config(request: Request):
    user = None
    token = None

    auth_header = request.headers.get("Authorization")
    if auth_header:
        cred = get_http_authorization_cred(auth_header)
        if cred:
            token = cred.credentials

    if not token and "token" in request.cookies:
        token = request.cookies.get("token")

    if token:
        try:
            data = decode_token(token)
        except Exception as e:
            log.debug(e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        if data is not None and "id" in data:
            user = Users.get_user_by_id(data["id"])

    user_count = Users.get_num_users()
    onboarding = False

    if user is None:
        onboarding = user_count == 0

    return {
        **({"onboarding": True} if onboarding else {}),
            "status": True,
            "name": app.state.WEBUI_NAME,
            "version": VERSION,
            "default_locale": str(DEFAULT_LOCALE),
            "oauth": {
            "providers": {
                name: config.get("name", name)
                for name, config in OAUTH_PROVIDERS.items()
            }
        },
            "features": {
                "auth": WEBUI_AUTH,
                "auth_trusted_header": bool(app.state.AUTH_TRUSTED_EMAIL_HEADER),
                "enable_signup_password_confirmation": ENABLE_SIGNUP_PASSWORD_CONFIRMATION,
                "enable_signup_email_verification": True,
                "enable_ldap": app.state.config.ENABLE_LDAP,
                "enable_api_key": app.state.config.ENABLE_API_KEY,
                "enable_signup": app.state.config.ENABLE_SIGNUP,
                "enable_login_form": app.state.config.ENABLE_LOGIN_FORM,
                "enable_websocket": ENABLE_WEBSOCKET_SUPPORT,
                "enable_version_update_check": ENABLE_VERSION_UPDATE_CHECK,
                "signup_email_verification_send_interval": app.state.email_verification_config["send_interval"],
            **(
                {
                    "enable_direct_connections": app.state.config.ENABLE_DIRECT_CONNECTIONS,
                    "enable_channels": app.state.config.ENABLE_CHANNELS,
                    "enable_notes": app.state.config.ENABLE_NOTES,
                    "enable_web_search": app.state.config.ENABLE_WEB_SEARCH,
                    "enable_code_execution": app.state.config.ENABLE_CODE_EXECUTION,
                    "enable_code_interpreter": app.state.config.ENABLE_CODE_INTERPRETER,
                    "enable_image_generation": app.state.config.ENABLE_IMAGE_GENERATION,
                    "enable_autocomplete_generation": app.state.config.ENABLE_AUTOCOMPLETE_GENERATION,
                    "enable_community_sharing": app.state.config.ENABLE_COMMUNITY_SHARING,
                    "enable_message_rating": app.state.config.ENABLE_MESSAGE_RATING,
                    "enable_user_webhooks": app.state.config.ENABLE_USER_WEBHOOKS,
                    "enable_admin_export": ENABLE_ADMIN_EXPORT,
                    "enable_admin_chat_access": ENABLE_ADMIN_CHAT_ACCESS,
                    "enable_google_drive_integration": app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
                    "enable_onedrive_integration": app.state.config.ENABLE_ONEDRIVE_INTEGRATION,
                    **(
                        {
                            "enable_onedrive_personal": ENABLE_ONEDRIVE_PERSONAL,
                            "enable_onedrive_business": ENABLE_ONEDRIVE_BUSINESS,
                        }
                        if app.state.config.ENABLE_ONEDRIVE_INTEGRATION
                        else {}
                    ),
                }
                if user is not None
                else {}
            ),
        },
        **(
            {
                "default_models": app.state.config.DEFAULT_MODELS,
                "default_prompt_suggestions": app.state.config.DEFAULT_PROMPT_SUGGESTIONS,
                "user_count": user_count,
                "code": {
                    "engine": app.state.config.CODE_EXECUTION_ENGINE,
                },
                "audio": {
                    "tts": {
                        "engine": app.state.config.TTS_ENGINE,
                        "voice": app.state.config.TTS_VOICE,
                        "split_on": app.state.config.TTS_SPLIT_ON,
                    },
                    "stt": {
                        "engine": app.state.config.STT_ENGINE,
                    },
                },
                "file": {
                    "max_size": app.state.config.FILE_MAX_SIZE,
                    "max_count": app.state.config.FILE_MAX_COUNT,
                    "image_compression": {
                        "width": app.state.config.FILE_IMAGE_COMPRESSION_WIDTH,
                        "height": app.state.config.FILE_IMAGE_COMPRESSION_HEIGHT,
                    },
                },
                "permissions": {**app.state.config.USER_PERMISSIONS},
                "google_drive": {
                    "client_id": GOOGLE_DRIVE_CLIENT_ID.value,
                    "api_key": GOOGLE_DRIVE_API_KEY.value,
                },
                "onedrive": {
                    "client_id_personal": ONEDRIVE_CLIENT_ID_PERSONAL,
                    "client_id_business": ONEDRIVE_CLIENT_ID_BUSINESS,
                    "sharepoint_url": ONEDRIVE_SHAREPOINT_URL.value,
                    "sharepoint_tenant_id": ONEDRIVE_SHAREPOINT_TENANT_ID.value,
                },
                "ui": {
                    "pending_user_overlay_title": app.state.config.PENDING_USER_OVERLAY_TITLE,
                    "pending_user_overlay_content": app.state.config.PENDING_USER_OVERLAY_CONTENT,
                    "response_watermark": app.state.config.RESPONSE_WATERMARK,
                },
                "license_metadata": app.state.LICENSE_METADATA,
                **(
                    {
                        "active_entries": app.state.USER_COUNT,
                    }
                    if user.role == "admin"
                    else {}
                ),
            }
            if user is not None and (user.role in ["admin", "user"])
            else {
                **(
                    {
                        "ui": {
                            "pending_user_overlay_title": app.state.config.PENDING_USER_OVERLAY_TITLE,
                            "pending_user_overlay_content": app.state.config.PENDING_USER_OVERLAY_CONTENT,
                        }
                    }
                    if user and user.role == "pending"
                    else {}
                ),
                **(
                    {
                        "metadata": {
                            "login_footer": app.state.LICENSE_METADATA.get(
                                "login_footer", ""
                            ),
                            "auth_logo_position": app.state.LICENSE_METADATA.get(
                                "auth_logo_position", ""
                            ),
                        }
                    }
                    if app.state.LICENSE_METADATA
                    else {}
                ),
            }
        ),
    }


class UrlForm(BaseModel):
    url: str


@app.get("/api/webhook")
async def get_webhook_url(user=Depends(get_admin_user)):
    return {
        "url": app.state.config.WEBHOOK_URL,
    }


@app.post("/api/webhook")
async def update_webhook_url(form_data: UrlForm, user=Depends(get_admin_user)):
    app.state.config.WEBHOOK_URL = form_data.url
    app.state.WEBHOOK_URL = app.state.config.WEBHOOK_URL
    return {"url": app.state.config.WEBHOOK_URL}


@app.get("/api/version")
async def get_app_version():
    return {
        "version": VERSION,
    }


@app.get("/api/version/updates")
async def get_app_latest_release_version(user=Depends(get_verified_user)):
    if not ENABLE_VERSION_UPDATE_CHECK:
        log.debug(
            f"Version update check is disabled, returning current version as latest version"
        )
        return {"current": VERSION, "latest": VERSION}
    try:
        timeout = aiohttp.ClientTimeout(total=1)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(
                "https://api.github.com/repos/open-webui/open-webui/releases/latest",
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                response.raise_for_status()
                data = await response.json()
                latest_version = data["tag_name"]

                return {"current": VERSION, "latest": latest_version[1:]}
    except Exception as e:
        log.debug(e)
        return {"current": VERSION, "latest": VERSION}


@app.get("/api/changelog")
async def get_app_changelog():
    return {key: CHANGELOG[key] for idx, key in enumerate(CHANGELOG) if idx < 5}


@app.get("/api/usage")
async def get_current_usage(user=Depends(get_verified_user)):
    """
    Get current usage statistics for Cakumi.
    This is an experimental endpoint and subject to change.
    """
    try:
        return {"model_ids": get_models_in_use(), "user_ids": get_active_user_ids()}
    except Exception as e:
        log.error(f"Error getting usage statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


############################
# OAuth Login & Callback
############################


# Initialize OAuth client manager with any MCP tool servers using OAuth 2.1
if len(app.state.config.TOOL_SERVER_CONNECTIONS) > 0:
    for tool_server_connection in app.state.config.TOOL_SERVER_CONNECTIONS:
        if tool_server_connection.get("type", "openapi") == "mcp":
            server_id = tool_server_connection.get("info", {}).get("id")
            auth_type = tool_server_connection.get("auth_type", "none")
            if server_id and auth_type == "oauth_2.1":
                oauth_client_info = tool_server_connection.get("info", {}).get(
                    "oauth_client_info", ""
                )

                try:
                    oauth_client_info = decrypt_data(oauth_client_info)
                    app.state.oauth_client_manager.add_client(
                        f"mcp:{server_id}",
                        OAuthClientInformationFull(**oauth_client_info),
                    )
                except Exception as e:
                    log.error(
                        f"Error adding OAuth client for MCP tool server {server_id}: {e}"
                    )
                    pass

try:
    if ENABLE_STAR_SESSIONS_MIDDLEWARE:
        redis_session_store = RedisStore(
            url=REDIS_URL,
            prefix=(f"{REDIS_KEY_PREFIX}:session:" if REDIS_KEY_PREFIX else "session:"),
        )

        app.add_middleware(SessionAutoloadMiddleware)
        app.add_middleware(
            StarSessionsMiddleware,
            store=redis_session_store,
            cookie_name="owui-session",
            cookie_same_site=WEBUI_SESSION_COOKIE_SAME_SITE,
            cookie_https_only=WEBUI_SESSION_COOKIE_SECURE,
        )
        log.info("Using Redis for session")
    else:
        raise ValueError("No Redis URL provided")
except Exception as e:
    app.add_middleware(
        SessionMiddleware,
        secret_key=WEBUI_SECRET_KEY,
        session_cookie="owui-session",
        same_site=WEBUI_SESSION_COOKIE_SAME_SITE,
        https_only=WEBUI_SESSION_COOKIE_SECURE,
    )


@app.get("/oauth/clients/{client_id}/authorize")
async def oauth_client_authorize(
    client_id: str,
    request: Request,
    response: Response,
    user=Depends(get_verified_user),
):
    return await oauth_client_manager.handle_authorize(request, client_id=client_id)


@app.get("/oauth/clients/{client_id}/callback")
async def oauth_client_callback(
    client_id: str,
    request: Request,
    response: Response,
    user=Depends(get_verified_user),
):
    return await oauth_client_manager.handle_callback(
        request,
        client_id=client_id,
        user_id=user.id if user else None,
        response=response,
    )


@app.get("/oauth/{provider}/login")
async def oauth_login(provider: str, request: Request):
    return await oauth_manager.handle_login(request, provider)


# OAuth login logic is as follows:
# 1. Attempt to find a user with matching subject ID, tied to the provider
# 2. If OAUTH_MERGE_ACCOUNTS_BY_EMAIL is true, find a user with the email address provided via OAuth
#    - This is considered insecure in general, as OAuth providers do not always verify email addresses
# 3. If there is no user, and ENABLE_OAUTH_SIGNUP is true, create a user
#    - Email addresses are considered unique, so we fail registration if the email address is already taken
@app.get("/oauth/{provider}/login/callback")
@app.get("/oauth/{provider}/callback")  # Legacy endpoint
async def oauth_login_callback(provider: str, request: Request, response: Response):
    return await oauth_manager.handle_callback(request, provider, response)


@app.get("/manifest.json")
async def get_manifest_json():
    if app.state.EXTERNAL_PWA_MANIFEST_URL:
        return requests.get(app.state.EXTERNAL_PWA_MANIFEST_URL).json()
    else:
        return {
            "name": app.state.WEBUI_NAME,
            "short_name": app.state.WEBUI_NAME,
            "description": f"{app.state.WEBUI_NAME} is an open, extensible, user-friendly interface for AI that adapts to your workflow.",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#343541",
            "icons": [
                {
                    "src": "/static/logo.png",
                    "type": "image/png",
                    "sizes": "500x500",
                    "purpose": "any",
                },
                {
                    "src": "/static/logo.png",
                    "type": "image/png",
                    "sizes": "500x500",
                    "purpose": "maskable",
                },
            ],
            "share_target": {
                "action": "/",
                "method": "GET",
                "params": {"text": "shared"},
            },
        }


@app.get("/opensearch.xml")
async def get_opensearch_xml():
    xml_content = rf"""
    <OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/" xmlns:moz="http://www.mozilla.org/2006/browser/search/">
    <ShortName>{app.state.WEBUI_NAME}</ShortName>
    <Description>Search {app.state.WEBUI_NAME}</Description>
    <InputEncoding>UTF-8</InputEncoding>
    <Image width="16" height="16" type="image/x-icon">{app.state.config.WEBUI_URL}/static/favicon.png</Image>
    <Url type="text/html" method="get" template="{app.state.config.WEBUI_URL}/?q={"{searchTerms}"}"/>
    <moz:SearchForm>{app.state.config.WEBUI_URL}</moz:SearchForm>
    </OpenSearchDescription>
    """
    return Response(content=xml_content, media_type="application/xml")


@app.get("/health")
async def healthcheck():
    return {"status": True}


@app.get("/health/db")
async def healthcheck_with_db():
    Session.execute(text("SELECT 1;")).all()
    return {"status": True}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/favicon.png")
async def get_favicon():
    return FileResponse(os.path.join(STATIC_DIR, "favicon.png"))


@app.get("/cache/{path:path}")
async def serve_cache_file(
    path: str,
    user=Depends(get_verified_user),
):
    file_path = os.path.abspath(os.path.join(CACHE_DIR, path))
    # prevent path traversal
    if not file_path.startswith(os.path.abspath(CACHE_DIR)):
        raise HTTPException(status_code=404, detail="File not found")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


def swagger_ui_html(*args, **kwargs):
    return get_swagger_ui_html(
        *args,
        **kwargs,
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/swagger-ui.css",
        swagger_favicon_url="/static/swagger-ui/favicon.png",
    )


applications.get_swagger_ui_html = swagger_ui_html

if os.path.exists(FRONTEND_BUILD_DIR):
    mimetypes.add_type("text/javascript", ".js")
    app.mount(
        "/",
        SPAStaticFiles(directory=FRONTEND_BUILD_DIR, html=True),
        name="spa-static-files",
    )
else:
    log.warning(
        f"Frontend build directory not found at '{FRONTEND_BUILD_DIR}'. Serving API only."
    )

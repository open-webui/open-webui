from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import os
import sys
import time
from contextlib import asynccontextmanager
from uuid import uuid4

import aiohttp
import anyio.to_thread
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    applications,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response, StreamingResponse
from starlette_compress import CompressMiddleware
from starsessions import (
    SessionAutoloadMiddleware,
)
from starsessions import (
    SessionMiddleware as StarSessionsMiddleware,
)
from starsessions.stores.redis import RedisStore

from open_webui.config import (
    BYPASS_ADMIN_ACCESS_CONTROL,
    CACHE_DIR,
    CORS_ALLOW_ORIGIN,
    DEFAULT_LOCALE,
    ENABLE_ADMIN_ANALYTICS,
    # Admin
    ENABLE_ADMIN_CHAT_ACCESS,
    ENABLE_ADMIN_EXPORT,
    ENABLE_ONEDRIVE_BUSINESS,
    ENABLE_ONEDRIVE_PERSONAL,
    # OpenAI
    ENV,
    FRONTEND_BUILD_DIR,
    GOOGLE_DRIVE_API_KEY,
    GOOGLE_DRIVE_CLIENT_ID,
    IFRAME_CSP,
    OAUTH_PROVIDERS,
    ONEDRIVE_CLIENT_ID_BUSINESS,
    ONEDRIVE_CLIENT_ID_PERSONAL,
    ONEDRIVE_SHAREPOINT_TENANT_ID,
    ONEDRIVE_SHAREPOINT_URL,
    STATIC_DIR,
    THREAD_POOL_SIZE,
    WEBUI_AUTH,
    WEBUI_NAME,
    async_reset_config,
    import_legacy_config_json,
    seed_registered_defaults,
)
from open_webui.constants import ERROR_MESSAGES, TASKS
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    AUDIT_EXCLUDED_PATHS,
    AUDIT_INCLUDED_PATHS,
    AUDIT_LOG_LEVEL,
    BYPASS_MODEL_ACCESS_CONTROL,
    CHANGELOG,
    DEPLOYMENT_ID,
    ENABLE_AUDIT_GET_REQUESTS,
    ENABLE_COMPRESSION_MIDDLEWARE,
    ENABLE_CUSTOM_MODEL_FALLBACK,
    ENABLE_EASTER_EGGS,
    EXTERNAL_PWA_MANIFEST_URL,
    # OAuth Back-Channel Logout
    ENABLE_OAUTH_BACKCHANNEL_LOGOUT,
    ENABLE_OTEL,
    ENABLE_PUBLIC_ACTIVE_USERS_COUNT,
    # SCIM
    ENABLE_SCIM,
    ENABLE_SIGNUP_PASSWORD_CONFIRMATION,
    ENABLE_STAR_SESSIONS_MIDDLEWARE,
    ENABLE_PYODIDE_FILE_PERSISTENCE,
    ENABLE_VERSION_UPDATE_CHECK,
    ENABLE_WEBSOCKET_SUPPORT,
    GLOBAL_LOG_LEVEL,
    INSTANCE_ID,
    LICENSE_KEY,
    LOG_FORMAT,
    MAX_BODY_LOG_SIZE,
    # Redis
    REDIS_KEY_PREFIX,
    REDIS_URL,
    RESET_CONFIG_ON_START,
    SAFE_MODE,
    SCIM_TOKEN,
    VERSION,
    # Admin Account Runtime Creation
    WEBUI_ADMIN_EMAIL,
    WEBUI_ADMIN_NAME,
    WEBUI_ADMIN_PASSWORD,
    WEBUI_AUTH_TRUSTED_EMAIL_HEADER,
    WEBUI_BUILD_HASH,
    WEBUI_SECRET_KEY,
    WEBUI_SESSION_COOKIE_SAME_SITE,
    WEBUI_SESSION_COOKIE_SECURE,
)
from open_webui.events import (
    EVENTS,
    delete_event_webhook,
    get_event_catalog as get_event_catalog_items,
    get_event_webhooks,
    migrate_legacy_webhook_config,
    publish_event,
    upsert_event_webhook,
)
from open_webui.internal.db import engine, get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.channels import Channels
from open_webui.models.chats import ChatForm, Chats
from open_webui.models.config import Config
from open_webui.models.functions import Functions
from open_webui.models.messages import Messages
from open_webui.models.models import Models
from open_webui.models.users import Users
from open_webui.routers import (
    analytics,
    audio,
    auths,
    automations,
    calendar,
    channels,
    chats,
    configs,
    evaluations,
    files,
    folders,
    functions,
    groups,
    images,
    knowledge,
    memories,
    models,
    notes,
    ollama,
    openai,
    pipelines,
    prompts,
    retrieval,
    scim,
    skills,
    tasks,
    terminals,
    tools,
    users,
    utils,
)
from open_webui.routers.retrieval import (
    get_ef,
    get_embedding_function,
    get_reranking_function,
    get_rf,
)
from open_webui.socket.main import (
    MODELS,
    get_event_emitter,
    get_models_in_use,
    get_user_id_from_session_pool,
    periodic_session_pool_cleanup,
    periodic_usage_pool_cleanup,
)
from open_webui.socket.main import (
    app as socket_app,
)
from open_webui.tasks import (
    cleanup_task,
    create_task,
    has_active_tasks,
    list_task_ids_by_item_id,
    list_tasks,
    redis_task_command_listener,
    stop_item_tasks,
    stop_task,
)  # Import from tasks.py
from open_webui.utils import logger
from open_webui.utils.access_control import has_permission
from open_webui.utils.actions import chat_action as chat_action_handler
from open_webui.utils.asgi_middleware import (
    AuthTokenMiddleware,
    CommitSessionMiddleware,
    RedirectMiddleware,
    WebsocketUpgradeGuardMiddleware,
)
from open_webui.utils.audit import AuditLevel, AuditLoggingMiddleware
from open_webui.utils.auth import (
    create_admin_user,
    decode_token,
    get_admin_user,
    get_http_authorization_cred,
    get_license_data,
    get_verified_user,
)
from open_webui.utils.chat import (
    chat_completed as chat_completed_handler,
)
from open_webui.utils.chat import (
    generate_chat_completion as chat_completion_handler,
)
from open_webui.utils.embeddings import generate_embeddings
from open_webui.utils.logger import start_logger
from open_webui.utils.middleware import (
    background_tasks_handler,
    build_chat_response_context,
    process_chat_payload,
    process_chat_response,
)
from open_webui.utils.models import (
    check_model_access,
    get_all_base_models,
    get_all_models,
    get_filtered_models,
)
from open_webui.utils.oauth import (
    OAuthClientInformationFull,
    OAuthClientManager,
    OAuthManager,
    apply_connection_oauth_options,
    decrypt_data,
    encrypt_data,
    get_oauth_client_info_with_dynamic_client_registration,
    get_oauth_client_info_with_static_credentials,
    recover_static_oauth_client_metadata,
    resolve_oauth_client_info,
)
from open_webui.utils.plugin import install_tool_and_function_dependencies
from open_webui.utils.redis import get_redis_client
from open_webui.utils.security_headers import SecurityHeadersMiddleware
from open_webui.utils.session_pool import get_session
from open_webui.utils.tools import set_terminal_servers, set_tool_servers

if SAFE_MODE:
    print('SAFE MODE ENABLED')
    # Functions.deactivate_all_functions() is awaited in lifespan below

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except (HTTPException, StarletteHTTPException) as ex:
            if ex.status_code == 404:
                if path.endswith('.js'):
                    # Return 404 for javascript files
                    raise ex
                else:
                    return await super().get_response('index.html', scope)
            else:
                raise ex


class CORSStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response


if LOG_FORMAT != 'json':
    banner = rf"""
 ██████╗ ██████╗ ███████╗███╗   ██╗    ██╗    ██╗███████╗██████╗ ██╗   ██╗██╗
██╔═══██╗██╔══██╗██╔════╝████╗  ██║    ██║    ██║██╔════╝██╔══██╗██║   ██║██║
██║   ██║██████╔╝█████╗  ██╔██╗ ██║    ██║ █╗ ██║█████╗  ██████╔╝██║   ██║██║
██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║    ██║███╗██║██╔══╝  ██╔══██╗██║   ██║██║
╚██████╔╝██║     ███████╗██║ ╚████║    ╚███╔███╔╝███████╗██████╔╝╚██████╔╝██║
 ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝     ╚══╝╚══╝ ╚══════╝╚═════╝  ╚═════╝ ╚═╝


v{VERSION} - building the best AI user interface.
{f'Commit: {WEBUI_BUILD_HASH}' if WEBUI_BUILD_HASH != 'dev-build' else ''}
https://github.com/open-webui/open-webui
"""
    try:
        print(banner)
    except UnicodeEncodeError:
        # Stdout can't encode the box-drawing banner (Windows cp1252, redirected/headless stdout); fall back to ASCII.
        print(f'Open WebUI v{VERSION} - building the best AI user interface.\nhttps://github.com/open-webui/open-webui')


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Store reference to main event loop for sync->async calls (e.g., embedding generation)
    # This allows sync functions to schedule work on the main loop without blocking health checks
    app.state.main_loop = asyncio.get_running_loop()

    app.state.instance_id = INSTANCE_ID
    start_logger()

    if RESET_CONFIG_ON_START:
        await async_reset_config()

    await import_legacy_config_json()
    await seed_registered_defaults()
    await initialize_runtime_config(app)
    await migrate_legacy_webhook_config()
    await publish_event(app, EVENTS.SYSTEM_STARTUP_STARTED, source='system')

    if LICENSE_KEY:
        get_license_data(app, LICENSE_KEY)

    # Create admin account from env vars if specified and no users exist
    if WEBUI_ADMIN_EMAIL and WEBUI_ADMIN_PASSWORD:
        if await create_admin_user(WEBUI_ADMIN_EMAIL, WEBUI_ADMIN_PASSWORD, WEBUI_ADMIN_NAME):
            # Disable signup since we now have an admin
            await Config.upsert({'ui.enable_signup': False})

    if SAFE_MODE:
        await Functions.deactivate_all_functions()

    # This should be blocking (sync) so functions are not deactivated on first /get_models calls
    # when the first user lands on the / route.
    log.info('Installing external dependencies of functions and tools...')
    await install_tool_and_function_dependencies()

    app.state.redis = get_redis_client(async_mode=True)

    if app.state.redis is not None:
        app.state.redis_task_command_listener = asyncio.create_task(redis_task_command_listener(app))

    if THREAD_POOL_SIZE and THREAD_POOL_SIZE > 0:
        limiter = anyio.to_thread.current_default_thread_limiter()
        limiter.total_tokens = THREAD_POOL_SIZE

    asyncio.create_task(periodic_usage_pool_cleanup())
    asyncio.create_task(periodic_session_pool_cleanup())

    from open_webui.utils.automations import scheduler_worker_loop

    asyncio.create_task(scheduler_worker_loop(app))

    if await Config.get('models.base_models_cache'):
        try:
            await get_all_models(
                Request(
                    # Creating a mock request object to pass to get_all_models
                    {
                        'type': 'http',
                        'asgi.version': '3.0',
                        'asgi.spec_version': '2.0',
                        'method': 'GET',
                        'path': '/internal',
                        'query_string': b'',
                        'headers': Headers({}).raw,
                        'client': ('127.0.0.1', 12345),
                        'server': ('127.0.0.1', 80),
                        'scheme': 'http',
                        'app': app,
                    }
                ),
                None,
            )
        except Exception as e:
            log.warning(f'Failed to pre-fetch models at startup: {e}')

    # Pre-fetch tool server specs so the first request doesn't pay the latency cost
    if len(await Config.get('tool_server.connections', []) or []) > 0:
        mock_request = Request(
            {
                'type': 'http',
                'asgi.version': '3.0',
                'asgi.spec_version': '2.0',
                'method': 'GET',
                'path': '/internal',
                'query_string': b'',
                'headers': Headers({}).raw,
                'client': ('127.0.0.1', 12345),
                'server': ('127.0.0.1', 80),
                'scheme': 'http',
                'app': app,
            }
        )

        log.info('Initializing tool servers...')
        try:
            await set_tool_servers(mock_request)
            log.info(f'Initialized {len(app.state.TOOL_SERVERS)} tool server(s)')
        except Exception as e:
            log.warning(f'Failed to initialize tool servers at startup: {e}')

        try:
            await set_terminal_servers(mock_request)
            log.info(f'Initialized {len(app.state.TERMINAL_SERVERS)} terminal server(s)')
        except Exception as e:
            log.warning(f'Failed to initialize terminal servers at startup: {e}')

    # Mark application as ready to accept traffic from a startup perspective.
    app.state.startup_complete = True
    await publish_event(app, EVENTS.SYSTEM_STARTUP_COMPLETED, source='system')

    yield

    await publish_event(app, EVENTS.SYSTEM_SHUTDOWN_STARTED, source='system')

    # Shutdown: clean up shared resources
    from open_webui.utils.session_pool import close_session

    await close_session()

    if hasattr(app.state, 'redis_task_command_listener'):
        app.state.redis_task_command_listener.cancel()

    await publish_event(app, EVENTS.SYSTEM_SHUTDOWN_COMPLETED, source='system')


app = FastAPI(
    title='Open WebUI',
    docs_url='/docs' if ENV == 'dev' else None,
    openapi_url='/openapi.json' if ENV == 'dev' else None,
    redoc_url=None,
    lifespan=lifespan,
)

# Used by readiness checks to gate traffic until startup work is done.
app.state.startup_complete = False

# For Open WebUI OIDC/OAuth2
oauth_manager = OAuthManager(app)
app.state.oauth_manager = oauth_manager

# For Integrations
oauth_client_manager = OAuthClientManager(app)
app.state.oauth_client_manager = oauth_client_manager

app.state.instance_id = None
app.state.redis = None

app.state.WEBUI_NAME = WEBUI_NAME
app.state.LICENSE_METADATA = None
app.state.USER_COUNT = None
app.state.EXTERNAL_PWA_MANIFEST_URL = EXTERNAL_PWA_MANIFEST_URL


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


app.state.OLLAMA_MODELS = {}

########################################
#
# OPENAI
#
########################################


app.state.OPENAI_MODELS = {}

########################################
#
# TOOL SERVERS
#
########################################

app.state.TOOL_SERVERS = []

########################################
#
# TERMINAL SERVER
#
########################################

app.state.TERMINAL_SERVERS = []

########################################
#
# DIRECT CONNECTIONS
#
########################################


########################################
#
# SCIM
#
########################################

app.state.ENABLE_SCIM = ENABLE_SCIM
app.state.SCIM_TOKEN = SCIM_TOKEN

########################################
#
# MODELS
#
########################################

app.state.BASE_MODELS = []

########################################
#
# WEBUI
#
########################################


async def initialize_runtime_config(app: FastAPI):
    # Migrate legacy access_control → access_grants on boot.
    from open_webui.utils.access_control import migrate_access_control

    connections = await Config.get('tool_server.connections', []) or []
    if any('access_control' in c.get('config', {}) for c in connections):
        for connection in connections:
            migrate_access_control(connection.get('config', {}))
        await Config.upsert({'tool_server.connections': connections})

    for tool_server_connection in connections:
        if tool_server_connection.get('type', 'openapi') == 'mcp':
            server_id = (tool_server_connection.get('info') or {}).get('id')
            auth_type = tool_server_connection.get('auth_type', 'none')

            if server_id and auth_type in ('oauth_2.1', 'oauth_2.1_static'):
                try:
                    oauth_client_info = resolve_oauth_client_info(tool_server_connection)
                    oauth_client_info = await recover_static_oauth_client_metadata(
                        tool_server_connection, oauth_client_info
                    )
                    oauth_client_info = apply_connection_oauth_options(tool_server_connection, oauth_client_info)
                    app.state.oauth_client_manager.add_client(
                        f'mcp:{server_id}',
                        OAuthClientInformationFull(**oauth_client_info),
                    )
                except Exception as e:
                    log.error(f'Error adding OAuth client for MCP tool server {server_id}: {e}')

    arena_models = await Config.get('evaluation.arena.models', []) or []
    if any('access_control' in m.get('meta', {}) for m in arena_models):
        for model in arena_models:
            migrate_access_control(model.get('meta', {}))
        await Config.upsert({'evaluation.arena.models': arena_models})

    app.state.EMBEDDING_FUNCTION = None
    app.state.RERANKING_FUNCTION = None
    app.state.ef = None
    app.state.rf = None
    app.state.YOUTUBE_LOADER_TRANSLATION = None

    try:
        rag_config = await Config.get_many(
            'rag.embedding_engine',
            'rag.embedding_model',
            'rag.enable_hybrid_search',
            'rag.bypass_embedding_and_retrieval',
            'rag.reranking_engine',
            'rag.reranking_model',
            'rag.external_reranker_url',
            'rag.external_reranker_api_key',
            'rag.external_reranker_timeout',
        )
        app.state.ef = get_ef(rag_config.get('rag.embedding_engine'), rag_config.get('rag.embedding_model'))
        if rag_config.get('rag.enable_hybrid_search') and not rag_config.get('rag.bypass_embedding_and_retrieval'):
            app.state.rf = get_rf(
                rag_config.get('rag.reranking_engine'),
                rag_config.get('rag.reranking_model'),
                rag_config.get('rag.external_reranker_url'),
                rag_config.get('rag.external_reranker_api_key'),
                rag_config.get('rag.external_reranker_timeout'),
            )
        else:
            app.state.rf = None
    except Exception as e:
        log.error(f'Error updating models: {e}')
        app.state.rf = None

    rag_config = await Config.get_many(
        'rag.embedding_engine',
        'rag.embedding_model',
        'rag.openai.api_base_url',
        'rag.ollama.base_url',
        'rag.azure_openai.base_url',
        'rag.openai.api_key',
        'rag.ollama.api_key',
        'rag.azure_openai.api_key',
        'rag.embedding_batch_size',
        'rag.azure_openai.api_version',
        'rag.enable_async_embedding',
        'rag.embedding_concurrent_requests',
        'rag.reranking_engine',
        'rag.reranking_model',
        'rag.reranking_batch_size',
    )
    embedding_engine = rag_config.get('rag.embedding_engine')
    app.state.EMBEDDING_FUNCTION = get_embedding_function(
        embedding_engine,
        rag_config.get('rag.embedding_model'),
        embedding_function=app.state.ef,
        url=(
            rag_config.get('rag.openai.api_base_url')
            if embedding_engine == 'openai'
            else (
                rag_config.get('rag.ollama.base_url')
                if embedding_engine == 'ollama'
                else rag_config.get('rag.azure_openai.base_url')
            )
        ),
        key=(
            rag_config.get('rag.openai.api_key')
            if embedding_engine == 'openai'
            else (
                rag_config.get('rag.ollama.api_key')
                if embedding_engine == 'ollama'
                else rag_config.get('rag.azure_openai.api_key')
            )
        ),
        embedding_batch_size=rag_config.get('rag.embedding_batch_size'),
        azure_api_version=(
            rag_config.get('rag.azure_openai.api_version') if embedding_engine == 'azure_openai' else None
        ),
        enable_async=rag_config.get('rag.enable_async_embedding'),
        concurrent_requests=rag_config.get('rag.embedding_concurrent_requests'),
    )

    app.state.RERANKING_FUNCTION = get_reranking_function(
        rag_config.get('rag.reranking_engine'),
        rag_config.get('rag.reranking_model'),
        reranking_function=app.state.rf,
        reranking_batch_size=rag_config.get('rag.reranking_batch_size'),
    )


########################################
#
# CODE EXECUTION
#
########################################


########################################
#
# IMAGES
#
########################################


########################################
#
# AUDIO
#
########################################


app.state.faster_whisper_model = None
app.state.speech_synthesiser = None
app.state.speech_speaker_embeddings_dataset = None


########################################
#
# TASKS
#
########################################


########################################
#
# WEBUI
#
########################################

app.state.MODELS = MODELS

# Add the middleware to the app
if ENABLE_COMPRESSION_MIDDLEWARE:
    app.add_middleware(CompressMiddleware)


# All HTTP middlewares below are pure-ASGI implementations. The previous
# `BaseHTTPMiddleware` / `@app.middleware('http')` versions wrapped the
# downstream app in an anyio task group whose cancel scope cancelled
# in-flight DB calls (and any other awaits) on client disconnect /
# response completion — which surfaced as noisy SQLAlchemy
# `terminate_force_close` tracebacks under aiosqlite and as random
# CancelledError storms across the request path. See
# `open_webui.utils.asgi_middleware` for the rationale.
app.add_middleware(RedirectMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CommitSessionMiddleware)
app.add_middleware(AuthTokenMiddleware, fastapi_app=app)
app.add_middleware(WebsocketUpgradeGuardMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGIN,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


app.mount('/ws', socket_app)


app.include_router(ollama.router, prefix='/ollama', tags=['ollama'])
app.include_router(openai.router, prefix='/openai', tags=['openai'])


app.include_router(pipelines.router, prefix='/api/v1/pipelines', tags=['pipelines'])
app.include_router(tasks.router, prefix='/api/v1/tasks', tags=['tasks'])
app.include_router(images.router, prefix='/api/v1/images', tags=['images'])

app.include_router(audio.router, prefix='/api/v1/audio', tags=['audio'])
app.include_router(retrieval.router, prefix='/api/v1/retrieval', tags=['retrieval'])

app.include_router(configs.router, prefix='/api/v1/configs', tags=['configs'])

app.include_router(auths.router, prefix='/api/v1/auths', tags=['auths'])
app.include_router(users.router, prefix='/api/v1/users', tags=['users'])


app.include_router(channels.router, prefix='/api/v1/channels', tags=['channels'])
app.include_router(chats.router, prefix='/api/v1/chats', tags=['chats'])
app.include_router(notes.router, prefix='/api/v1/notes', tags=['notes'])


app.include_router(models.router, prefix='/api/v1/models', tags=['models'])
app.include_router(knowledge.router, prefix='/api/v1/knowledge', tags=['knowledge'])
app.include_router(prompts.router, prefix='/api/v1/prompts', tags=['prompts'])
app.include_router(tools.router, prefix='/api/v1/tools', tags=['tools'])
app.include_router(skills.router, prefix='/api/v1/skills', tags=['skills'])

app.include_router(memories.router, prefix='/api/v1/memories', tags=['memories'])
app.include_router(folders.router, prefix='/api/v1/folders', tags=['folders'])
app.include_router(groups.router, prefix='/api/v1/groups', tags=['groups'])
app.include_router(files.router, prefix='/api/v1/files', tags=['files'])
app.include_router(functions.router, prefix='/api/v1/functions', tags=['functions'])
app.include_router(evaluations.router, prefix='/api/v1/evaluations', tags=['evaluations'])
if ENABLE_ADMIN_ANALYTICS:
    app.include_router(analytics.router, prefix='/api/v1/analytics', tags=['analytics'])
app.include_router(utils.router, prefix='/api/v1/utils', tags=['utils'])
app.include_router(terminals.router, prefix='/api/v1/terminals', tags=['terminals'])
app.include_router(automations.router, prefix='/api/v1/automations', tags=['automations'])
app.include_router(calendar.router, prefix='/api/v1/calendars', tags=['calendars'])

# SCIM 2.0 API for identity management
if ENABLE_SCIM:
    app.include_router(scim.router, prefix='/api/v1/scim/v2', tags=['scim'])


try:
    audit_level = AuditLevel(AUDIT_LOG_LEVEL)
except ValueError as e:
    logger.error(f'Invalid audit level: {AUDIT_LOG_LEVEL}. Error: {e}')
    audit_level = AuditLevel.NONE

if audit_level != AuditLevel.NONE:
    app.add_middleware(
        AuditLoggingMiddleware,
        audit_level=audit_level,
        excluded_paths=AUDIT_EXCLUDED_PATHS,
        included_paths=AUDIT_INCLUDED_PATHS,
        audit_get_requests=ENABLE_AUDIT_GET_REQUESTS,
        max_body_size=MAX_BODY_LOG_SIZE,
    )
##################################
#
# Chat Endpoints
#
##################################


@app.get('/api/models')
@app.get('/api/v1/models')  # Experimental: Compatibility with OpenAI API
async def get_models(request: Request, refresh: bool = False, user=Depends(get_verified_user)):
    all_models = await get_all_models(request, refresh=refresh, user=user)

    models = []
    for model in all_models:
        # Filter out filter pipelines
        if 'pipeline' in model and model['pipeline'].get('type', None) == 'filter':
            continue

        # Remove profile image URL to reduce payload size
        if model.get('info', {}).get('meta', {}).get('profile_image_url'):
            model['info']['meta'].pop('profile_image_url', None)

        try:
            model_tags = [tag.get('name') for tag in model.get('info', {}).get('meta', {}).get('tags', [])]
            tags = [tag.get('name') for tag in model.get('tags', [])]

            tags = list(set(model_tags + tags))
            model['tags'] = [{'name': tag} for tag in tags]
        except Exception as e:
            log.debug(f'Error processing model tags: {e}')
            model['tags'] = []
            pass

        models.append(model)

    # Chat requests resolve models by ID from request.app.state.MODELS, where
    # duplicate IDs collapse to the last model. Return the same effective list.
    models = list({model['id']: model for model in models}.values())

    model_order_list = await Config.get('ui.model_order_list')
    if model_order_list:
        model_order_dict = {model_id: i for i, model_id in enumerate(model_order_list)}
        # Sort models by order list priority, with fallback for those not in the list
        models.sort(
            key=lambda model: (
                model_order_dict.get(model.get('id', ''), float('inf')),
                (model.get('name', '') or ''),
            )
        )

    models = await get_filtered_models(models, user)

    log.debug(
        f'/api/models returned filtered models accessible to the user: {json.dumps([model.get("id") for model in models])}'
    )
    return {'data': models}


@app.get('/api/models/base')
async def get_base_models(request: Request, user=Depends(get_admin_user)):
    models = await get_all_base_models(request, user=user)
    return {'data': models}


class ModelUnloadForm(BaseModel):
    model: str


def strip_provider_model_prefix(model_id: str, prefix_id: str | None) -> str:
    if prefix_id and model_id.startswith(f'{prefix_id}.'):
        return model_id[len(f'{prefix_id}.') :]
    return model_id


@app.post('/api/models/unload')
async def unload_model(request: Request, form_data: ModelUnloadForm, user=Depends(get_admin_user)):
    """
    Unified model unload endpoint.
    Resolves the provider that owns the model and calls its native unload mechanism.
    Supports: Ollama (keep_alive=0) and llama.cpp (/models/unload).
    """
    model_id = form_data.model

    ollama_models = getattr(request.app.state, 'OLLAMA_MODELS', None) or {}
    openai_models = getattr(request.app.state, 'OPENAI_MODELS', None) or {}

    seen = set()
    while model_id not in ollama_models and model_id not in openai_models and model_id not in seen:
        seen.add(model_id)
        model_info = await Models.get_model_by_id(model_id)
        if not model_info or not model_info.base_model_id:
            break
        model_id = model_info.base_model_id

    # --- Ollama provider ---
    if model_id in ollama_models:
        ollama_config = await Config.get_many('ollama.base_urls', 'ollama.api_configs')
        ollama_base_urls = ollama_config.get('ollama.base_urls') or []
        ollama_api_configs = ollama_config.get('ollama.api_configs') or {}
        url_indices = ollama_models[model_id].get('urls', [])
        errors = []
        for idx in url_indices:
            url = ollama_base_urls[idx]
            api_config = ollama_api_configs.get(
                str(idx),
                ollama_api_configs.get(url, {}),
            )
            key = api_config.get('key', None)

            prefix_id = api_config.get('prefix_id', None)
            actual_model = strip_provider_model_prefix(model_id, prefix_id)

            payload = json.dumps({'model': actual_model, 'keep_alive': 0, 'prompt': ''})

            try:
                timeout = aiohttp.ClientTimeout(total=30)
                async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
                    headers = {
                        'Content-Type': 'application/json',
                        **({'Authorization': f'Bearer {key}'} if key else {}),
                    }
                    async with session.post(
                        f'{url}/api/generate',
                        data=payload,
                        headers=headers,
                    ) as r:
                        if not r.ok:
                            errors.append({'url_idx': idx, 'error': await r.text()})
            except Exception as e:
                log.exception(f'Failed to unload model on Ollama node {idx}: {e}')
                errors.append({'url_idx': idx, 'error': str(e)})

        if errors:
            raise HTTPException(
                status_code=500,
                detail=f'Failed to unload model on {len(errors)} node(s): {errors}',
            )
        return {'status': True}

    # --- OpenAI-compatible providers ---
    if model_id in openai_models:
        openai_config = await Config.get_many('openai.api_configs', 'openai.api_base_urls', 'openai.api_keys')
        openai_api_configs = openai_config.get('openai.api_configs') or {}
        openai_base_urls = openai_config.get('openai.api_base_urls') or []
        openai_api_keys = openai_config.get('openai.api_keys') or []
        model_info = openai_models[model_id]
        idx = model_info.get('urlIdx')
        api_config = openai_api_configs.get(str(idx), {})
        provider = api_config.get('provider', '')
        base_url = openai_base_urls[idx]
        key = openai_api_keys[idx] if idx < len(openai_api_keys) else ''

        if provider == 'llama.cpp':
            root_url = base_url.rstrip('/').removesuffix('/v1')
            actual_model = strip_provider_model_prefix(model_id, api_config.get('prefix_id'))
            try:
                timeout = aiohttp.ClientTimeout(total=30)
                async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
                    headers = {
                        'Content-Type': 'application/json',
                        **({'Authorization': f'Bearer {key}'} if key else {}),
                    }
                    async with session.post(
                        f'{root_url}/models/unload',
                        json={'model': actual_model},
                        headers=headers,
                    ) as r:
                        if not r.ok:
                            detail = await r.text()
                            raise HTTPException(status_code=r.status, detail=detail)
                        return await r.json()
            except HTTPException:
                raise
            except Exception as e:
                log.exception(f'Failed to unload model via llama.cpp: {e}')
                raise HTTPException(status_code=500, detail=str(e))
        else:
            raise HTTPException(
                status_code=400,
                detail=f'Provider "{provider or "default"}" does not support model unloading',
            )

    raise HTTPException(status_code=404, detail=f'Model "{model_id}" not found')


##################################
# Embeddings
##################################


@app.post('/api/embeddings')
@app.post('/api/v1/embeddings')  # Experimental: Compatibility with OpenAI API
async def embeddings(request: Request, form_data: dict, user=Depends(get_verified_user)):
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


@app.post('/api/chat/completions')
@app.post('/api/v1/chat/completions')  # Experimental: Compatibility with OpenAI API
async def chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
):
    if not request.app.state.MODELS:
        await get_all_models(request, user=user)

    model_id = form_data.get('model', None)
    model_item = form_data.pop('model_item', {})
    tasks = form_data.pop('background_tasks', None)

    metadata = {}
    try:
        model_info = None
        if not model_item.get('direct', False):
            if model_id not in request.app.state.MODELS:
                raise Exception('Model not found')

            model = request.app.state.MODELS[model_id]
            model_info = await Models.get_model_by_id(model_id)

            # Check if user has access to the model
            if not BYPASS_MODEL_ACCESS_CONTROL and (user.role != 'admin' or not BYPASS_ADMIN_ACCESS_CONTROL):
                try:
                    await check_model_access(user, model)
                except Exception as e:
                    raise e
        else:
            model = model_item

            request.state.direct = True
            request.state.model = model

        # Model params: global defaults as base, per-model overrides win
        default_model_params = await Config.get('models.default_params', {}) or {}
        model_info_params = {
            **default_model_params,
            **(model_info.params.model_dump() if model_info and model_info.params else {}),
        }
        request_params = {key: value for key, value in (form_data.get('params') or {}).items() if value is not None}
        if model_info_params or request_params:
            form_data['params'] = {
                **model_info_params,
                **request_params,
            }

        # Check base model existence for custom models
        if model_info and model_info.base_model_id:
            base_model_id = model_info.base_model_id
            if base_model_id not in request.app.state.MODELS:
                if ENABLE_CUSTOM_MODEL_FALLBACK:
                    default_models = ((await Config.get('ui.default_models')) or '').split(',')

                    fallback_model_id = default_models[0].strip() if default_models[0] else None

                    if fallback_model_id and fallback_model_id in request.app.state.MODELS:
                        # Update model and form_data so routing uses the fallback model's type
                        model = request.app.state.MODELS[fallback_model_id]
                        form_data['model'] = fallback_model_id
                    else:
                        raise Exception('Model not found')
                else:
                    raise Exception('Model not found')

        # Chat Params
        stream_delta_chunk_size = form_data.get('params', {}).get('stream_delta_chunk_size')
        reasoning_tags = form_data.get('params', {}).get('reasoning_tags')
        compact_token_threshold = form_data.get('params', {}).get('compact_token_threshold')

        # Model Params
        if model_info_params.get('stream_response') is not None:
            form_data['stream'] = model_info_params.get('stream_response')

        if model_info_params.get('stream_delta_chunk_size'):
            stream_delta_chunk_size = model_info_params.get('stream_delta_chunk_size')

        if model_info_params.get('reasoning_tags') is not None:
            reasoning_tags = model_info_params.get('reasoning_tags')

        if model_info_params.get('compact_token_threshold') is not None:
            compact_token_threshold = model_info_params.get('compact_token_threshold')

        # parent_id signals intent:
        #   null   → new chat (root message, no parent)
        #   value  → follow-up (user message's parentId = prev assistant)
        #   absent → legacy caller, no chat management
        is_new_chat = 'parent_id' in form_data and form_data['parent_id'] is None and not form_data.get('chat_id')
        parent_id = form_data.pop('parent_id', None)
        form_data.pop('new_chat', None)  # Legacy field

        # Multi-model message_ids: list of {model_id, message_id} entries.
        # Supports both the new array format and legacy dict format for backward compat.
        message_ids = form_data.pop('message_ids', None)
        if isinstance(message_ids, list):
            # New format: [{"model_id": ..., "message_id": ...}, ...]
            form_data.pop('id', None)
        elif isinstance(message_ids, dict):
            # Legacy dict format: {model_id: message_id} — convert to list
            message_ids = [{'model_id': k, 'message_id': v} for k, v in message_ids.items()]
            form_data.pop('id', None)
        else:
            # Single-model fallback
            message_ids = [{'model_id': model_id, 'message_id': form_data.pop('id', None)}]

        user_message = form_data.pop('user_message', None) or form_data.pop('parent_message', None)

        # Drop tool_servers if caller lacks features.direct_tool_servers —
        # mirrors the storage-side strip in user/settings/update.
        tool_servers = form_data.pop('tool_servers', None)
        if (
            tool_servers
            and user.role != 'admin'
            and not await has_permission(
                user.id,
                'features.direct_tool_servers',
                await Config.get('user.permissions'),
            )
        ):
            tool_servers = None

        metadata = {
            'user_id': user.id,
            'user_agent': request.headers.get('user-agent', '') or '',
            'chat_id': form_data.pop('chat_id', None) or '',
            'user_message': user_message,
            'user_message_id': user_message.get('id') if user_message else None,
            'assistant_message_id': form_data.pop('assistant_message_id', None),
            'session_id': form_data.pop('session_id', None),
            'folder_id': form_data.pop('folder_id', None),
            'filter_ids': form_data.pop('filter_ids', []),
            'tool_ids': form_data.get('tool_ids', None),
            'tool_servers': tool_servers,
            'files': form_data.get('files', None),
            'features': form_data.get('features', {}),
            'variables': form_data.get('variables', {}),
            'model': model,
            'direct': model_item.get('direct', False),
            'params': {
                'stream_delta_chunk_size': stream_delta_chunk_size,
                'reasoning_tags': reasoning_tags,
                'compact_token_threshold': compact_token_threshold,
                'function_calling': (
                    form_data.get('params', {}).get('function_calling')
                    or model_info_params.get('function_calling')
                    or 'native'
                ),
            },
        }

        if is_new_chat:
            metadata['chat_id'] = str(uuid4())

        initial_title_generation = None
        if is_new_chat and tasks and TASKS.TITLE_GENERATION in tasks:
            initial_title_generation = tasks.pop(TASKS.TITLE_GENERATION)

        if metadata.get('chat_id') and user:
            chat_id = metadata['chat_id']

            # Gate channel: branch — caller needs write access on the channel
            # and the supplied message_id must belong to that channel.
            if chat_id.startswith('channel:'):
                channel_id = chat_id.removeprefix('channel:')
                channel = await Channels.get_channel_by_id(channel_id)
                if not channel:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=ERROR_MESSAGES.NOT_FOUND,
                    )
                if user.role != 'admin':
                    if channel.type in ['group', 'dm']:
                        if not await Channels.is_user_channel_member(channel.id, user.id):
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail=ERROR_MESSAGES.DEFAULT(),
                            )
                    else:
                        if not await AccessGrants.has_access(
                            user_id=user.id,
                            resource_type='channel',
                            resource_id=channel.id,
                            permission='write',
                        ):
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail=ERROR_MESSAGES.DEFAULT(),
                            )
                for entry in message_ids:
                    target_message_id = entry.get('message_id')
                    if not target_message_id:
                        continue
                    target_message = await Messages.get_message_by_id(target_message_id)
                    if target_message and target_message.channel_id != channel.id:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=ERROR_MESSAGES.DEFAULT(),
                        )

            if not chat_id.startswith('local:') and not chat_id.startswith(
                'channel:'
            ):  # temporary/channel chats are not stored
                if is_new_chat:
                    # Build the full history upfront with ALL assistant placeholders
                    user_message = metadata.get('user_message') or {}
                    user_message_id = user_message.get('id') if user_message else None

                    history_messages = {}
                    all_assistant_ids = [entry['message_id'] for entry in message_ids if entry.get('message_id')]

                    if user_message_id and user_message:
                        user_message['childrenIds'] = all_assistant_ids
                        history_messages[user_message_id] = user_message

                    for entry in message_ids:
                        target_model_id = entry['model_id']
                        assistant_message_id = entry['message_id']
                        if assistant_message_id:
                            history_messages[assistant_message_id] = {
                                'id': assistant_message_id,
                                'parentId': user_message_id,
                                'childrenIds': [],
                                'role': 'assistant',
                                'content': '',
                                'done': False,
                                'model': target_model_id,
                                'timestamp': int(time.time()),
                            }

                    await Chats.insert_new_chat(
                        chat_id,
                        user.id,
                        ChatForm(
                            chat={
                                'id': chat_id,
                                'title': 'New Chat',
                                'models': [entry['model_id'] for entry in message_ids],
                                'history': {
                                    'currentId': all_assistant_ids[0] if all_assistant_ids else user_message_id,
                                    'messages': history_messages,
                                },
                                'messages': [
                                    {'role': 'user', 'content': user_message.get('content', '')},
                                ]
                                if user_message_id
                                else [],
                                'files': metadata.get('files') or [],
                                'tags': [],
                                'timestamp': int(time.time() * 1000),
                            },
                            folder_id=metadata.get('folder_id'),
                        ),
                    )
                    await publish_event(
                        request,
                        EVENTS.CHAT_CREATED,
                        actor=user,
                        subject_id=chat_id,
                        data={'title': 'New Chat'},
                    )
                    if user_message_id:
                        await publish_event(
                            request,
                            EVENTS.MESSAGE_CREATED,
                            actor=user,
                            subject_id=user_message_id,
                            data={
                                'chat_id': chat_id,
                                'role': 'user',
                                'content_preview': user_message.get('content', '')[:300],
                            },
                        )
                    for entry in message_ids:
                        assistant_message_id = entry.get('message_id')
                        if assistant_message_id:
                            await publish_event(
                                request,
                                EVENTS.MESSAGE_CREATED,
                                actor=user,
                                subject_id=assistant_message_id,
                                data={
                                    'chat_id': chat_id,
                                    'role': 'assistant',
                                    'model': entry.get('model_id'),
                                },
                            )

                    # Insert chat files from user message if any
                    user_message_files = user_message.get('files', [])
                    if user_message_files:
                        try:
                            await Chats.insert_chat_files(
                                chat_id,
                                user_message_id,
                                [
                                    file_item.get('id')
                                    for file_item in user_message_files
                                    if file_item.get('type') == 'file'
                                ],
                                user.id,
                            )
                        except Exception as e:
                            log.debug(f'Error inserting chat files: {e}')
                            pass

                    if initial_title_generation is not None and all_assistant_ids:
                        title_metadata = {
                            **metadata,
                            'message_id': all_assistant_ids[0],
                        }
                        event_emitter = await get_event_emitter(title_metadata, update_db=False)
                        title_ctx = {
                            'request': request,
                            'form_data': form_data,
                            'user': user,
                            'metadata': title_metadata,
                            'tasks': {TASKS.TITLE_GENERATION: initial_title_generation},
                            'event_emitter': event_emitter,
                        }

                        async def run_initial_title_generation():
                            try:
                                await background_tasks_handler(title_ctx)
                            except Exception as e:
                                log.debug(f'Error generating initial chat title: {e}')

                        asyncio.create_task(run_initial_title_generation())
                else:
                    # Existing chat — verify ownership
                    if not await Chats.is_chat_owner(chat_id, user.id) and user.role != 'admin':
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=ERROR_MESSAGES.DEFAULT(),
                        )

                    user_message = metadata.get('user_message') or {}
                    selected_chat_models = user_message.get('models') if isinstance(user_message, dict) else None
                    if not isinstance(selected_chat_models, list) or not selected_chat_models:
                        selected_chat_models = [entry.get('model_id') for entry in message_ids if entry.get('model_id')]

                    # Persist chat-level fields the frontend used to save on every message.
                    # The old frontend saveChatHandler did this on every message;
                    # now the backend owns persistence.
                    chat_files = metadata.get('files')
                    if chat_files is not None or selected_chat_models:
                        existing_chat = await Chats.get_chat_by_id(chat_id)
                        if existing_chat:
                            updated = {**existing_chat.chat}
                            if chat_files is not None:
                                updated['files'] = chat_files
                            if selected_chat_models:
                                updated['models'] = selected_chat_models
                            await Chats.update_chat_by_id(chat_id, updated)

                    # Save user message to DB
                    if user_message and user_message.get('id'):
                        await Chats.upsert_message_to_chat_by_id_and_message_id(
                            chat_id,
                            user_message['id'],
                            user_message,
                        )
                        await publish_event(
                            request,
                            EVENTS.MESSAGE_CREATED,
                            actor=user,
                            subject_id=user_message['id'],
                            data={
                                'chat_id': chat_id,
                                'role': user_message.get('role', 'user'),
                                'content_preview': user_message.get('content', '')[:300],
                            },
                        )

                        # Link grandparent → user message (childrenIds)
                        grandparent_id = user_message.get('parentId')
                        if grandparent_id:
                            grandparent = await Chats.get_message_by_id_and_message_id(chat_id, grandparent_id)
                            if grandparent:
                                child_ids = grandparent.get('childrenIds', [])
                                if user_message['id'] not in child_ids:
                                    child_ids.append(user_message['id'])
                                    await Chats.upsert_message_to_chat_by_id_and_message_id(
                                        chat_id, grandparent_id, {'childrenIds': child_ids}
                                    )

                    # Insert chat files from user message if any
                    user_message_files = user_message.get('files', [])
                    if user_message_files:
                        try:
                            await Chats.insert_chat_files(
                                chat_id,
                                user_message.get('id'),
                                [
                                    file_item.get('id')
                                    for file_item in user_message_files
                                    if file_item.get('type') == 'file'
                                ],
                                user.id,
                            )
                        except Exception as e:
                            log.debug(f'Error inserting chat files: {e}')
                            pass

                    # Save ALL assistant placeholders
                    user_message_id = metadata.get('user_message_id')
                    all_assistant_ids = [entry['message_id'] for entry in message_ids if entry.get('message_id')]

                    # Link user message → all assistant messages (childrenIds)
                    if user_message_id and all_assistant_ids:
                        existing_user_message = await Chats.get_message_by_id_and_message_id(chat_id, user_message_id)
                        if existing_user_message:
                            child_ids = existing_user_message.get('childrenIds', [])
                            for assistant_id in all_assistant_ids:
                                if assistant_id not in child_ids:
                                    child_ids.append(assistant_id)
                            await Chats.upsert_message_to_chat_by_id_and_message_id(
                                chat_id,
                                user_message_id,
                                {'childrenIds': child_ids},
                            )

                    # Save each assistant placeholder
                    for entry in message_ids:
                        target_model_id = entry['model_id']
                        assistant_message_id = entry['message_id']
                        if assistant_message_id:
                            await Chats.upsert_message_to_chat_by_id_and_message_id(
                                chat_id,
                                assistant_message_id,
                                {
                                    'id': assistant_message_id,
                                    'parentId': user_message_id,
                                    'childrenIds': [],
                                    'role': 'assistant',
                                    'content': '',
                                    'done': False,
                                    'model': target_model_id,
                                    'timestamp': int(time.time()),
                                },
                            )
                            await publish_event(
                                request,
                                EVENTS.MESSAGE_CREATED,
                                actor=user,
                                subject_id=assistant_message_id,
                                data={
                                    'chat_id': chat_id,
                                    'role': 'assistant',
                                    'model': target_model_id,
                                },
                            )

        request.state.metadata = metadata
        form_data['metadata'] = metadata

    except HTTPException:
        raise
    except Exception as e:
        log.warning(f'Error processing chat metadata: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    async def process_chat(request, form_data, user, metadata, model, tasks=None):
        try:
            form_data, metadata, events = await process_chat_payload(request, form_data, user, metadata, model)

            response = await chat_completion_handler(request, form_data, user)

            # When the upstream provider returns an error (e.g. HTTP 400
            # content-filter, quota exceeded), generate_chat_completion
            # returns a JSONResponse instead of raising.  Detect this and
            # raise so the except-block below emits chat:message:error +
            # chat:tasks:cancel, unblocking the frontend.
            if isinstance(response, JSONResponse) and response.status_code >= 400:
                try:
                    error_body = json.loads(response.body.decode('utf-8', 'replace'))
                    detail = error_body.get('error', error_body) if isinstance(error_body, dict) else error_body
                    if isinstance(detail, dict):
                        detail = detail.get('message', detail.get('detail', str(detail)))
                except Exception:
                    detail = f'Provider returned HTTP {response.status_code}'
                raise Exception(detail)

            ctx = await build_chat_response_context(request, form_data, user, model, metadata, tasks, events)

            return await process_chat_response(response, ctx)
        except asyncio.CancelledError:
            log.info('Chat processing was cancelled')
            try:

                async def emit_cancel_event():
                    event_emitter = await get_event_emitter(metadata)
                    if event_emitter:
                        await event_emitter({'type': 'chat:tasks:cancel'})

                await asyncio.shield(emit_cancel_event())
            except Exception:
                pass
            raise  # re-raise to ensure proper task cancellation handling
        except Exception as e:
            error_detail = e.detail if isinstance(e, HTTPException) else str(e)
            log.error('Error processing chat payload: %s', error_detail)
            if metadata.get('chat_id') and metadata.get('message_id'):
                # Update the chat message with the error
                try:
                    if not metadata.get('chat_id', '').startswith('local:') and not metadata.get(
                        'chat_id', ''
                    ).startswith('channel:'):
                        await Chats.upsert_message_to_chat_by_id_and_message_id(
                            metadata['chat_id'],
                            metadata['message_id'],
                            {
                                'parentId': metadata.get('user_message_id', None),
                                'error': {'content': error_detail},
                            },
                        )

                    event_emitter = await get_event_emitter(metadata)
                    if event_emitter:
                        await event_emitter(
                            {
                                'type': 'chat:message:error',
                                'data': {'error': {'content': error_detail}},
                            }
                        )
                        await event_emitter(
                            {'type': 'chat:tasks:cancel'},
                        )

                except Exception:
                    pass
            else:
                # No chat_id/message_id → legacy/direct API path with no
                # WebSocket error channel.  We must surface the error as
                # a proper HTTP response; without this the function would
                # return None which FastAPI serializes as null.  #23924
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_detail,
                )
        finally:
            # Clean up MCP clients.  Each client is isolated so one
            # failure doesn't skip the rest.
            #
            # NOTE: asyncio.wait_for() / asyncio.shield() must NOT be used
            # here — they create new asyncio Tasks, which violate anyio
            # cancel-scope task-ownership rules when the MCPClient's
            # exit_stack contains anyio transport resources (streamable_http).
            # Exiting those cancel scopes from the wrong task raises
            # "Attempted to exit a cancel scope that isn't the current
            # task's current cancel scope", which propagates as a
            # BaseException through the finally block, discards the response
            # return value, and surfaces as a 500 "No response returned."
            # MCPClient.disconnect() suppresses known transport teardown errors
            # while still propagating real task cancellation.
            try:
                if mcp_clients := metadata.get('mcp_clients'):
                    for client in reversed(list(mcp_clients.values())):
                        try:
                            await client.disconnect()
                        except BaseException as e:
                            log.debug(f'Error disconnecting MCP client: {e}')
            except BaseException as e:
                log.debug(f'Error cleaning up MCP clients: {e}')

            # Deregister this task, then emit chat:active=false if no others remain
            try:
                chat_id = metadata.get('chat_id')
                task_id = metadata.get('task_id')
                if chat_id and task_id:
                    await cleanup_task(request.app.state.redis, task_id, chat_id)
                    if not await has_active_tasks(request.app.state.redis, chat_id):
                        event_emitter = await get_event_emitter(metadata, update_db=False)
                        if event_emitter:
                            try:
                                await asyncio.shield(event_emitter({'type': 'chat:active', 'data': {'active': False}}))
                            except asyncio.CancelledError:
                                pass
            except Exception:
                pass

    # Fan out: one task per model
    if metadata.get('session_id') and metadata.get('chat_id'):
        task_ids = []
        chat_id = metadata['chat_id']

        for idx, entry in enumerate(message_ids):
            target_model_id = entry['model_id']
            assistant_message_id = entry['message_id']
            if not assistant_message_id:
                continue

            # Per-model metadata: own message_id + model
            per_model_metadata = {
                **metadata,
                'message_id': assistant_message_id,
            }

            # Per-model form_data: own model
            model_form_data = {
                **form_data,
                'model': target_model_id,
                'metadata': per_model_metadata,
            }

            # Resolve the model object for this specific model
            resolved_model = request.app.state.MODELS.get(target_model_id, model)

            # Only the first model runs chat-level background tasks;
            # subsequent models only run follow-ups.
            task_id, _ = await create_task(
                request.app.state.redis,
                process_chat(
                    request,
                    model_form_data,
                    user,
                    per_model_metadata,
                    resolved_model,
                    tasks
                    if idx == 0
                    else {
                        k: v
                        for k, v in (tasks or {}).items()
                        if k not in (TASKS.TITLE_GENERATION, TASKS.TAGS_GENERATION)
                    }
                    or None,
                ),
                id=chat_id,
            )
            per_model_metadata['task_id'] = task_id
            task_ids.append(task_id)

        # Emit chat:active=true
        if task_ids:
            event_emitter = await get_event_emitter(
                {**metadata, 'message_id': message_ids[0]['message_id']},
                update_db=False,
            )
            if event_emitter:
                await event_emitter({'type': 'chat:active', 'data': {'active': True}})

        return {
            'status': True,
            'task_ids': task_ids,
            'chat_id': chat_id,
        }
    else:
        # Legacy/direct: single model, synchronous
        metadata['message_id'] = message_ids[0]['message_id']
        return await process_chat(request, form_data, user, metadata, model, tasks)


# Alias for chat_completion (Legacy)
generate_chat_completions = chat_completion
generate_chat_completion = chat_completion

# Expose as app.state so internal callers (e.g. automations) can
# use the full pipeline without importing from main.py (avoids circular deps).
app.state.CHAT_COMPLETION_HANDLER = chat_completion


##################################
#
# Anthropic Messages API Compatible Endpoint
#
##################################


from open_webui.utils.anthropic import (
    convert_anthropic_to_openai_payload,
    convert_openai_to_anthropic_response,
    openai_stream_to_anthropic_stream,
)


@app.post('/api/message')
@app.post('/api/v1/messages')  # Anthropic Messages API compatible endpoint
async def generate_messages(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
):
    """
    Anthropic Messages API compatible endpoint.

    Accepts the Anthropic Messages API format, converts internally to OpenAI
    Chat Completions format, routes through the existing chat completion
    pipeline, then converts the response back to Anthropic Messages format.

    Supports both streaming and non-streaming requests.
    All models configured in Open WebUI are accessible via this endpoint.

    Authentication: Supports both standard Authorization header and
    Anthropic's x-api-key header (via middleware translation).
    """
    # Convert Anthropic payload to OpenAI format
    requested_model = form_data.get('model', '')

    openai_payload = convert_anthropic_to_openai_payload(form_data)

    # Route through the existing chat_completion handler
    response = await chat_completion(request, openai_payload, user)

    # Convert response back to Anthropic format
    if isinstance(response, StreamingResponse):
        # Streaming response: wrap the generator to convert SSE format
        return StreamingResponse(
            openai_stream_to_anthropic_stream(response.body_iterator, model=requested_model),
            media_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            },
        )
    elif isinstance(response, dict):
        return convert_openai_to_anthropic_response(response, model=requested_model)
    else:
        # Passthrough for error responses (JSONResponse, PlainTextResponse, etc.)
        return response


@app.post('/api/chat/completed')
async def chat_completed(request: Request, form_data: dict, user=Depends(get_verified_user)):
    """Deprecated: outlet filters now run inline during chat completion.
    Kept for backward compatibility with external integrations."""
    try:
        model_item = form_data.pop('model_item', {})

        if model_item.get('direct', False):
            request.state.direct = True
            request.state.model = model_item

        return await chat_completed_handler(request, form_data, user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@app.post('/api/chat/actions/{action_id}')
async def chat_action(request: Request, action_id: str, form_data: dict, user=Depends(get_verified_user)):
    try:
        model_item = form_data.pop('model_item', {})

        if model_item.get('direct', False):
            request.state.direct = True
            request.state.model = model_item

        return await chat_action_handler(request, action_id, form_data, user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@app.post('/api/tasks/stop/{task_id}')
async def stop_task_endpoint(request: Request, task_id: str, user=Depends(get_admin_user)):
    try:
        result = await stop_task(request.app.state.redis, task_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@app.get('/api/tasks')
async def list_tasks_endpoint(request: Request, user=Depends(get_admin_user)):
    return {'tasks': await list_tasks(request.app.state.redis)}


@app.get('/api/tasks/chat/{chat_id:path}')
async def list_tasks_by_chat_id_endpoint(request: Request, chat_id: str, user=Depends(get_verified_user)):
    if chat_id.startswith('local:') or chat_id.startswith('channel:'):
        socket_id = chat_id[len('local:') :]
        owner_id = get_user_id_from_session_pool(socket_id)
        if owner_id != user.id and user.role != 'admin':
            return {'task_ids': []}
    else:
        chat = await Chats.get_chat_by_id(chat_id)
        if chat is None or (chat.user_id != user.id and user.role != 'admin'):
            return {'task_ids': []}

    task_ids = await list_task_ids_by_item_id(request.app.state.redis, chat_id)

    log.debug(f'Task IDs for chat {chat_id}: {task_ids}')
    return {'task_ids': task_ids}


@app.post('/api/tasks/chat/{chat_id:path}/stop')
async def stop_tasks_by_chat_id_endpoint(request: Request, chat_id: str, user=Depends(get_verified_user)):
    if chat_id.startswith('local:') or chat_id.startswith('channel:'):
        socket_id = chat_id[len('local:') :]
        owner_id = get_user_id_from_session_pool(socket_id)
        if owner_id != user.id and user.role != 'admin':
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    else:
        chat = await Chats.get_chat_by_id(chat_id)
        if chat is None or (chat.user_id != user.id and user.role != 'admin'):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    result = await stop_item_tasks(request.app.state.redis, chat_id)
    return result


##################################
#
# Config Endpoints
#
##################################


@app.get('/api/config')
async def get_app_config(request: Request):
    user = None
    token = None

    auth_header = request.headers.get('Authorization')
    if auth_header:
        cred = get_http_authorization_cred(auth_header)
        if cred:
            token = cred.credentials

    if not token and 'token' in request.cookies:
        token = request.cookies.get('token')

    if token:
        try:
            data = decode_token(token)
        except Exception as e:
            log.debug(e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid token',
            )
        if data is not None and 'id' in data:
            user = await Users.get_user_by_id(data['id'])

    onboarding = False
    if user is None:
        onboarding = not await Users.has_users()

    license_metadata = getattr(app.state, 'LICENSE_METADATA', None)
    user_count = await Users.get_num_users() if license_metadata else None
    config = await Config.get_many(
        'oauth.auto_redirect',
        'ldap.enable',
        'ui.enable_signup',
        'ui.enable_login_form',
        'auth.enable_api_keys',
        'ui.enable_password_change_form',
        'direct.enable',
        'folders.enable',
        'folders.max_file_count',
        'channels.enable',
        'calendar.enable',
        'automations.enable',
        'notes.enable',
        'web.search.enable',
        'web.search.confirmation.enable',
        'web.search.confirmation.content',
        'code_execution.enable',
        'code_interpreter.enable',
        'image_generation.enable',
        'task.autocomplete.enable',
        'ui.enable_community_sharing',
        'ui.enable_message_rating',
        'ui.enable_user_webhooks',
        'users.enable_status',
        'google_drive.enable',
        'onedrive.enable',
        'memories.enable',
        'ui.default_models',
        'ui.default_pinned_models',
        'ui.prompt_suggestions',
        'code_execution.engine',
        'code_interpreter.engine',
        'audio.tts.engine',
        'audio.tts.voice',
        'audio.tts.split_on',
        'audio.stt.engine',
        'rag.file.max_size',
        'rag.file.max_count',
        'file.image_compression_width',
        'file.image_compression_height',
        'user.permissions',
        'ui.pending_user_overlay_title',
        'ui.pending_user_overlay_content',
        'ui.watermark',
    )

    return {
        **({'onboarding': True} if onboarding else {}),
        'status': True,
        'name': app.state.WEBUI_NAME,
        'version': VERSION,
        'default_locale': str(DEFAULT_LOCALE),
        'oauth': {
            'providers': {name: config.get('name', name) for name, config in OAUTH_PROVIDERS.items()},
            'auto_redirect': config.get('oauth.auto_redirect'),
        },
        'features': {
            # --- Public: required by login/signup page pre-auth ---
            'auth': WEBUI_AUTH,
            'auth_trusted_header': bool(WEBUI_AUTH_TRUSTED_EMAIL_HEADER),
            'enable_signup_password_confirmation': ENABLE_SIGNUP_PASSWORD_CONFIRMATION,
            'enable_ldap': config.get('ldap.enable'),
            'enable_signup': config.get('ui.enable_signup'),
            'enable_login_form': config.get('ui.enable_login_form'),
            'enable_websocket': ENABLE_WEBSOCKET_SUPPORT,
            # --- Authenticated: only consumed by logged-in frontend ---
            **(
                {
                    'enable_api_keys': config.get('auth.enable_api_keys'),
                    'enable_password_change_form': config.get('ui.enable_password_change_form'),
                    'enable_version_update_check': ENABLE_VERSION_UPDATE_CHECK,
                    'enable_pyodide_file_persistence': ENABLE_PYODIDE_FILE_PERSISTENCE,
                    'enable_public_active_users_count': ENABLE_PUBLIC_ACTIVE_USERS_COUNT,
                    'enable_easter_eggs': ENABLE_EASTER_EGGS,
                    'enable_direct_connections': config.get('direct.enable'),
                    'enable_folders': config.get('folders.enable'),
                    'folder_max_file_count': config.get('folders.max_file_count'),
                    'enable_channels': config.get('channels.enable'),
                    'enable_calendar': config.get('calendar.enable'),
                    'enable_automations': config.get('automations.enable'),
                    'enable_notes': config.get('notes.enable'),
                    'enable_web_search': config.get('web.search.enable'),
                    'enable_web_search_confirmation': config.get('web.search.confirmation.enable'),
                    'web_search_confirmation_content': config.get('web.search.confirmation.content'),
                    'enable_code_execution': config.get('code_execution.enable'),
                    'enable_code_interpreter': config.get('code_interpreter.enable'),
                    'enable_image_generation': config.get('image_generation.enable'),
                    'enable_autocomplete_generation': config.get('task.autocomplete.enable'),
                    'enable_community_sharing': config.get('ui.enable_community_sharing'),
                    'enable_message_rating': config.get('ui.enable_message_rating'),
                    'enable_user_webhooks': config.get('ui.enable_user_webhooks'),
                    'enable_user_status': config.get('users.enable_status'),
                    'enable_admin_export': ENABLE_ADMIN_EXPORT,
                    'enable_admin_chat_access': ENABLE_ADMIN_CHAT_ACCESS,
                    'enable_admin_analytics': ENABLE_ADMIN_ANALYTICS,
                    'enable_google_drive_integration': config.get('google_drive.enable'),
                    'enable_onedrive_integration': config.get('onedrive.enable'),
                    'enable_memories': config.get('memories.enable'),
                    **(
                        {
                            'enable_onedrive_personal': ENABLE_ONEDRIVE_PERSONAL,
                            'enable_onedrive_business': ENABLE_ONEDRIVE_BUSINESS,
                        }
                        if config.get('onedrive.enable')
                        else {}
                    ),
                }
                if user is not None
                else {}
            ),
        },
        **(
            {
                'default_models': config.get('ui.default_models'),
                'default_pinned_models': config.get('ui.default_pinned_models'),
                'default_prompt_suggestions': config.get('ui.prompt_suggestions'),
                **({'user_count': user_count} if user_count is not None else {}),
                'code': {
                    'engine': config.get('code_execution.engine'),
                    'interpreter_engine': config.get('code_interpreter.engine'),
                },
                'audio': {
                    'tts': {
                        'engine': config.get('audio.tts.engine'),
                        'voice': config.get('audio.tts.voice'),
                        'split_on': config.get('audio.tts.split_on'),
                    },
                    'stt': {
                        'engine': config.get('audio.stt.engine'),
                    },
                },
                'file': {
                    'max_size': config.get('rag.file.max_size'),
                    'max_count': config.get('rag.file.max_count'),
                    'image_compression': {
                        'width': config.get('file.image_compression_width'),
                        'height': config.get('file.image_compression_height'),
                    },
                },
                'permissions': {**(config.get('user.permissions') or {})},
                'google_drive': {
                    'client_id': GOOGLE_DRIVE_CLIENT_ID,
                    'api_key': GOOGLE_DRIVE_API_KEY,
                },
                'onedrive': {
                    'client_id_personal': ONEDRIVE_CLIENT_ID_PERSONAL,
                    'client_id_business': ONEDRIVE_CLIENT_ID_BUSINESS,
                    'sharepoint_url': ONEDRIVE_SHAREPOINT_URL,
                    'sharepoint_tenant_id': ONEDRIVE_SHAREPOINT_TENANT_ID,
                },
                'ui': {
                    'pending_user_overlay_title': config.get('ui.pending_user_overlay_title'),
                    'pending_user_overlay_content': config.get('ui.pending_user_overlay_content'),
                    'response_watermark': config.get('ui.watermark'),
                    'iframe_csp': IFRAME_CSP,
                },
                'license_metadata': license_metadata,
                **(
                    {
                        'active_entries': user_count,
                    }
                    if user.role == 'admin' and user_count is not None
                    else {}
                ),
            }
            if user is not None and (user.role in ['admin', 'user'])
            else {
                **(
                    {
                        'ui': {
                            'pending_user_overlay_title': config.get('ui.pending_user_overlay_title'),
                            'pending_user_overlay_content': config.get('ui.pending_user_overlay_content'),
                        }
                    }
                    if user and user.role == 'pending'
                    else {}
                ),
                **(
                    {
                        'metadata': {
                            'login_footer': license_metadata.get('login_footer', ''),
                            'auth_logo_position': license_metadata.get('auth_logo_position', ''),
                        }
                    }
                    if license_metadata
                    else {}
                ),
            }
        ),
    }


class EventWebhookForm(BaseModel):
    name: str | None = None
    url: str
    enabled: bool = True
    events: list[str] | None = None
    targets: list[dict[str, str]] | None = None


class EventWebhookUpdateForm(BaseModel):
    name: str | None = None
    url: str | None = None
    enabled: bool | None = None
    events: list[str] | None = None
    targets: list[dict[str, str]] | None = None


@app.get('/api/events')
async def get_event_catalog(user=Depends(get_admin_user)):
    return {
        'schema': VERSION,
        'events': get_event_catalog_items(),
    }


@app.get('/api/events/webhooks')
async def get_event_webhooks_api(user=Depends(get_admin_user)):
    return await get_event_webhooks()


@app.post('/api/events/webhooks')
async def create_event_webhook(form_data: EventWebhookForm, user=Depends(get_admin_user)):
    try:
        webhook = await upsert_event_webhook(
            {
                'name': form_data.name,
                'url': form_data.url,
                'enabled': form_data.enabled,
                'events': form_data.events,
                'targets': form_data.targets,
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    await publish_event(
        app,
        EVENTS.CONFIG_WEBHOOK_UPDATED,
        actor=user,
        subject_id=webhook['id'],
        subject_type='config',
        data={
            'action': 'created',
            'enabled': webhook.get('enabled'),
            'events': webhook.get('events'),
            'targets': webhook.get('targets'),
        },
    )
    return webhook


@app.put('/api/events/webhooks/{webhook_id}')
async def update_event_webhook(webhook_id: str, form_data: EventWebhookUpdateForm, user=Depends(get_admin_user)):
    webhooks = await get_event_webhooks()
    existing = next((webhook for webhook in webhooks if webhook.get('id') == webhook_id), None)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Webhook not found')

    try:
        webhook = await upsert_event_webhook(
            {
                **existing,
                **form_data.model_dump(exclude_unset=True),
                'id': webhook_id,
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    await publish_event(
        app,
        EVENTS.CONFIG_WEBHOOK_UPDATED,
        actor=user,
        subject_id=webhook_id,
        subject_type='config',
        data={
            'action': 'updated',
            'enabled': webhook.get('enabled'),
            'events': webhook.get('events'),
            'targets': webhook.get('targets'),
        },
    )
    return webhook


@app.delete('/api/events/webhooks/{webhook_id}')
async def delete_event_webhook_api(webhook_id: str, user=Depends(get_admin_user)):
    deleted = await delete_event_webhook(webhook_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Webhook not found')

    await publish_event(
        app,
        EVENTS.CONFIG_WEBHOOK_UPDATED,
        actor=user,
        subject_id=webhook_id,
        subject_type='config',
        data={'action': 'deleted'},
    )
    return {'status': True}


@app.get('/api/version')
async def get_app_version():
    return {
        'version': VERSION,
        'deployment_id': DEPLOYMENT_ID,
    }


@app.get('/api/version/updates')
async def get_app_latest_release_version(user=Depends(get_verified_user)):
    if not ENABLE_VERSION_UPDATE_CHECK:
        log.debug(f'Version update check is disabled, returning current version as latest version')
        return {'current': VERSION, 'latest': VERSION}
    try:
        timeout = aiohttp.ClientTimeout(total=1)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(
                'https://api.github.com/repos/open-webui/open-webui/releases/latest',
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                response.raise_for_status()
                data = await response.json()
                latest_version = data['tag_name']

                return {'current': VERSION, 'latest': latest_version[1:]}
    except Exception as e:
        log.debug(e)
        return {'current': VERSION, 'latest': VERSION}


@app.get('/api/changelog')
async def get_app_changelog():
    return {key: CHANGELOG[key] for idx, key in enumerate(CHANGELOG) if idx < 5}


@app.get('/api/usage')
async def get_current_usage(user=Depends(get_verified_user)):
    """
    Get current usage statistics for Open WebUI.
    This is an experimental endpoint and subject to change.
    """
    try:
        # If public visibility is disabled, only allow admins to access this endpoint
        if not ENABLE_PUBLIC_ACTIVE_USERS_COUNT and user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Access denied. Only administrators can view usage statistics.',
            )

        return {
            'model_ids': get_models_in_use(),
            'user_count': await Users.get_active_user_count(),
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f'Error getting usage statistics: {e}')
        raise HTTPException(status_code=500, detail='Internal Server Error')


# --- OAuth Login & Callback ---


try:
    if ENABLE_STAR_SESSIONS_MIDDLEWARE:
        redis_session_store = RedisStore(
            url=REDIS_URL,
            prefix=(f'{REDIS_KEY_PREFIX}:session:' if REDIS_KEY_PREFIX else 'session:'),
        )

        app.add_middleware(SessionAutoloadMiddleware)
        app.add_middleware(
            StarSessionsMiddleware,
            store=redis_session_store,
            cookie_name='owui-session',
            cookie_same_site=WEBUI_SESSION_COOKIE_SAME_SITE,
            cookie_https_only=WEBUI_SESSION_COOKIE_SECURE,
        )
        log.info('Using Redis for session')
    else:
        raise ValueError('No Redis URL provided')
except Exception as e:
    app.add_middleware(
        SessionMiddleware,
        secret_key=WEBUI_SECRET_KEY,
        session_cookie='owui-session',
        same_site=WEBUI_SESSION_COOKIE_SAME_SITE,
        https_only=WEBUI_SESSION_COOKIE_SECURE,
    )


async def register_client(request, client_id: str) -> bool:
    server_type, server_id = client_id.split(':', 1)

    connection = None
    connection_idx = None

    tool_server_connections = await Config.get('tool_server.connections', []) or []
    for idx, conn in enumerate(tool_server_connections):
        if conn.get('type', 'openapi') == server_type:
            info = conn.get('info') or {}
            if info.get('id') == server_id:
                connection = conn
                connection_idx = idx
                break

    if connection is None or connection_idx is None:
        log.warning(f'Unable to locate MCP tool server configuration for client {client_id} during re-registration')
        return False

    server_url = connection.get('url')
    auth_type = connection.get('auth_type', 'none')
    oauth_scope = (connection.get('info') or {}).get('oauth_scope') or (connection.get('config') or {}).get(
        'oauth_scope'
    )
    oauth_server_key = (connection.get('config') or {}).get('oauth_server_key')

    try:
        if auth_type == 'oauth_2.1_static':
            # Static credentials: rebuild from admin-provided credentials + fresh metadata
            info = connection.get('info') or {}
            oauth_client_id = info.get('oauth_client_id') or ''
            oauth_client_secret = info.get('oauth_client_secret') or ''
            if not oauth_client_id or not oauth_client_secret:
                # Fall back to blob for backward compatibility
                existing_client_info = info.get('oauth_client_info', '')
                if not existing_client_info:
                    log.error(f'No stored OAuth client info for static client {client_id}')
                    return False
                existing_data = decrypt_data(existing_client_info)
                oauth_client_id = oauth_client_id or existing_data.get('client_id', '')
                oauth_client_secret = oauth_client_secret or existing_data.get('client_secret', '')
            oauth_client_info = await get_oauth_client_info_with_static_credentials(
                request,
                client_id,
                server_url,
                oauth_client_id=oauth_client_id,
                oauth_client_secret=oauth_client_secret,
                oauth_scope=oauth_scope,
            )
        else:
            oauth_client_info = await get_oauth_client_info_with_dynamic_client_registration(
                request,
                client_id,
                server_url,
                oauth_server_key,
                oauth_scope=oauth_scope,
            )
    except Exception as e:
        log.error(f'OAuth client re-registration failed for {client_id}: {e}')
        return False

    try:
        connections = await Config.get('tool_server.connections', []) or []
        connections[connection_idx] = {
            **connection,
            'info': {
                **(connection.get('info') or {}),
                'oauth_client_info': encrypt_data(oauth_client_info.model_dump(mode='json')),
            },
        }
        await Config.upsert({'tool_server.connections': connections})
    except Exception as e:
        log.error(f'Failed to persist updated OAuth client info for tool server {client_id}: {e}')
        return False

    oauth_client_manager.remove_client(client_id)
    oauth_client_info = OAuthClientInformationFull(
        **apply_connection_oauth_options(connection, oauth_client_info.model_dump(mode='json'))
    )
    oauth_client_manager.add_client(client_id, oauth_client_info)
    log.info(f'Re-registered OAuth client {client_id} for tool server')
    return True


@app.get('/oauth/clients/{client_id}/authorize')
async def oauth_client_authorize(
    client_id: str,
    request: Request,
    response: Response,
    user=Depends(get_verified_user),
):
    # ensure_valid_client_registration
    client = await oauth_client_manager.get_client(client_id)
    client_info = await oauth_client_manager.get_client_info(client_id)
    if client is None or client_info is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    if not await oauth_client_manager._preflight_authorization_url(client, client_info):
        log.info(
            'Detected invalid OAuth client %s; attempting re-registration',
            client_id,
        )

        registered = await register_client(request, client_id)
        if not registered:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Failed to re-register OAuth client',
            )

        client = await oauth_client_manager.get_client(client_id)
        client_info = await oauth_client_manager.get_client_info(client_id)
        if client is None or client_info is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='OAuth client unavailable after re-registration',
            )

        if not await oauth_client_manager._preflight_authorization_url(client, client_info):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='OAuth client registration is still invalid after re-registration',
            )

    return await oauth_client_manager.handle_authorize(request, client_id=client_id)


@app.get('/oauth/clients/{client_id}/callback')
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


@app.get('/oauth/{provider}/login')
async def oauth_login(provider: str, request: Request):
    return await oauth_manager.handle_login(request, provider)


@app.get('/oauth/{provider}/login/callback')
@app.get('/oauth/{provider}/callback')  # Legacy endpoint
async def oauth_login_callback(
    provider: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_session),
):
    """Handle the OAuth provider callback.

    Resolution order:
    1. Match by subject ID bound to the provider.
    2. If ``OAUTH_MERGE_ACCOUNTS_BY_EMAIL`` is enabled, match by email
       (note: some providers do not verify email addresses).
    3. If no match and ``ENABLE_OAUTH_SIGNUP`` is enabled, create a new user
       (fails if the email is already registered).
    """
    return await oauth_manager.handle_callback(request, provider, response, db=db)


############################
# OIDC Back-Channel Logout
############################


@app.post('/oauth/backchannel-logout')
async def oauth_backchannel_logout(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    if not ENABLE_OAUTH_BACKCHANNEL_LOGOUT:
        raise HTTPException(status_code=404)
    return await oauth_manager.handle_backchannel_logout(request, db=db)


@app.get('/manifest.json')
async def get_manifest_json():
    external_pwa_manifest_url = getattr(app.state, 'EXTERNAL_PWA_MANIFEST_URL', None)
    if external_pwa_manifest_url:
        session = await get_session()
        async with session.get(
            external_pwa_manifest_url,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as r:
            r.raise_for_status()
            return await r.json()
    else:
        return {
            'name': app.state.WEBUI_NAME,
            'short_name': app.state.WEBUI_NAME,
            'description': f'{app.state.WEBUI_NAME} is an open, extensible, user-friendly interface for AI that adapts to your workflow.',
            'start_url': '/',
            'display': 'standalone',
            'background_color': '#343541',
            'icons': [
                {
                    'src': '/static/logo.png',
                    'type': 'image/png',
                    'sizes': '500x500',
                    'purpose': 'any',
                },
                {
                    'src': '/static/logo.png',
                    'type': 'image/png',
                    'sizes': '500x500',
                    'purpose': 'maskable',
                },
            ],
            'share_target': {
                'action': '/',
                'method': 'GET',
                'params': {'text': 'shared'},
            },
        }


@app.get('/opensearch.xml')
async def get_opensearch_xml():
    webui_url = await Config.get('webui.url')
    xml_content = rf"""
    <OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/" xmlns:moz="http://www.mozilla.org/2006/browser/search/">
    <ShortName>{app.state.WEBUI_NAME}</ShortName>
    <Description>Search {app.state.WEBUI_NAME}</Description>
    <InputEncoding>UTF-8</InputEncoding>
    <Image width="16" height="16" type="image/x-icon">{webui_url}/static/favicon.png</Image>
    <Url type="text/html" method="get" template="{webui_url}/?q={'{searchTerms}'}"/>
    <moz:SearchForm>{webui_url}</moz:SearchForm>
    </OpenSearchDescription>
    """
    return Response(content=xml_content, media_type='application/xml')


def _sync_db_ping() -> None:
    """Verify the database is reachable with a simple SELECT 1.

    Uses a raw connection from the engine pool instead of the thread-local
    ScopedSession.  This is necessary because CommitSessionMiddleware
    deliberately skips healthcheck paths (/health, /ready, /health/db),
    so any ScopedSession opened on a healthcheck worker thread is never
    rolled back or removed.  If the session ever enters an invalid state
    (e.g. after a transient connection error), it stays broken on that
    thread permanently, causing PendingRollbackError on every subsequent
    probe — exactly the failure reported in #24605.

    A raw ``engine.connect()`` context manager obtains a fresh connection
    from the pool, executes the ping, and deterministically returns the
    connection regardless of success or failure.
    """
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))


async def async_db_ping() -> None:
    await asyncio.to_thread(_sync_db_ping)


@app.get('/health')
async def healthcheck():
    return {'status': True}


@app.get('/ready')
async def readiness_check():
    """
    Returns 200 only when the application is ready to accept traffic.
    """

    # Ensure application startup work has completed
    if not getattr(app.state, 'startup_complete', False):
        log.info('Readiness check failed: startup not complete')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Startup not complete',
        )

    # Check database connectivity
    try:
        await async_db_ping()
    except Exception as e:
        log.warning(f'Readiness check DB ping failed: {e!r}')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Database not ready',
        )

    # Check Redis connectivity if configured
    redis = app.state.redis
    if redis is not None:
        try:
            pong = await redis.ping()
            if pong is False:
                raise Exception('Redis PING returned False')
        except Exception as e:
            log.warning(f'Readiness check Redis ping failed: {e!r}')
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Redis not ready',
            )

    return {'status': True}


@app.get('/health/db')
async def check_db_health():
    """Verify database connectivity by issuing a lightweight ping."""
    await async_db_ping()
    return {'status': True}


# --- static assets & files ---
# Serve build-time static assets (CSS, JS, images, favicon, etc.)
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')


@app.get('/cache/{path:path}')
async def serve_cache_file(
    path: str,
    user=Depends(get_verified_user),
):
    """Serve cached files (e.g. tool outputs) with path-traversal protection.

    Only ``image/*``, ``audio/*``, and ``video/*`` MIME types are served inline;
    everything else gets a ``Content-Disposition: attachment`` header to prevent
    XSS from user-generated HTML stored in the cache directory.
    """
    file_path = os.path.abspath(os.path.join(CACHE_DIR, path))
    # trailing os.sep is required: without it, a path resolving to a sibling
    # whose name starts with the cache-dir basename (e.g. cache_backup) passes
    cache_root = os.path.abspath(CACHE_DIR) + os.sep
    if not file_path.startswith(cache_root):
        raise HTTPException(status_code=404, detail='File not found')
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail='File not found')

    mime, _ = mimetypes.guess_type(file_path)
    inline_safe = mime and mime.split('/', 1)[0] in {'image', 'audio', 'video'}
    headers = {'X-Content-Type-Options': 'nosniff'}
    if not inline_safe:
        headers['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
    return FileResponse(file_path, headers=headers)


def swagger_ui_html(*args, **kwargs):
    return get_swagger_ui_html(
        *args,
        **kwargs,
        swagger_js_url='/static/swagger-ui/swagger-ui-bundle.js',
        swagger_css_url='/static/swagger-ui/swagger-ui.css',
        swagger_favicon_url='/static/swagger-ui/favicon.png',
    )


applications.get_swagger_ui_html = swagger_ui_html

if os.path.exists(FRONTEND_BUILD_DIR):
    mimetypes.add_type('text/javascript', '.js')
    pyodide_dir = FRONTEND_BUILD_DIR / 'pyodide'
    if os.path.exists(pyodide_dir):
        app.mount('/pyodide', CORSStaticFiles(directory=pyodide_dir), name='pyodide')

    app.mount(
        '/',
        SPAStaticFiles(directory=FRONTEND_BUILD_DIR, html=True),
        name='spa-static-files',
    )
else:
    log.warning(f"Frontend build directory not found at '{FRONTEND_BUILD_DIR}'. Serving API only.")

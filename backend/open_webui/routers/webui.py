import inspect
import json
import logging
import time
from typing import AsyncGenerator, Generator, Iterator

from open_webui.socket.main import get_event_call, get_event_emitter
from open_webui.models.functions import Functions
from open_webui.models.models import Models
from open_webui.routers import (
    auths,
    chats,
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
    utils,
)
from open_webui.utils.plugin import load_function_module_by_id
from open_webui.config import (
    ADMIN_EMAIL,
    CORS_ALLOW_ORIGIN,
    DEFAULT_MODELS,
    DEFAULT_PROMPT_SUGGESTIONS,
    DEFAULT_USER_ROLE,
    MODEL_ORDER_LIST,
    ENABLE_COMMUNITY_SHARING,
    ENABLE_LOGIN_FORM,
    ENABLE_MESSAGE_RATING,
    ENABLE_SIGNUP,
    ENABLE_API_KEY,
    ENABLE_EVALUATION_ARENA_MODELS,
    EVALUATION_ARENA_MODELS,
    DEFAULT_ARENA_MODEL,
    JWT_EXPIRES_IN,
    ENABLE_OAUTH_ROLE_MANAGEMENT,
    OAUTH_ROLES_CLAIM,
    OAUTH_EMAIL_CLAIM,
    OAUTH_PICTURE_CLAIM,
    OAUTH_USERNAME_CLAIM,
    OAUTH_ALLOWED_ROLES,
    OAUTH_ADMIN_ROLES,
    SHOW_ADMIN_DETAILS,
    USER_PERMISSIONS,
    WEBHOOK_URL,
    WEBUI_AUTH,
    WEBUI_BANNERS,
    ENABLE_LDAP,
    LDAP_SERVER_LABEL,
    LDAP_SERVER_HOST,
    LDAP_SERVER_PORT,
    LDAP_ATTRIBUTE_FOR_USERNAME,
    LDAP_SEARCH_FILTERS,
    LDAP_SEARCH_BASE,
    LDAP_APP_DN,
    LDAP_APP_PASSWORD,
    LDAP_USE_TLS,
    LDAP_CA_CERT_FILE,
    LDAP_CIPHERS,
    AppConfig,
)
from open_webui.env import (
    ENV,
    SRC_LOG_LEVELS,
    WEBUI_AUTH_TRUSTED_EMAIL_HEADER,
    WEBUI_AUTH_TRUSTED_NAME_HEADER,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from open_webui.utils.misc import (
    openai_chat_chunk_message_template,
    openai_chat_completion_message_template,
)
from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_model_system_prompt_to_body,
)


from open_webui.utils.tools import get_tools


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

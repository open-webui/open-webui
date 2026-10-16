"""
conftest.py - Stub infrastructure for middleware unit tests.

Strategy
--------
backend/ is on sys.path, so Python resolves the *real* open_webui package
from the filesystem:
    open_webui/                   ← backend/open_webui/__init__.py
    open_webui/utils/             ← backend/open_webui/utils/__init__.py
    open_webui/utils/middleware   ← backend/open_webui/utils/middleware.py

For every *other* open_webui.* module (config, env, models/*, routers/*, …)
we inject lightweight stub ModuleType objects into sys.modules *before* the
middleware module is imported.  Python checks sys.modules first, so the stubs
are returned instead of triggering any real import.
"""
from __future__ import annotations

import asyncio
import json as _json
import logging
import os
import sys
import types
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# 1. Put backend/ on sys.path so "open_webui.utils.middleware" resolves to
#    backend/open_webui/utils/middleware.py via normal package discovery.
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


# ---------------------------------------------------------------------------
# 2. Helper builders
# ---------------------------------------------------------------------------

def _stub(name: str, **attrs) -> types.ModuleType:
    """
    Register a stub module in sys.modules under *name*.

    We do NOT create parent-package stubs here — those should either be real
    packages found via sys.path or already exist in sys.modules.
    """
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    sys.modules[name] = m
    return m


def _async_ret(return_value=None):
    return AsyncMock(return_value=return_value)


def _async_echo_first():
    """Async function that echoes its first positional argument."""
    async def _impl(*args, **kwargs):
        return args[0] if args else None
    return _impl


def _async_echo_second():
    """Async function that echoes its second positional argument (form_data pattern)."""
    async def _impl(*args, **kwargs):
        return args[1] if len(args) > 1 else (args[0] if args else None)
    return _impl


# ---------------------------------------------------------------------------
# 3. aiocache stub (not available on Python 3.14)
# ---------------------------------------------------------------------------
if "aiocache" not in sys.modules:
    _stub("aiocache", cached=lambda *a, **kw: (lambda f: f))


# ---------------------------------------------------------------------------
# 4. open_webui leaf-module stubs
#    (open_webui and open_webui.utils are NOT stubbed — Python finds them
#     from backend/ via sys.path so that middleware.py is importable.)
# ---------------------------------------------------------------------------

# ---- open_webui.config ----
_stub(
    "open_webui.config",
    CACHE_DIR="/tmp/owtest",
    CODE_INTERPRETER_BLOCKED_MODULES=[],
    CODE_INTERPRETER_PYODIDE_PROMPT="",
    DEFAULT_CODE_INTERPRETER_PROMPT="",
    DEFAULT_TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE="{tools}",
    DEFAULT_VOICE_MODE_PROMPT_TEMPLATE="",
)

# ---- open_webui.constants ----
_stub("open_webui.constants", TASKS=MagicMock())

# ---- open_webui.env ----
_stub(
    "open_webui.env",
    BYPASS_MODEL_ACCESS_CONTROL=False,
    CHAT_RESPONSE_MAX_TOOL_CALL_ITERATIONS=5,
    CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE=512,
    ENABLE_API_OUTLET_FILTERS=False,
    ENABLE_CHAT_RESPONSE_BASE64_IMAGE_URL_CONVERSION=False,
    ENABLE_CHAT_RESPONSE_STREAM_INPLACE_APPEND=False,
    ENABLE_FUNCTIONS=False,        # disables the filter-functions path
    ENABLE_QUERIES_CACHE=False,
    ENABLE_REALTIME_CHAT_SAVE=False,
    ENABLE_RESPONSES_API_STATEFUL=False,
    ENABLE_TOOL_SERVERS=True,
    GLOBAL_LOG_LEVEL=logging.WARNING,
    RAG_SYSTEM_CONTEXT="",
)

# ---- open_webui.events ----
_stub(
    "open_webui.events",
    EVENTS=MagicMock(),
    publish_event=_async_ret(None),
)

# ---- open_webui.models.* ----
# UserModel must be a real class (isinstance() check in middleware.py)
class _UserModel:
    def __init__(self, id: str = "test-user", role: str = "user"):
        self.id = id
        self.role = role

    def model_dump(self) -> dict:
        return {"id": self.id, "role": self.role}

class _Config:
    @classmethod
    async def get(cls, key, default=None):
        if key == "terminal_server.connections":
            return []
        return default

class _Chats:
    @classmethod
    async def get_chat_by_id(cls, chat_id):
        return None
    @classmethod
    async def get_chat_folder_id(cls, chat_id, user_id):
        return None
    @classmethod
    async def get_message_by_id_and_message_id(cls, chat_id, msg_id):
        return None
    @classmethod
    async def upsert_message_to_chat_by_id_and_message_id(cls, *a, **kw):
        return None

class _Folders:
    @classmethod
    async def get_folder_by_id(cls, folder_id):
        return None

# Register all model stubs — these are leaf modules so we stub directly
_stub("open_webui.models.access_grants", AccessGrants=MagicMock())
_stub("open_webui.models.chats", Chats=_Chats)
_stub("open_webui.models.config", Config=_Config)
_stub("open_webui.models.folders", Folders=_Folders)
_stub("open_webui.models.models", Models=MagicMock())
_stub("open_webui.models.notes", Notes=MagicMock())
_stub("open_webui.models.users", UserModel=_UserModel, Users=MagicMock())
_stub("open_webui.models.skills", Skills=MagicMock())   # lazily imported

# ---- open_webui.retrieval.* ----
_stub(
    "open_webui.retrieval.utils",
    filter_source_metadata=MagicMock(return_value=[]),
    get_sources_from_items=MagicMock(return_value=[]),
)

# ---- open_webui.routers.* ----
_stub(
    "open_webui.routers.images",
    CreateImageForm=MagicMock(),
    EditImageForm=MagicMock(),
    image_edits=_async_ret(None),
    image_generations=_async_ret(None),
)
_stub(
    "open_webui.routers.pipelines",
    get_sorted_filters=MagicMock(return_value=[]),
    process_pipeline_inlet_filter=_async_echo_second(),   # returns form_data (arg[1])
    process_pipeline_outlet_filter=_async_echo_second(),
)
_stub(
    "open_webui.routers.retrieval",
    SearchForm=MagicMock(),
    process_web_search=_async_ret(None),
)
_stub(
    "open_webui.routers.tasks",
    generate_chat_tags=_async_ret(None),
    generate_follow_ups=_async_ret(None),
    generate_image_prompt=_async_ret(None),
    generate_queries=_async_ret([]),
    generate_title=_async_ret(None),
)

# ---- open_webui.socket.main ----
async def _make_event_emitter(metadata, update_db=True):
    async def _emit(event):
        pass
    return _emit

async def _make_event_caller(metadata):
    async def _call(event):
        return None
    return _call

_stub(
    "open_webui.socket.main",
    get_event_emitter=_make_event_emitter,
    get_event_call=_make_event_caller,
)

# ---- open_webui.tasks ----
_stub(
    "open_webui.tasks",
    append_response_stream=_async_ret(None),
    clear_response_stream=_async_ret(None),
    save_response_stream=_async_ret(None),
)

# ---- open_webui.utils.access_control* ----
_stub("open_webui.utils.access_control", has_permission=_async_ret(True))
_stub("open_webui.utils.access_control.files", get_owner_accessible_folder_files=_async_ret([]))
_stub("open_webui.utils.access_control.folders", has_folder_access=_async_ret(True))

# ---- open_webui.utils.ask_user ----
_stub("open_webui.utils.ask_user", stage_ask_user_tool_calls=MagicMock(return_value=[]))

# ---- open_webui.utils.chat ----
_stub("open_webui.utils.chat", generate_chat_completion=_async_ret(None))

# ---- open_webui.utils.chat_id ----
def _is_saved_chat_id(chat_id):
    """Return True only for non-empty string chat IDs (temporary chats have '')."""
    return bool(chat_id) and isinstance(chat_id, str)

_stub("open_webui.utils.chat_id", is_saved_chat_id=_is_saved_chat_id)

# ---- open_webui.utils.code_interpreter ----
_stub("open_webui.utils.code_interpreter", execute_code_jupyter=_async_ret(None))

# ---- open_webui.utils.context_compaction ----
async def _compact(request, user, messages, metadata, model, models, system_prompt=None):
    return messages, None, False

_stub("open_webui.utils.context_compaction", compact_messages_for_request=_compact)

# ---- open_webui.utils.files ----
_stub(
    "open_webui.utils.files",
    convert_markdown_base64_images=MagicMock(return_value=[]),
    get_file_url_from_base64=MagicMock(return_value=None),
    get_image_base64_from_url=_async_ret(None),
    get_image_url_from_base64=MagicMock(return_value=None),
)

# ---- open_webui.utils.filter ----
class _FilterContext:
    pass

_stub(
    "open_webui.utils.filter",
    FilterContext=_FilterContext,
    get_filter_context=MagicMock(return_value=None),
    get_filter_functions=_async_ret([]),
    process_filter_functions=AsyncMock(return_value=({}, {})),
)

# ---- open_webui.utils.json_codec ----
class _JSONCodec:
    JSONDecodeError = _json.JSONDecodeError

    @staticmethod
    def loads(s):
        return _json.loads(s)

    @staticmethod
    def dumps(obj):
        return _json.dumps(obj)

_stub(
    "open_webui.utils.json_codec",
    JSONCodec=_JSONCodec,
    dumps_bytes=MagicMock(return_value=b"{}"),
)

# ---- open_webui.utils.memory ----
_stub(
    "open_webui.utils.memory",
    add_memory_context=_async_echo_second(),   # add_memory_context(request, form_data, ...) → form_data
    review_memory_after_turn=_async_ret(None),
)

# ---- open_webui.utils.misc ----
# Provide real implementations for functions that process_chat_payload calls
# on our simple test messages.

def _get_system_message(messages):
    for m in messages:
        if isinstance(m, dict) and m.get("role") == "system":
            return m
    return None

def _get_last_user_message(messages):
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            content = m.get("content", "")
            return content if isinstance(content, str) else ""
    return ""

def _get_last_user_message_item(messages):
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            return m
    return None

def _get_content_from_message(message):
    if message is None:
        return ""
    return message.get("content", "") if isinstance(message, dict) else ""

def _add_or_update_system_message(content, messages, append=False):
    for m in messages:
        if isinstance(m, dict) and m.get("role") == "system":
            if append:
                existing = m.get("content", "")
                m["content"] = f"{existing}\n{content}" if existing else content
            else:
                m["content"] = content
            return messages
    return [{"role": "system", "content": content}, *messages]

_stub(
    "open_webui.utils.misc",
    add_or_update_system_message=_add_or_update_system_message,
    add_or_update_user_message=lambda c, msgs: msgs,
    convert_output_to_messages=MagicMock(return_value=[]),
    extract_urls=MagicMock(return_value=[]),
    get_content_from_message=_get_content_from_message,
    get_last_assistant_message=MagicMock(return_value=""),
    get_last_user_message=_get_last_user_message,
    get_last_user_message_item=_get_last_user_message_item,
    get_message_list=MagicMock(return_value=[]),
    get_output_text=MagicMock(return_value=""),
    get_paired_tool_call_ids=MagicMock(return_value=[]),
    get_reasoning_details=MagicMock(return_value={}),
    get_response_error_detail=MagicMock(return_value=None),
    get_system_message=_get_system_message,
    is_raster_image_content_type=MagicMock(return_value=False),
    merge_system_messages=lambda msgs: msgs,
    prepend_to_first_user_message_content=lambda c, msgs: msgs,
    replace_system_message_content=lambda c, msgs: msgs,
    set_last_user_message_content=lambda c, msgs: None,
    strip_empty_content_blocks=lambda msgs: msgs,
)

# ---- open_webui.utils.oauth ----
_stub("open_webui.utils.oauth", get_system_oauth_token=_async_ret(None))

# ---- open_webui.utils.payload ----
def _apply_params(form_data, model):
    return form_data

async def _apply_system_prompt(content, form_data, metadata, user, replace=False):
    return form_data

async def _resolve_system_prompt(template, metadata, user):
    return None

_stub(
    "open_webui.utils.payload",
    apply_params_to_form_data=_apply_params,
    apply_system_prompt_to_body=_apply_system_prompt,
    resolve_system_prompt=_resolve_system_prompt,
)

# ---- open_webui.utils.plugin ----
_stub("open_webui.utils.plugin", load_function_module_by_id=_async_ret(None))

# ---- open_webui.utils.response ----
_stub(
    "open_webui.utils.response",
    get_response_delta_key=MagicMock(return_value="content"),
    handle_responses_streaming_event=MagicMock(return_value=None),
    merge_usage=MagicMock(return_value={}),
    normalize_usage=MagicMock(return_value={}),
)

# ---- open_webui.utils.sanitize ----
_stub("open_webui.utils.sanitize", sanitize_code=MagicMock(return_value=""))

# ---- open_webui.utils.skills ----
_stub(
    "open_webui.utils.skills",
    apply_skills_create_prompt=MagicMock(return_value=False),
    extract_skill_ids_from_messages=MagicMock(return_value=set()),
    has_prior_user_message=MagicMock(return_value=True),
    replace_skill_mentions_with_labels=MagicMock(return_value=[]),
    strip_skill_mentions=MagicMock(),          # in-place, no return used
)

# ---- open_webui.utils.task ----
_stub(
    "open_webui.utils.task",
    get_task_model_id=lambda model_id, *a, **kw: model_id,
    parse_follow_ups=MagicMock(return_value=[]),
    rag_template=MagicMock(return_value=""),
    tools_function_calling_generation_template=MagicMock(return_value=""),
)

# ---- open_webui.utils.tool_approval ----
_stub(
    "open_webui.utils.tool_approval",
    complete_tool_call=MagicMock(),
    pending_tool_calls=MagicMock(return_value=False),
)

# ---- open_webui.utils.tool_search ----
async def _apply_tool_search(form_data, metadata, tools_dict, inlet_filter_tools):
    """No deferred tools — all tools flow directly to form_data['tools']."""
    return []

_stub(
    "open_webui.utils.tool_search",
    apply_tool_search=_apply_tool_search,
    resolve_tool_call=_async_ret(None),
)

# ---- open_webui.utils.tools ----
async def _get_builtin_tools_default(request, extra_params, features, model, is_note_chat=False):
    """
    Simulate the real get_builtin_tools() for a UI session.

    The real function returns a non-empty dict of tools for any session that
    has a session_id, regardless of whether the model supports tools.  That
    non-empty return value is what causes form_data['tools'] to be populated
    when use_builtin_tools is True (the bug).
    """
    return {
        "web_search": {
            "spec": {
                "name": "web_search",
                "description": "Search the web for up-to-date information",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Search query"}},
                    "required": ["query"],
                },
            },
            "type": "builtin",
        },
        "generate_image": {
            "spec": {
                "name": "generate_image",
                "description": "Generate an image",
                "parameters": {
                    "type": "object",
                    "properties": {"prompt": {"type": "string"}},
                    "required": ["prompt"],
                },
            },
            "type": "builtin",
        },
    }

_stub(
    "open_webui.utils.tools",
    connect_mcp_server=_async_ret(None),
    get_attached_knowledge=MagicMock(return_value=[]),
    get_builtin_tools=_get_builtin_tools_default,
    get_terminal_tools=_async_ret(None),
    get_tools=_async_ret({}),
    get_updated_tool_function=MagicMock(return_value=None),
)

# ---- lazily-imported modules (inside if-blocks in middleware.py) ----
_stub(
    "open_webui.utils.terminals",
    add_terminal_agents_md=MagicMock(return_value=[]),
    get_terminal_agents_md=_async_ret(None),
    format_terminal_skill_context=MagicMock(return_value=""),
    format_terminal_skill_manifest_entry=MagicMock(return_value=""),
    get_terminal_json=_async_ret(None),
    get_terminal_skill=_async_ret(None),
)
_stub(
    "open_webui.utils.skill_files",
    format_skill_content=MagicMock(return_value=""),
    skill_overview=_async_ret(""),
)

# ---------------------------------------------------------------------------
# 5. pytest fixtures
# ---------------------------------------------------------------------------
import pytest


@pytest.fixture
def mock_user():
    """Minimal user compatible with process_chat_payload."""
    return _UserModel(id="test-user-001", role="user")


@pytest.fixture
def mock_request():
    """Minimal FastAPI-like request object."""
    state = MagicMock()
    state.direct = False
    state.internal = False
    request = MagicMock()
    request.state = state
    request.app.state.MODELS = {}
    request.app.state.config = MagicMock()
    return request

import logging
import sys
import inspect
import json
import asyncio

from pydantic import BaseModel
from typing import AsyncGenerator, Generator, Iterator
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from starlette.responses import Response, StreamingResponse
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.models.users import UserModel

from open_webui.socket.main import (
    get_event_call,
    get_event_emitter,
)


from open_webui.models.functions import Functions
from open_webui.models.models import Models

from open_webui.utils.plugin import load_function_module_by_id
from open_webui.utils.tools import get_tools
from open_webui.utils.access_control import has_access
from open_webui.utils.super_admin import is_super_admin

from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

# OpenTelemetry instrumentation helpers
try:
    from open_webui.utils.otel_instrumentation import (
        trace_span_async,
        add_span_event,
        set_span_attribute,
    )
    from opentelemetry.trace import SpanKind
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    # Create no-op functions if OTEL not available
    # NOTE: Must be regular function (not async def) to match @asynccontextmanager signature
    def trace_span_async(*args, **kwargs):
        span_name = kwargs.get('name', args[0] if args else 'unknown')
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def _noop():
            # Get logger at call time (log variable will be defined by then)
            _log = logging.getLogger(__name__)
            try:
                _log.debug(f"[trace_span_async] Generator entering (OTEL unavailable, no-op) for span '{span_name}'")
                yield None
                _log.debug(f"[trace_span_async] Generator exiting normally (OTEL unavailable, no-op) for span '{span_name}'")
            except GeneratorExit as ge:
                _log.debug(f"[trace_span_async] GeneratorExit caught (OTEL unavailable, no-op) for span '{span_name}': {ge}")
                # Properly handle generator exit
                raise
            except Exception as e:
                _log.warning(f"[trace_span_async] Exception thrown into generator (OTEL unavailable, no-op) for span '{span_name}': {type(e).__name__}: {e}", exc_info=True)
                # Properly handle exceptions thrown into generator - must re-raise or return
                # Re-raising ensures the exception propagates correctly
                raise
        return _noop()
    def add_span_event(*args, **kwargs):
        pass
    def set_span_attribute(*args, **kwargs):
        pass
    SpanKind = None

from open_webui.utils.misc import (
    add_or_update_system_message,
    get_last_user_message,
    prepend_to_first_user_message_content,
    openai_chat_chunk_message_template,
    openai_chat_completion_message_template,
)
from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_model_system_prompt_to_body,
)


logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

# Safe wrapper functions that NEVER fail - OTEL is monitoring only, must not affect task execution
def safe_add_span_event(event_name, attributes=None):
    """Safely add span event - never fails, even if OTEL is broken"""
    try:
        add_span_event(event_name, attributes)
    except Exception as e:
        log.debug(f"OTEL add_span_event failed (non-critical): {e}")

def safe_trace_span_async(*args, **kwargs):
    """Safely create async trace span - never fails, even if OTEL is broken
    
    Returns an async context manager (same signature as trace_span_async).
    Can be used with: async with safe_trace_span_async(...) as span:
    """
    span_name = kwargs.get('name', args[0] if args else 'unknown')
    try:
        log.debug(f"[safe_trace_span_async] Attempting to create span '{span_name}'")
        return trace_span_async(*args, **kwargs)  # Returns async context manager, not a coroutine
    except Exception as e:
        log.warning(f"[safe_trace_span_async] OTEL trace_span_async failed (non-critical) for span '{span_name}': {type(e).__name__}: {e}", exc_info=True)
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def _noop():
            try:
                log.debug(f"[safe_trace_span_async] Generator entering (safe fallback) for span '{span_name}'")
                yield None
                log.debug(f"[safe_trace_span_async] Generator exiting normally (safe fallback) for span '{span_name}'")
            except GeneratorExit as ge:
                log.debug(f"[safe_trace_span_async] GeneratorExit caught (safe fallback) for span '{span_name}': {ge}")
                # Properly handle generator exit
                raise
            except Exception as gen_exc:
                log.warning(f"[safe_trace_span_async] Exception thrown into generator (safe fallback) for span '{span_name}': {type(gen_exc).__name__}: {gen_exc}", exc_info=True)
                # Properly handle exceptions thrown into generator - must re-raise or return
                # Re-raising ensures the exception propagates correctly
                raise
        return _noop()


def get_function_module_by_id(request: Request, pipe_id: str):
    log.debug(f"[DEBUG] [inside get_function_module_by_id() from functions.py] entry. pipe_id={pipe_id}.")
    # Check if function is already loaded
    if pipe_id not in request.app.state.FUNCTIONS:
        log.debug(f"[DEBUG] [inside get_function_module_by_id() from functions.py] cache miss for pipe_id={pipe_id}; loading via load_function_module_by_id().")
        function_module, _, _ = load_function_module_by_id(pipe_id)
        request.app.state.FUNCTIONS[pipe_id] = function_module
    else:
        log.debug(f"[DEBUG] [inside get_function_module_by_id() from functions.py] cache hit for pipe_id={pipe_id}.")
        function_module = request.app.state.FUNCTIONS[pipe_id]

    if hasattr(function_module, "valves") and hasattr(function_module, "Valves"):
        valves = Functions.get_function_valves_by_id(pipe_id)
        function_module.valves = function_module.Valves(**(valves if valves else {}))
    return function_module


async def get_function_models(request, user: UserModel = None):
    # Defensive check: return empty list if user is None
    if user is None:
        return []
    
    from open_webui.models.groups import Groups
    from open_webui.models.users import Users
    from open_webui.models.models import Models
    from open_webui.internal.db import get_db
    from open_webui.models.models import Model
    
    pipes = Functions.get_functions_by_type("pipe", active_only=True)
    pipe_models = []

    # OPTIMIZATION: Pre-fetch data needed for filtering ONCE, not per-pipe
    # This avoids N database queries in the loop
    
    # For users: pre-fetch user's groups and all models assigned to those groups
    user_group_ids = set()  # Initialize as set for consistency
    accessible_model_ids = set()  # Model IDs assigned to user's groups
    accessible_pipe_ids = set()  # Pipe IDs that have models assigned to user's groups
    
    # For users AND admins (co-admins), we need to check group-based access
    # Pre-fetch groups for both roles
    if user.role in ("user", "admin"):
        # Fetch user's groups ONCE
        user_groups = Groups.get_groups_by_member_id(user.id)
        user_group_ids = set(g.id for g in user_groups)
        
        log.debug(f"[MODEL_VISIBILITY] User {user.email} (id={user.id}) belongs to {len(user_groups)} groups")
        log.debug(f"[MODEL_VISIBILITY] User group IDs: {user_group_ids}")
        
        # Fetch ALL models with access_control in ONE query
        # Build sets of accessible model IDs and pipe IDs
        with get_db() as db:
            all_models_with_access = db.query(Model).filter(
                Model.access_control.isnot(None)
            ).all()
        
        log.debug(f"[MODEL_VISIBILITY] Found {len(all_models_with_access)} models with access_control set")
        
        for model in all_models_with_access:
            if model.access_control:
                read_groups = set(model.access_control.get("read", {}).get("group_ids", []))
                log.debug(f"[MODEL_VISIBILITY] Model '{model.id}' has read groups: {read_groups}")
                # Check if any of user's groups have read access to this model
                if read_groups & user_group_ids:
                    log.debug(f"[MODEL_VISIBILITY] MATCH! User has access to model '{model.id}'")
                    accessible_model_ids.add(model.id)
                    
                    # Determine which ID to use for pipe extraction:
                    # - Preset models have base_model_id pointing to the actual pipe model
                    # - Pipe models have the pipe ID as prefix of model.id
                    model_id_for_pipe = model.id
                    if model.base_model_id:
                        # This is a preset model - use base_model_id to find the pipe
                        model_id_for_pipe = model.base_model_id
                        # IMPORTANT: Also add base_model_id to accessible_model_ids
                        # so that when filtering sub-pipes, the underlying model is accessible
                        accessible_model_ids.add(model.base_model_id)
                        log.debug(f"[MODEL_VISIBILITY] Model '{model.id}' is a preset, using base_model_id '{model.base_model_id}' for pipe extraction")
                        log.debug(f"[MODEL_VISIBILITY] Added base_model_id '{model.base_model_id}' to accessible_model_ids")
                    
                    # Extract pipe ID from the appropriate model ID
                    # e.g., "llm_portkey.@gpt-4o/gpt-4o" -> "llm_portkey"
                    if "." in model_id_for_pipe:
                        pipe_id = model_id_for_pipe.split(".", 1)[0]
                        accessible_pipe_ids.add(pipe_id)
                        log.debug(f"[MODEL_VISIBILITY] Extracted pipe_id '{pipe_id}' from '{model_id_for_pipe}'")
                    else:
                        # Model ID without dot - might be a standalone pipe ID
                        accessible_pipe_ids.add(model_id_for_pipe)
        
        log.debug(f"[MODEL_VISIBILITY] User {user.email} has access to {len(accessible_model_ids)} models: {accessible_model_ids}")
        log.debug(f"[MODEL_VISIBILITY] User {user.email} has access to pipes: {accessible_pipe_ids}")
    
    # STEP 1: Filter pipes based on access (fast, no module loading)
    accessible_pipes = []
    log.debug(f"[MODEL_VISIBILITY] Total active pipes: {len(pipes)}")
    for pipe in pipes:
        log.debug(f"[MODEL_VISIBILITY] Checking pipe '{pipe.id}' (created_by={pipe.created_by})")
        # For super admins: show all pipes
        if is_super_admin(user):
            accessible_pipes.append(pipe)
        # For admins: show pipes they created OR pipes with models assigned to their groups (co-admin)
        elif user.role == "admin":
            # Admin created this pipe
            if pipe.created_by == user.email:
                accessible_pipes.append(pipe)
            # OR admin is a co-admin (member of a group that has access to models from this pipe)
            elif pipe.id in accessible_pipe_ids:
                log.debug(f"[MODEL_VISIBILITY] Admin {user.email} has co-admin access to pipe '{pipe.id}'")
                accessible_pipes.append(pipe)
        # For users: only show pipes that have models assigned to user's groups
        elif user.role == "user":
            # Check if this pipe has any models assigned to user's groups
            if pipe.id in accessible_pipe_ids:
                log.debug(f"[MODEL_VISIBILITY] Pipe '{pipe.id}' is accessible to user")
                accessible_pipes.append(pipe)
            else:
                log.debug(f"[MODEL_VISIBILITY] Pipe '{pipe.id}' NOT accessible - not in {accessible_pipe_ids}")
        # Unknown role - skip for safety
        else:
            log.warning(f"Unknown user role '{user.role}' for user {user.email} - skipping pipe {pipe.id}")
    
    log.debug(f"[MODEL_VISIBILITY] Accessible pipes for user {user.email}: {[p.id for p in accessible_pipes]}")
    
    # STEP 2: Load modules and fetch models only for accessible pipes
    # OPTIMIZATION: Process pipes in parallel to avoid sequential HTTP calls
    
    async def process_single_pipe(pipe):
        """Process a single pipe and return its models."""
        models = []
        try:
            function_module = get_function_module_by_id(request, pipe.id)

            # Check if function is a manifold
            if hasattr(function_module, "pipes"):
                sub_pipes = []

                # Handle pipes being a list, sync function, or async function
                try:
                    if callable(function_module.pipes):
                        if asyncio.iscoroutinefunction(function_module.pipes):
                            sub_pipes = await function_module.pipes()
                        else:
                            # Run sync function in thread pool to avoid blocking
                            loop = asyncio.get_running_loop()
                            sub_pipes = await loop.run_in_executor(None, function_module.pipes)
                    else:
                        # pipes is not callable - treat as list/iterable
                        sub_pipes = function_module.pipes
                    
                    # Ensure sub_pipes is iterable and convert to list if needed
                    if sub_pipes is None:
                        sub_pipes = []
                    elif not isinstance(sub_pipes, (list, tuple)):
                        # Try to convert to list, but if it fails, use empty list
                        try:
                            sub_pipes = list(sub_pipes) if hasattr(sub_pipes, '__iter__') else []
                        except Exception:
                            sub_pipes = []
                except Exception as e:
                    log.exception(f"Error fetching sub-pipes for {pipe.id}: {e}")
                    sub_pipes = []

                log.debug(f"get_function_models: function '{pipe.id}' is a manifold of {sub_pipes}")

                # Iterate over sub_pipes and validate each entry
                # Determine if this admin is the creator, a super admin, or a co-admin
                is_pipe_creator = (user.role == "admin" and pipe.created_by == user.email)
                user_is_super_admin = is_super_admin(user)
                
                for p in sub_pipes:
                    # Defensive check: ensure p is a dict with required keys
                    if not isinstance(p, dict):
                        log.warning(f"Invalid sub-pipe entry for {pipe.id}: expected dict, got {type(p)}")
                        continue
                    if "id" not in p or "name" not in p:
                        log.warning(f"Invalid sub-pipe entry for {pipe.id}: missing 'id' or 'name' key: {p}")
                        continue
                    sub_pipe_id = f'{pipe.id}.{p["id"]}'
                    sub_pipe_name = p["name"]

                    # For users AND co-admins: only include models that are explicitly assigned to their groups
                    # Super admins and admins who created the pipe see all models; co-admins see only assigned models
                    if not user_is_super_admin and (user.role == "user" or (user.role == "admin" and not is_pipe_creator)):
                        if sub_pipe_id not in accessible_model_ids:
                            log.debug(f"Skipping model {sub_pipe_id} - not assigned to user's/co-admin's groups")
                            continue
                    
                    if hasattr(function_module, "name"):
                        sub_pipe_name = f"{function_module.name}{sub_pipe_name}"

                    pipe_flag = {"type": pipe.type}

                    models.append({
                            "id": sub_pipe_id,
                            "name": sub_pipe_name,
                            "object": "model",
                            "created": pipe.created_at,
                            "owned_by": "openai",
                            "pipe": pipe_flag,
                            "created_by": pipe.created_by,
                    })
            else:
                pipe_flag = {"type": "pipe"}

                # Determine if this admin is the creator, a super admin, or a co-admin
                is_pipe_creator = (user.role == "admin" and pipe.created_by == user.email)
                user_is_super_admin = is_super_admin(user)

                # For users AND co-admins: only include models that are explicitly assigned to their groups
                # Super admins and admins who created the pipe see all models
                if not user_is_super_admin and (user.role == "user" or (user.role == "admin" and not is_pipe_creator)):
                    if pipe.id not in accessible_model_ids:
                        log.debug(f"Skipping model {pipe.id} - not assigned to user's/co-admin's groups")
                        return models  # Return empty list
                
                log.debug(f"get_function_models: function '{pipe.id}' is a single pipe {{ 'id': {pipe.id}, 'name': {pipe.name} }}")

                models.append({
                        "id": pipe.id,
                        "name": pipe.name,
                        "object": "model",
                        "created": pipe.created_at,
                        "owned_by": "openai",
                        "pipe": pipe_flag,
                        "created_by": pipe.created_by,
                })
        except Exception as e:
            log.exception(f"Error processing pipe {pipe.id}: {e}")
        
        return models
    
    # Run all pipe processing in parallel
    if accessible_pipes:
        results = await asyncio.gather(*[process_single_pipe(pipe) for pipe in accessible_pipes], return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                log.error(f"Pipe processing failed: {result}")
            elif result:
                pipe_models.extend(result)

    return pipe_models


async def generate_function_chat_completion(
    request, form_data, user, models: dict = {}
):
    # Extract pipe/function info for instrumentation
    model_id = form_data.get("model", "unknown")
    pipe_id = model_id
    if "." in pipe_id:
        pipe_id, _ = pipe_id.split(".", 1)
    is_streaming = form_data.get("stream", False)
    log.debug(
        f"[DEBUG] [inside generate_function_chat_completion() from functions.py] entry. pipe_id={pipe_id}, model_id={model_id}, "
        f"user={getattr(user, 'email', None)} (id={getattr(user, 'id', None)}), stream={is_streaming}."
    )
    # Create span for function/pipe chat completion
    # CRITICAL: Use safe_trace_span_async to ensure OTEL failures never prevent function execution
    async with safe_trace_span_async(
        name="llm.function.chat_completion",
        attributes={
            "llm.provider": "function",
            "llm.function.id": pipe_id,
            "llm.model": model_id,
            "llm.stream": is_streaming,
        },
        kind=SpanKind.CLIENT if OTEL_AVAILABLE and SpanKind else None,
    ) as span:
        try:
            # Add event: Function/pipe request started
            safe_add_span_event("llm.function.request", {
                "function_id": pipe_id,
                "model": model_id,
            })
            
            async def execute_pipe(pipe, params):
                if inspect.iscoroutinefunction(pipe):
                    return await pipe(**params)
                else:
                    return pipe(**params)

            async def get_message_content(res: str | Generator | AsyncGenerator) -> str:
                if isinstance(res, str):
                    return res
                if isinstance(res, Generator):
                    return "".join(map(str, res))
                if isinstance(res, AsyncGenerator):
                    return "".join([str(stream) async for stream in res])

            def process_line(form_data: dict, line):
                if isinstance(line, BaseModel):
                    line = line.model_dump_json()
                    line = f"data: {line}"
                if isinstance(line, dict):
                    line = f"data: {json.dumps(line)}"

                try:
                    line = line.decode("utf-8")
                except Exception:
                    pass

                if line.startswith("data:"):
                    return f"{line}\n\n"
                else:
                    line = openai_chat_chunk_message_template(form_data["model"], line)
                    return f"data: {json.dumps(line)}\n\n"

            def get_pipe_id(form_data: dict) -> str:
                pipe_id = form_data["model"]
                if "." in pipe_id:
                    pipe_id, _ = pipe_id.split(".", 1)
                return pipe_id

            def get_function_params(function_module, form_data, user, extra_params=None):
                if extra_params is None:
                    extra_params = {}

                pipe_id = get_pipe_id(form_data)

                # Get the signature of the function
                sig = inspect.signature(function_module.pipe)
                params = {"body": form_data} | {
                    k: v for k, v in extra_params.items() if k in sig.parameters
                }

                if "__user__" in params and hasattr(function_module, "UserValves"):
                    user_valves = Functions.get_user_valves_by_id_and_user_id(pipe_id, user.id)
                    try:
                        params["__user__"]["valves"] = function_module.UserValves(**user_valves)
                    except Exception as e:
                        log.exception(e)
                        params["__user__"]["valves"] = function_module.UserValves()

                return params

            model_id = form_data.get("model")
            model_info = Models.get_model_by_id(model_id)

            metadata = form_data.pop("metadata", {})

            files = metadata.get("files", [])
            tool_ids = metadata.get("tool_ids", [])
            # Check if tool_ids is None
            if tool_ids is None:
                tool_ids = []

            __event_emitter__ = None
            __event_call__ = None
            __task__ = None
            __task_body__ = None

            if metadata:
                has_keys = all(k in metadata for k in ("session_id", "chat_id", "message_id"))
                has_valid_values = (
                    metadata.get("session_id") and metadata.get("chat_id") and metadata.get("message_id")
                )
                if has_keys and has_valid_values:
                    __event_emitter__ = get_event_emitter(metadata)
                    __event_call__ = get_event_call(metadata)
                    log.debug(
                        f"[DEBUG] [WS-CHAT 8] [inside generate_function_chat_completion() from functions.py] metadata has session_id/chat_id/message_id; "
                        f"__event_emitter__ set. session_id={metadata.get('session_id')!r} chat_id={metadata.get('chat_id')!r}."
                    )
                else:
                    log.debug(
                        f"[DEBUG] [WS-CHAT 9] [inside generate_function_chat_completion() from functions.py] metadata missing or invalid session_id/chat_id/message_id; "
                        f"__event_emitter__=None. session_id={metadata.get('session_id')!r} chat_id={metadata.get('chat_id')!r} message_id={metadata.get('message_id')!r}. (BROKE: no emitter for pipe.)"
                    )
                __task__ = metadata.get("task", None)
                __task_body__ = metadata.get("task_body", None)

            extra_params = {
                "__event_emitter__": __event_emitter__,
                "__event_call__": __event_call__,
                "__task__": __task__,
                "__task_body__": __task_body__,
                "__files__": files,
                "__user__": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                },
                "__metadata__": metadata,
                "__request__": request,
            }
            extra_params["__tools__"] = get_tools(
                request,
                tool_ids,
                user,
                {
                    **extra_params,
                    "__model__": models.get(form_data["model"], None),
                    "__messages__": form_data["messages"],
                    "__files__": files,
                },
            )

            if model_info:
                if model_info.base_model_id:
                    form_data["model"] = model_info.base_model_id

                params = model_info.params.model_dump()
                form_data = apply_model_params_to_body_openai(params, form_data)
                form_data = apply_model_system_prompt_to_body(params, form_data, metadata, user)

            pipe_id = get_pipe_id(form_data)
            function_module = get_function_module_by_id(request, pipe_id)
            log.debug(
                f"[DEBUG] [WS-CHAT 10] [inside generate_function_chat_completion() from functions.py] got function module for pipe_id={pipe_id}; executing pipe (stream={form_data.get('stream', False)})."
            )
            pipe = function_module.pipe
            params = get_function_params(function_module, form_data, user, extra_params)

            if form_data.get("stream", False):

                async def stream_content():
                    try:
                        res = await execute_pipe(pipe, params)

                        # Directly return if the response is a StreamingResponse
                        if isinstance(res, StreamingResponse):
                            async for data in res.body_iterator:
                                yield data
                            return
                        if isinstance(res, dict):
                            yield f"data: {json.dumps(res)}\n\n"
                            return

                        # Process different response types
                        if isinstance(res, str):
                            message = openai_chat_chunk_message_template(form_data["model"], res)
                            yield f"data: {json.dumps(message)}\n\n"
                            # Send finish message for string responses
                            finish_message = openai_chat_chunk_message_template(
                                form_data["model"], ""
                            )
                            finish_message["choices"][0]["finish_reason"] = "stop"
                            yield f"data: {json.dumps(finish_message)}\n\n"
                            yield "data: [DONE]"
                            return

                        if isinstance(res, Iterator):
                            for line in res:
                                yield process_line(form_data, line)
                            # Send finish message for Iterator responses
                            finish_message = openai_chat_chunk_message_template(
                                form_data["model"], ""
                            )
                            finish_message["choices"][0]["finish_reason"] = "stop"
                            yield f"data: {json.dumps(finish_message)}\n\n"
                            yield "data: [DONE]"
                            return

                        if isinstance(res, AsyncGenerator):
                            async for line in res:
                                yield process_line(form_data, line)
                            # Send finish message for AsyncGenerator responses
                            finish_message = openai_chat_chunk_message_template(
                                form_data["model"], ""
                            )
                            finish_message["choices"][0]["finish_reason"] = "stop"
                            yield f"data: {json.dumps(finish_message)}\n\n"
                            yield "data: [DONE]"
                            return

                        if isinstance(res, Generator):
                            for line in res:
                                yield process_line(form_data, line)
                            # Send finish message for Generator responses
                            finish_message = openai_chat_chunk_message_template(
                                form_data["model"], ""
                            )
                            finish_message["choices"][0]["finish_reason"] = "stop"
                            yield f"data: {json.dumps(finish_message)}\n\n"
                            yield "data: [DONE]"
                            return

                    except Exception as e:
                        log.error(f"Error in stream_content: {e}")
                        yield f"data: {json.dumps({'error': {'detail':str(e)}})}\n\n"
                        return

                # Add event: Function response (streaming)
                safe_add_span_event("llm.function.response", {
                    "status": "success",
                    "streaming": True,
                })
                
                return StreamingResponse(stream_content(), media_type="text/event-stream")
            else:
                try:
                    res = await execute_pipe(pipe, params)

                except Exception as e:
                    log.error(f"Error: {e}")
                    return {"error": {"detail": str(e)}}

                if isinstance(res, StreamingResponse) or isinstance(res, dict):
                    # Add event: Function response (non-streaming)
                    safe_add_span_event("llm.function.response", {
                        "status": "success",
                        "streaming": False,
                    })
                    return res
                if isinstance(res, BaseModel):
                    # Add event: Function response (non-streaming)
                    safe_add_span_event("llm.function.response", {
                        "status": "success",
                        "streaming": False,
                    })
                    return res.model_dump()

                message = await get_message_content(res)
                
                # Add event: Function response (non-streaming)
                safe_add_span_event("llm.function.response", {
                    "status": "success",
                    "streaming": False,
                })
                
                return openai_chat_completion_message_template(form_data["model"], message)
            
        except Exception as e:
            # Add event: Function error
            safe_add_span_event("llm.function.error", {
                "error.type": type(e).__name__,
                "error.message": str(e)[:200],
                "function_id": pipe_id,
            })
            
            # Re-raise exception (span status will be set by trace_span_async)
            raise

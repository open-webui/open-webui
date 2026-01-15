import time
import logging
import sys

from aiocache import cached
from typing import Any, Optional
import random
import json
import inspect
import uuid
import asyncio

from fastapi import Request, status, HTTPException
from starlette.responses import Response, StreamingResponse, JSONResponse


from open_webui.models.users import UserModel

from open_webui.socket.main import (
    sio,
    get_event_call,
    get_event_emitter,
)
from open_webui.functions import generate_function_chat_completion

from open_webui.routers.openai import (
    generate_chat_completion as generate_openai_chat_completion,
)

from open_webui.routers.ollama import (
    generate_chat_completion as generate_ollama_chat_completion,
)

from open_webui.routers.pipelines import (
    process_pipeline_inlet_filter,
    process_pipeline_outlet_filter,
)

from open_webui.models.functions import Functions
from open_webui.models.models import Models


from open_webui.utils.plugin import (
    load_function_module_by_id,
    get_function_module_from_cache,
)
from open_webui.utils.models import get_all_models, check_model_access
from open_webui.utils.payload import convert_payload_openai_to_ollama
from open_webui.utils.response import (
    convert_response_ollama_to_openai,
    convert_streaming_response_ollama_to_openai,
)
from open_webui.utils.filter import (
    get_sorted_filter_ids,
    process_filter_functions,
)

from open_webui.env import GLOBAL_LOG_LEVEL, BYPASS_MODEL_ACCESS_CONTROL, ENABLE_SERVER_SIDE_ORCHESTRATION
from open_webui.models.chats import Chats

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)

class ServerSideChatManager:
    @staticmethod
    def snapshot_context(request: Request, form_data: dict, user: Any, metadata: dict, model: dict):
        """
        Creates a background-safe snapshot of the chat context.
        """
        # Capture only what's necessary to avoid serializing massive objects
        return {
            "form_data": json.loads(json.dumps(form_data)),
            "user_id": user.id,
            "user_role": user.role,
            "metadata": json.loads(json.dumps(metadata)),
            "model": json.loads(json.dumps(model)) if model else None,
            "session_id": metadata.get("session_id"),
            "chat_id": metadata.get("chat_id"),
            "message_id": metadata.get("message_id"),
            "direct": getattr(request.state, "direct", False),
            "token": getattr(request.state, "token", None)
        }

    @staticmethod
    async def orchestrate(snapshot: dict, app_state: Any):
        """
        The main orchestration loop for server-side chat generation.
        """
        chat_id = snapshot.get("chat_id")
        message_id = snapshot.get("message_id")
        user_id = snapshot.get("user_id")
        user_role = snapshot.get("user_role")

        log.info(f"Starting server-side orchestration for chat {chat_id}, message {message_id}")

        # 1. Setup Event Emitter
        metadata = snapshot["metadata"]

        # 2. Create User and Request objects
        user = type('obj', (object,), {"id": user_id, "role": user_role})
        
        class MockRequest:
            def __init__(self, app_state, metadata, snapshot):
                self.app = type('obj', (object,), {'state': app_state})
                self.state = type('obj', (object,), {
                    'metadata': metadata,
                    'direct': snapshot.get("direct", False),
                    'token': snapshot.get("token")
                })
                self.cookies = {}

        mock_request = MockRequest(app_state, metadata, snapshot)

        from open_webui.constants import TASKS
        
        # Inlets, LLM call, and Outlets are all handled within this block
        try:
            # Short-circuit for MoA to provide instant feedback
            if snapshot.get("form_data", {}).get("metadata", {}).get("task") == str(TASKS.MOA_RESPONSE_GENERATION):
                emitter = get_event_emitter(snapshot["metadata"])
                if emitter:
                    await emitter({
                        "type": "status",
                        "data": {"action": "agent_mixing", "status": "in_progress", "content": "Mixing agent responses..."},
                    })

            # 3. Process Payload (Inlets)
            from open_webui.utils.middleware import process_chat_payload, process_chat_response
            
            form_data, metadata, events = await process_chat_payload(
                mock_request, snapshot["form_data"], user, metadata, snapshot["model"]
            )

            # 4. Trigger LLM Call
            # Note: We set orchestrate=False here to perform actual generation
            response = await generate_chat_completion(
                request=mock_request,
                form_data=form_data,
                user=user,
                orchestrate=False
            )

            # 5. Handle Response (Outlet, Persistence, Streaming to SIO)
            # tasks come from form_data (background_tasks)
            tasks = snapshot.get("form_data", {}).get("background_tasks")
            
            streaming_response = await process_chat_response(
                mock_request, response, form_data, user, metadata, snapshot["model"], events, tasks
            )

            # If it's a StreamingResponse, we must iterate over it to execute the logic
            if isinstance(streaming_response, StreamingResponse):
                async for chunk in streaming_response.body_iterator:
                    # Logic is handled inside the generator (emits SIO, saves to DB)
                    pass
                if streaming_response.background:
                    await streaming_response.background()

            log.info(f"Server-side orchestration completed for chat {chat_id}")

        except Exception as e:
            log.exception(f"Error in server-side orchestration: {e}")
            
            error_message = "An unexpected error occurred. Please try again."
            if snapshot.get("form_data", {}).get("metadata", {}).get("task") == str(TASKS.MOA_RESPONSE_GENERATION):
                error_message = "One of the agents failed to respond. Please try again."

            event_emitter = get_event_emitter(metadata)
            if event_emitter:
                await event_emitter({"type": "chat:message:error", "data": {"error": {"content": error_message}}})
            
            if chat_id and message_id:
                Chats.upsert_message_to_chat_by_id_and_message_id(
                    chat_id, message_id, {"error": {"content": str(e)}, "done": True}
                )

    @staticmethod
    async def periodic_zombie_cleanup(app):
        """
        Periodically checks for messages stuck in 'processing' state without an active task.
        """
        from open_webui.tasks import list_tasks
        from open_webui.models.chats import Chats
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            try:
                log.debug("Running periodic zombie cleanup...")
                active_task_ids = await list_tasks(getattr(app.state, "redis", None))
                
                processing_chat_ids = Chats.get_processing_chat_ids()
                for chat_id in processing_chat_ids:
                    from open_webui.tasks import list_task_ids_by_item_id
                    chat_tasks = await list_task_ids_by_item_id(getattr(app.state, "redis", None), chat_id)
                    
                    if not chat_tasks:
                        log.warning(f"Found zombie chat {chat_id}. Marking messages as interrupted.")
                        messages = Chats.get_messages_by_chat_id(chat_id)
                        if messages:
                            for message in messages:
                                if message.get("role") == "assistant" and message.get("done") is False:
                                    Chats.mark_message_as_interrupted(chat_id, message.get("id"))
                
            except Exception as e:
                log.error(f"Error in zombie cleanup: {e}")

async def generate_direct_chat_completion(
    request: Request,
    form_data: dict,
    user: Any,
    models: dict,
):
    log.info("generate_direct_chat_completion")

    metadata = form_data.pop("metadata", {})

    user_id = metadata.get("user_id")
    session_id = metadata.get("session_id")
    request_id = str(uuid.uuid4())  # Generate a unique request ID

    event_caller = get_event_call(metadata)

    channel = f"{user_id}:{session_id}:{request_id}"
    logging.info(f"WebSocket channel: {channel}")

    if form_data.get("stream"):
        q = asyncio.Queue()

        async def message_listener(sid, data):
            """
            Handle received socket messages and push them into the queue.
            """
            await q.put(data)

        # Register the listener
        sio.on(channel, message_listener)

        # Start processing chat completion in background
        res = await event_caller(
            {
                "type": "request:chat:completion",
                "data": {
                    "form_data": form_data,
                    "model": models[form_data["model"]],
                    "channel": channel,
                    "session_id": session_id,
                },
            }
        )

        log.info(f"res: {res}")

        if res.get("status", False):
            # Define a generator to stream responses
            async def event_generator():
                nonlocal q
                try:
                    while True:
                        data = await q.get()  # Wait for new messages
                        if isinstance(data, dict):
                            if "done" in data and data["done"]:
                                break  # Stop streaming when 'done' is received

                            yield f"data: {json.dumps(data)}\n\n"
                        elif isinstance(data, str):
                            if "data:" in data:
                                yield f"{data}\n\n"
                            else:
                                yield f"data: {data}\n\n"
                except Exception as e:
                    log.debug(f"Error in event generator: {e}")
                    pass

            # Define a background task to run the event generator
            async def background():
                try:
                    del sio.handlers["/"][channel]
                except Exception as e:
                    pass

            # Return the streaming response
            return StreamingResponse(
                event_generator(), media_type="text/event-stream", background=background
            )
        else:
            raise Exception(str(res))
    else:
        res = await event_caller(
            {
                "type": "request:chat:completion",
                "data": {
                    "form_data": form_data,
                    "model": models[form_data["model"]],
                    "channel": channel,
                    "session_id": session_id,
                },
            }
        )

        if "error" in res and res["error"]:
            raise Exception(res["error"])

        return res


async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user: Any,
    bypass_filter: bool = False,
    bypass_system_prompt: bool = False,
    orchestrate: bool = True,
):
    log.debug(f"generate_chat_completion: {form_data}")

    metadata = form_data.get("metadata", {})
    if not metadata and hasattr(request.state, "metadata"):
        metadata = request.state.metadata

    if orchestrate and ENABLE_SERVER_SIDE_ORCHESTRATION:
        chat_id = metadata.get("chat_id")
        if chat_id and not chat_id.startswith("local:"):
            from open_webui.tasks import list_task_ids_by_item_id, create_task
            # Check if there is already an active task for this chat
            active_tasks = await list_task_ids_by_item_id(
                getattr(request.app.state, "redis", None),
                chat_id
            )
            if active_tasks:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Generation already in progress for this chat."
                )

            models = getattr(request.app.state, "MODELS", {})
            model_id = form_data.get("model")
            model = models.get(model_id) if models else None

            snapshot = ServerSideChatManager.snapshot_context(request, form_data, user, metadata, model)
            task_id, _ = await create_task(
                getattr(request.app.state, "redis", None),
                ServerSideChatManager.orchestrate(snapshot, request.app.state),
                id=chat_id
            )
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "status": "processing",
                    "chat_id": chat_id,
                    "message_id": metadata.get("message_id"),
                    "task_id": task_id
                }
            )

    # If we are here, it means either:
    # 1. Orchestration is disabled
    # 2. It's a local/temp chat
    # 3. We are INSIDE the orchestrated background task (orchestrate=False)
    
    if not orchestrate:
        # Direct dispatch (Old behavior of generate_chat_completion)
        return await _generate_chat_completion_direct(
            request, form_data, user, bypass_filter, bypass_system_prompt
        )
    else:
        # Standard flow with inlets/outlets
        return await _generate_chat_completion_with_middleware(
            request, form_data, user, metadata
        )

async def _generate_chat_completion_with_middleware(request, form_data, user, metadata):
    from open_webui.utils.middleware import process_chat_payload, process_chat_response
    
    # We need models for pipeline/filters
    models = getattr(request.app.state, "MODELS", {})
    model_id = form_data.get("model")
    model = models.get(model_id) if models else None

    try:
        form_data, metadata, events = await process_chat_payload(
            request, form_data, user, metadata, model
        )

        response = await _generate_chat_completion_direct(request, form_data, user)
        
        # background_tasks might be in form_data or metadata
        tasks = form_data.get("background_tasks")
        
        return await process_chat_response(
            request, response, form_data, user, metadata, model, events, tasks
        )
    except asyncio.CancelledError:
        log.info("Chat processing was cancelled")
        try:
            event_emitter = get_event_emitter(metadata)
            if event_emitter:
                await asyncio.shield(
                    event_emitter(
                        {"type": "chat:tasks:cancel"},
                    )
                )
        except Exception:
            pass
        finally:
            raise
    except Exception as e:
        log.exception(f"Error in chat completion middleware: {e}")
        if metadata.get("chat_id") and metadata.get("message_id"):
            try:
                if not metadata["chat_id"].startswith("local:"):
                    Chats.upsert_message_to_chat_by_id_and_message_id(
                        metadata["chat_id"],
                        metadata["message_id"],
                        {
                            "error": {"content": str(e)},
                        },
                    )

                event_emitter = get_event_emitter(metadata)
                if event_emitter:
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def _generate_chat_completion_direct(
    request: Request,
    form_data: dict,
    user: Any,
    bypass_filter: bool = False,
    bypass_system_prompt: bool = False,
):
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    if hasattr(request.state, "metadata"):
        if "metadata" not in form_data:
            form_data["metadata"] = request.state.metadata
        else:
            form_data["metadata"] = {
                **form_data["metadata"],
                **request.state.metadata,
            }

    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        models = {
            request.state.model["id"]: request.state.model,
        }
        log.debug(f"direct connection to model: {models}")
    else:
        models = getattr(request.app.state, "MODELS", {})

    model_id = form_data["model"]
    if model_id not in models:
        raise Exception("Model not found")

    model = models[model_id]

    if getattr(request.state, "direct", False):
        return await generate_direct_chat_completion(
            request, form_data, user=user, models=models
        )
    else:
        # Check if user has access to the model
        if not bypass_filter and user.role == "user":
            try:
                check_model_access(user, model)
            except Exception as e:
                raise e

        if model.get("owned_by") == "arena":
            model_ids = model.get("info", {}).get("meta", {}).get("model_ids")
            filter_mode = model.get("info", {}).get("meta", {}).get("filter_mode")
            if model_ids and filter_mode == "exclude":
                model_ids = [
                    model["id"]
                    for model in list(request.app.state.MODELS.values())
                    if model.get("owned_by") != "arena" and model["id"] not in model_ids
                ]

            selected_model_id = None
            if isinstance(model_ids, list) and model_ids:
                selected_model_id = random.choice(model_ids)
            else:
                model_ids = [
                    model["id"]
                    for model in list(request.app.state.MODELS.values())
                    if model.get("owned_by") != "arena"
                ]
                selected_model_id = random.choice(model_ids)

            form_data["model"] = selected_model_id

            if form_data.get("stream") == True:

                async def stream_wrapper(stream):
                    yield f"data: {json.dumps({'selected_model_id': selected_model_id})}\n\n"
                    async for chunk in stream:
                        yield chunk

                response = await generate_chat_completion(
                    request,
                    form_data,
                    user,
                    bypass_filter=True,
                    bypass_system_prompt=bypass_system_prompt,
                    orchestrate=False
                )
                return StreamingResponse(
                    stream_wrapper(response.body_iterator),
                    media_type="text/event-stream",
                    background=response.background,
                )
            else:
                return {
                    **(
                        await generate_chat_completion(
                            request,
                            form_data,
                            user,
                            bypass_filter=True,
                            bypass_system_prompt=bypass_system_prompt,
                            orchestrate=False
                        )
                    ),
                    "selected_model_id": selected_model_id,
                }

        if model.get("pipe"):
            # Below does not require bypass_filter because this is the only route the uses this function and it is already bypassing the filter
            return await generate_function_chat_completion(
                request, form_data, user=user, models=models
            )
        if model.get("owned_by") == "ollama":
            # Using /ollama/api/chat endpoint
            form_data = convert_payload_openai_to_ollama(form_data)
            response = await generate_ollama_chat_completion(
                request=request,
                form_data=form_data,
                user=user,
                bypass_filter=bypass_filter,
                bypass_system_prompt=bypass_system_prompt,
            )
            if form_data.get("stream"):
                response.headers["content-type"] = "text/event-stream"
                return StreamingResponse(
                    convert_streaming_response_ollama_to_openai(response),
                    headers=dict(response.headers),
                    background=response.background,
                )
            else:
                return convert_response_ollama_to_openai(response)
        else:
            return await generate_openai_chat_completion(
                request=request,
                form_data=form_data,
                user=user,
                bypass_filter=bypass_filter,
                bypass_system_prompt=bypass_system_prompt,
            )


chat_completion = generate_chat_completion


async def chat_completed(request: Request, form_data: dict, user: Any):
    if not request.app.state.MODELS:
        await get_all_models(request, user=user)

    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        models = {
            request.state.model["id"]: request.state.model,
        }
    else:
        models = request.app.state.MODELS

    data = form_data
    model_id = data["model"]
    if model_id not in models:
        raise Exception("Model not found")

    model = models[model_id]

    try:
        data = await process_pipeline_outlet_filter(request, data, user, models)
    except Exception as e:
        raise Exception(f"Error: {e}")

    metadata = {
        "chat_id": data["chat_id"],
        "message_id": data["id"],
        "filter_ids": data.get("filter_ids", []),
        "session_id": data["session_id"],
        "user_id": user.id,
    }

    extra_params = {
        "__event_emitter__": get_event_emitter(metadata),
        "__event_call__": get_event_call(metadata),
        "__user__": user.model_dump() if isinstance(user, UserModel) else {},
        "__metadata__": metadata,
        "__request__": request,
        "__model__": model,
    }

    try:
        filter_functions = [
            Functions.get_function_by_id(filter_id)
            for filter_id in get_sorted_filter_ids(
                request, model, metadata.get("filter_ids", [])
            )
        ]

        result, _ = await process_filter_functions(
            request=request,
            filter_functions=filter_functions,
            filter_type="outlet",
            form_data=data,
            extra_params=extra_params,
        )
        return result
    except Exception as e:
        raise Exception(f"Error: {e}")


async def chat_action(request: Request, action_id: str, form_data: dict, user: Any):
    if "." in action_id:
        action_id, sub_action_id = action_id.split(".")
    else:
        sub_action_id = None

    action = Functions.get_function_by_id(action_id)
    if not action:
        raise Exception(f"Action not found: {action_id}")

    if not request.app.state.MODELS:
        await get_all_models(request, user=user)

    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        models = {
            request.state.model["id"]: request.state.model,
        }
    else:
        models = request.app.state.MODELS

    data = form_data
    model_id = data["model"]

    if model_id not in models:
        raise Exception("Model not found")
    model = models[model_id]

    __event_emitter__ = get_event_emitter(
        {
            "chat_id": data["chat_id"],
            "message_id": data["id"],
            "session_id": data["session_id"],
            "user_id": user.id,
        }
    )
    __event_call__ = get_event_call(
        {
            "chat_id": data["chat_id"],
            "message_id": data["id"],
            "session_id": data["session_id"],
            "user_id": user.id,
        }
    )

    function_module, _, _ = get_function_module_from_cache(request, action_id)

    if hasattr(function_module, "valves") and hasattr(function_module, "Valves"):
        valves = Functions.get_function_valves_by_id(action_id)
        function_module.valves = function_module.Valves(**(valves if valves else {}))

    if hasattr(function_module, "action"):
        try:
            action = function_module.action

            # Get the signature of the function
            sig = inspect.signature(action)
            params = {"body": data}

            # Extra parameters to be passed to the function
            extra_params = {
                "__model__": model,
                "__id__": sub_action_id if sub_action_id is not None else action_id,
                "__event_emitter__": __event_emitter__,
                "__event_call__": __event_call__,
                "__request__": request,
            }

            # Add extra params in contained in function signature
            for key, value in extra_params.items():
                if key in sig.parameters:
                    params[key] = value

            if "__user__" in sig.parameters:
                __user__ = user.model_dump() if isinstance(user, UserModel) else {}

                try:
                    if hasattr(function_module, "UserValves"):
                        __user__["valves"] = function_module.UserValves(
                            **Functions.get_user_valves_by_id_and_user_id(
                                action_id, user.id
                            )
                        )
                except Exception as e:
                    log.exception(f"Failed to get user values: {e}")

                params = {**params, "__user__": __user__}

            if inspect.iscoroutinefunction(action):
                data = await action(**params)
            else:
                data = action(**params)

        except Exception as e:
            raise Exception(f"Error: {e}")

    return data

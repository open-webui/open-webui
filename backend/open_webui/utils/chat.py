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

from fastapi import Request, status
from starlette.responses import Response, StreamingResponse, JSONResponse


from open_webui.models.users import UserModel, Users
from open_webui.models.memories import Memories
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

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

from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL, BYPASS_MODEL_ACCESS_CONTROL


logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


async def get_memory_topics(request: Request, form_data: dict, user: Any, chat_completion_func) -> list[str]:
    user_message = ""
    if len(form_data["messages"]) > 0:
        # Get the last user message
        for message in reversed(form_data["messages"]):
            if message['role'] == 'user':
                user_message = message['content']
                break

    if not user_message:
        return []

    prompt = f"Extract the main topics from the following user query. Return the topics as a comma-separated list. For example, if the query is 'What is my budget for the hiking trip?', you should return 'budget, hiking trip'.\n\nUser query: '{user_message}'"

    topic_extraction_payload = {
        "model": form_data.get("model"),
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "features": {"memory": False},  # Avoid recursion
    }

    try:
        response = await chat_completion_func(
            request,
            topic_extraction_payload,
            user,
            bypass_filter=True,
        )

        content = response['choices'][0]['message']['content']
        topics = [topic.strip() for topic in content.split(',')]
        return topics
    except Exception as e:
        log.error(f"Error extracting memory topics: {e}")
        return []


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
    enable_memory_retrieval: bool = True,
):
    if enable_memory_retrieval and form_data.get("features", {}).get("memory", False):
        log.info("Memory feature enabled, retrieving relevant memories.")

        topics = await get_memory_topics(
            request, form_data, user, generate_chat_completion
        )
        log.info(f"Extracted topics: {topics}")

        if topics:
            all_results = []
            embedding_function = getattr(request.app.state, "EMBEDDING_FUNCTION", None)

            if embedding_function:
                for topic in topics:
                    try:
                        embedding = embedding_function(topic, user=user)
                        results = VECTOR_DB_CLIENT.search(
                            collection_name=f"user-memory-{user.id}",
                            vectors=[embedding],
                            limit=3,
                        )
                        all_results.extend(results)
                    except Exception as e:
                        log.error(f"Error during memory search for topic '{topic}': {e}")

            if all_results:
                unique_memories = {item["id"]: item for item in all_results}.values()
                sorted_memories = sorted(unique_memories, key=lambda x: x["score"], reverse=True)
                top_memories = sorted_memories[:5]

                if top_memories:
                    memory_context = "Here are some relevant memories from our past conversations:\n"
                    for mem in top_memories:
                        memory_context += f"- {mem['text']}\n"
                    
                    if form_data["messages"] and form_data["messages"][0]["role"] == "system":
                        form_data["messages"][0]["content"] += f"\n{memory_context}"
                    else:
                        form_data["messages"].insert(0, {"role": "system", "content": memory_context})

    log.debug(f"generate_chat_completion: {form_data}")
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
        models = request.app.state.MODELS

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
                    request, form_data, user, bypass_filter=True
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
                            request, form_data, user, bypass_filter=True
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
            )


chat_completion = generate_chat_completion


async def extract_memories_from_conversation(
    request: Request,
    form_data: dict,
    user: Any,
    chat_completion_func,
) -> list[str]:
    # Extract user message and all subsequent assistant responses
    conversation_history = ""
    user_message_content = ""
    assistant_responses = []

    # Find the last user message
    for i in range(len(form_data["messages"]) - 1, -1, -1):
        if form_data["messages"][i]["role"] == "user":
            user_message_content = form_data["messages"][i]["content"]
            # Get all assistant messages that follow
            for j in range(i + 1, len(form_data["messages"])):
                if form_data["messages"][j]["role"] == "assistant":
                    assistant_responses.append(form_data["messages"][j]["content"])
            break

    if not user_message_content or not assistant_responses:
        return []

    conversation_history = f"User: {user_message_content}\n"
    for i, response in enumerate(assistant_responses):
        conversation_history += f"Assistant {i+1}: {response}\n"

    prompt = f"Analyze the following conversation and identify any key facts, user preferences, or important pieces of information that should be saved as a memory. Return the memories as a JSON array of strings. For example, if the user says 'I prefer concise responses', you should return '[\"User prefers concise responses.\"]'. If nothing new or important is mentioned, return an empty array.\n\nConversation:\n{conversation_history}"

    memory_extraction_payload = {
        "model": form_data.get("model"),
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }

    try:
        response = await chat_completion_func(
            request,
            memory_extraction_payload,
            user,
            bypass_filter=True,
            enable_memory_retrieval=False,  # Disable memory retrieval for this call
        )

        if isinstance(response, JSONResponse):
            try:
                error_content = response.body.decode("utf-8")
                log.error(
                    f"Error from chat completion for memory extraction: {error_content}"
                )
            except Exception:
                log.error(
                    f"Error from chat completion for memory extraction: status_code={response.status_code}"
                )
            return []

        content = response["choices"][0]["message"]["content"]

        # Find the JSON array in the response
        start_index = content.find('[')
        end_index = content.rfind(']')
        if start_index != -1 and end_index != -1:
            json_str = content[start_index:end_index+1]
            memories = json.loads(json_str)
            return memories
        else:
            return []
    except Exception as e:
        log.error(f"Error extracting memories from conversation: {e}")
        return []


async def chat_completed(request: Request, form_data: dict, user: Any):
    # Automatic memory creation
    user_with_settings = Users.get_user_by_id(user.id)
    if (
        user_with_settings
        and user_with_settings.settings
        and user_with_settings.settings.ui.get("automaticMemory", False)
    ):
        log.info("Automatic memory creation enabled.")
        memories = await extract_memories_from_conversation(
            request, form_data, user, chat_completion
        )
        if memories:
            log.info(f"Adding {len(memories)} new memories.")
            embedding_function = getattr(request.app.state, "EMBEDDING_FUNCTION", None)
            for memory_content in memories:
                new_memory = Memories.insert_new_memory(user.id, memory_content)
                if new_memory and embedding_function:
                    try:
                        VECTOR_DB_CLIENT.upsert(
                            collection_name=f"user-memory-{user.id}",
                            items=[
                                {
                                    "id": new_memory.id,
                                    "text": new_memory.content,
                                    "vector": embedding_function(
                                        new_memory.content, user=user
                                    ),
                                    "metadata": {"created_at": new_memory.created_at},
                                }
                            ],
                        )
                    except Exception as e:
                        log.error(f"Error upserting new memory to vector DB: {e}")

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
        return Exception(f"Error: {e}")

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
        return Exception(f"Error: {e}")


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
            return Exception(f"Error: {e}")

    return data

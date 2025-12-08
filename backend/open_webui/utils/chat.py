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
from open_webui.models.user_model_credentials import UserModelCredentials


from open_webui.utils.plugin import (
    load_function_module_by_id,
    get_function_module_from_cache,
)
from open_webui.utils.models import get_all_models, check_model_access, transform_user_model_if_needed
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
    chatting_completion: bool = False
):
    """
    聊天完成生成函数 - 根据模型类型分发到不同的底层 API 处理器

    这是聊天完成的核心路由函数，负责：
    1. 验证模型存在性和用户权限
    2. 处理 Direct 模式（直连外部 API）
    3. 处理 Arena 模式（随机选择模型进行对比）
    4. 根据模型类型分发到对应处理器：
       - Pipe: Pipeline 插件函数
       - Ollama: Ollama 本地模型
       - OpenAI: OpenAI 兼容 API (含 Claude, Gemini 等)

    Args:
        request: FastAPI Request 对象
        form_data: OpenAI 格式的聊天请求数据
        user: 用户对象
        bypass_filter: 是否绕过权限和 Pipeline Filter 检查

    Returns:
        - 流式: StreamingResponse (SSE 格式)
        - 非流式: dict (OpenAI 兼容格式)

    Raises:
        Exception: 模型不存在或无权限访问
    """
    log.debug(f"generate_chat_completion: {form_data}")

    # === 1. 权限检查配置 ===
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True  # 全局配置：绕过所有权限检查

    # === 2. 合并元数据 ===
    # 从 request.state.metadata 获取上游传递的元数据（chat_id, user_id 等）
    if hasattr(request.state, "metadata"):
        if "metadata" not in form_data:
            form_data["metadata"] = request.state.metadata
        else:
            # 合并，request.state.metadata 优先级更高
            form_data["metadata"] = {
                **form_data["metadata"],
                **request.state.metadata,
            }

    # === 3. 确定模型列表来源 ===
    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        # Direct 模式：用户直接提供外部 API 配置（如 OpenAI API Key）
        models = {
            request.state.model["id"]: request.state.model,
        }
        log.debug(f"direct connection to model: {models}")
    else:
        # 标准模式：使用平台内置模型列表
        models = request.app.state.MODELS

    # === 4. 验证模型存在性 ===
    model_id = form_data["model"]

    # 私有模型直连：如果是用户私有模型，使用 credential_id 注入 direct 配置
    if form_data.get("is_user_model") and form_data.get("model_item", {}).get("credential_id"):
        cred = UserModelCredentials.get_credential_by_id_and_user_id(
            form_data["model_item"]["credential_id"], user.id
        )
        if not cred:
            raise Exception("User model credential not found")
        request.state.direct = True
        request.state.model = {
            "id": cred.model_id,
            "name": cred.name or cred.model_id,
            "base_url": cred.base_url,
            "api_key": cred.api_key,
        }
        models = {request.state.model["id"]: request.state.model}
        model_id = cred.model_id
    if model_id not in models:
        raise Exception("Model not found")

    model = models[model_id]

    # === 5. Direct 模式分支：直连外部 API ===
    # 原始逻辑是调用 generate_direct_chat_completion，但该函数实际上是一个无法处理 API 请求的“断头路”。
    # 经过调试发现，真正能将请求发送到上游 OpenAI 兼容 API 的是 generate_openai_chat_completion。
    # 因此，当识别为直连模式时（例如用户私有模型），将请求直接导向 generate_openai_chat_completion。
    if getattr(request.state, "direct", False):
        return await generate_openai_chat_completion(
            request=request,
            form_data=form_data,
            user=user,
        )
    else:
        # === 6. 标准模式：检查用户权限 ===
        if not bypass_filter and user.role == "user":
            try:
                check_model_access(user, model)  # 验证 RBAC 权限
            except Exception as e:
                raise e

        # === 7. Arena 模式：随机选择模型进行盲测对比 ===
        if False:
            if model.get("owned_by") == "arena":
                # 获取候选模型列表
                model_ids = model.get("info", {}).get("meta", {}).get("model_ids")
                filter_mode = model.get("info", {}).get("meta", {}).get("filter_mode")

                # 如果是排除模式，反选模型列表
                if model_ids and filter_mode == "exclude":
                    model_ids = [
                        model["id"]
                        for model in list(request.app.state.MODELS.values())
                        if model.get("owned_by") != "arena" and model["id"] not in model_ids
                    ]

                # 随机选择一个模型
                selected_model_id = None
                if isinstance(model_ids, list) and model_ids:
                    selected_model_id = random.choice(model_ids)
                else:
                    # 未指定则从所有非 Arena 模型中随机选择
                    model_ids = [
                        model["id"]
                        for model in list(request.app.state.MODELS.values())
                        if model.get("owned_by") != "arena"
                    ]
                    selected_model_id = random.choice(model_ids)

                # 替换模型 ID
                form_data["model"] = selected_model_id

                # 流式响应：在首个 chunk 中注入 selected_model_id
                if form_data.get("stream") == True:

                    async def stream_wrapper(stream):
                        """在流式响应前添加选中的模型 ID"""
                        yield f"data: {json.dumps({'selected_model_id': selected_model_id})}\n\n"
                        async for chunk in stream:
                            yield chunk

                    # 递归调用自身，绕过 Arena 逻辑
                    response = await generate_chat_completion(
                        request, form_data, user, bypass_filter=True
                    )
                    return StreamingResponse(
                        stream_wrapper(response.body_iterator),
                        media_type="text/event-stream",
                        background=response.background,
                    )
                else:
                    # 非流式响应：直接在结果中添加 selected_model_id
                    return {
                        **(
                            await generate_chat_completion(
                                request, form_data, user, bypass_filter=True
                            )
                        ),
                        "selected_model_id": selected_model_id,
                    }

        # === 8. Pipeline 模式：调用自定义 Python 函数 ===
        if False:
            if model.get("pipe"):
                return await generate_function_chat_completion(
                    request, form_data, user=user, models=models
                )

        # === 9. Ollama 模式：调用本地 Ollama 服务 ===
        if False:
            if model.get("owned_by") == "ollama":
                # 转换 OpenAI 格式 → Ollama 格式
                form_data = convert_payload_openai_to_ollama(form_data)
                response = await generate_ollama_chat_completion(
                    request=request,
                    form_data=form_data,
                    user=user,
                    bypass_filter=bypass_filter,
                )

                # 流式响应：转换 Ollama SSE → OpenAI SSE
                if form_data.get("stream"):
                    response.headers["content-type"] = "text/event-stream"
                    return StreamingResponse(
                        convert_streaming_response_ollama_to_openai(response),
                        headers=dict(response.headers),
                        background=response.background,
                    )
                else:
                    # 非流式响应：转换 Ollama JSON → OpenAI JSON
                    return convert_response_ollama_to_openai(response)

        # === 10. OpenAI 兼容模式：调用 OpenAI API 或兼容服务 ===
        # >>>
        return await generate_openai_chat_completion(
            request=request,
            form_data=form_data,
            user=user,
            bypass_filter=bypass_filter,
            chatting_completion = chatting_completion
        )


chat_completion = generate_chat_completion


async def chat_completed(request: Request, form_data: dict, user: Any):
    if not request.app.state.MODELS:
        await get_all_models(request, user=user)

    form_data = await transform_user_model_if_needed(form_data, user)
    model_item = form_data.get("model_item", {})

    if model_item.get("direct", False):
        request.state.direct = True
        request.state.model = model_item

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

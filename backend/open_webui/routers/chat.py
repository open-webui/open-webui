from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

router = APIRouter()


@app.post("/api/chat/completions")
async def generate_chat_completions(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: bool = False,
):
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    model_list = request.state.models
    models = {model["id"]: model for model in model_list}

    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    model = models[model_id]

    # Check if user has access to the model
    if not bypass_filter and user.role == "user":
        if model.get("arena"):
            if not has_access(
                user.id,
                type="read",
                access_control=model.get("info", {})
                .get("meta", {})
                .get("access_control", {}),
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Model not found",
                )
        else:
            model_info = Models.get_model_by_id(model_id)
            if not model_info:
                raise HTTPException(
                    status_code=404,
                    detail="Model not found",
                )
            elif not (
                user.id == model_info.user_id
                or has_access(
                    user.id, type="read", access_control=model_info.access_control
                )
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Model not found",
                )

    if model["owned_by"] == "arena":
        model_ids = model.get("info", {}).get("meta", {}).get("model_ids")
        filter_mode = model.get("info", {}).get("meta", {}).get("filter_mode")
        if model_ids and filter_mode == "exclude":
            model_ids = [
                model["id"]
                for model in await get_all_models()
                if model.get("owned_by") != "arena" and model["id"] not in model_ids
            ]

        selected_model_id = None
        if isinstance(model_ids, list) and model_ids:
            selected_model_id = random.choice(model_ids)
        else:
            model_ids = [
                model["id"]
                for model in await get_all_models()
                if model.get("owned_by") != "arena"
            ]
            selected_model_id = random.choice(model_ids)

        form_data["model"] = selected_model_id

        if form_data.get("stream") == True:

            async def stream_wrapper(stream):
                yield f"data: {json.dumps({'selected_model_id': selected_model_id})}\n\n"
                async for chunk in stream:
                    yield chunk

            response = await generate_chat_completions(
                form_data, user, bypass_filter=True
            )
            return StreamingResponse(
                stream_wrapper(response.body_iterator), media_type="text/event-stream"
            )
        else:
            return {
                **(
                    await generate_chat_completions(form_data, user, bypass_filter=True)
                ),
                "selected_model_id": selected_model_id,
            }

    if model.get("pipe"):
        # Below does not require bypass_filter because this is the only route the uses this function and it is already bypassing the filter
        return await generate_function_chat_completion(
            form_data, user=user, models=models
        )
    if model["owned_by"] == "ollama":
        # Using /ollama/api/chat endpoint
        form_data = convert_payload_openai_to_ollama(form_data)
        form_data = GenerateChatCompletionForm(**form_data)
        response = await generate_ollama_chat_completion(
            form_data=form_data, user=user, bypass_filter=bypass_filter
        )
        if form_data.stream:
            response.headers["content-type"] = "text/event-stream"
            return StreamingResponse(
                convert_streaming_response_ollama_to_openai(response),
                headers=dict(response.headers),
            )
        else:
            return convert_response_ollama_to_openai(response)
    else:
        return await generate_openai_chat_completion(
            form_data, user=user, bypass_filter=bypass_filter
        )


@app.post("/api/chat/completed")
async def chat_completed(form_data: dict, user=Depends(get_verified_user)):
    model_list = await get_all_models()
    models = {model["id"]: model for model in model_list}

    data = form_data
    model_id = data["model"]
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    model = models[model_id]
    sorted_filters = get_sorted_filters(model_id, models)
    if "pipeline" in model:
        sorted_filters = [model] + sorted_filters

    for filter in sorted_filters:
        r = None
        try:
            urlIdx = filter["urlIdx"]

            url = openai_app.state.config.OPENAI_API_BASE_URLS[urlIdx]
            key = openai_app.state.config.OPENAI_API_KEYS[urlIdx]

            if key != "":
                headers = {"Authorization": f"Bearer {key}"}
                r = requests.post(
                    f"{url}/{filter['id']}/filter/outlet",
                    headers=headers,
                    json={
                        "user": {
                            "id": user.id,
                            "name": user.name,
                            "email": user.email,
                            "role": user.role,
                        },
                        "body": data,
                    },
                )

                r.raise_for_status()
                data = r.json()
        except Exception as e:
            # Handle connection error here
            print(f"Connection error: {e}")

            if r is not None:
                try:
                    res = r.json()
                    if "detail" in res:
                        return JSONResponse(
                            status_code=r.status_code,
                            content=res,
                        )
                except Exception:
                    pass

            else:
                pass

    __event_emitter__ = get_event_emitter(
        {
            "chat_id": data["chat_id"],
            "message_id": data["id"],
            "session_id": data["session_id"],
        }
    )

    __event_call__ = get_event_call(
        {
            "chat_id": data["chat_id"],
            "message_id": data["id"],
            "session_id": data["session_id"],
        }
    )

    def get_priority(function_id):
        function = Functions.get_function_by_id(function_id)
        if function is not None and hasattr(function, "valves"):
            # TODO: Fix FunctionModel to include vavles
            return (function.valves if function.valves else {}).get("priority", 0)
        return 0

    filter_ids = [function.id for function in Functions.get_global_filter_functions()]
    if "info" in model and "meta" in model["info"]:
        filter_ids.extend(model["info"]["meta"].get("filterIds", []))
        filter_ids = list(set(filter_ids))

    enabled_filter_ids = [
        function.id
        for function in Functions.get_functions_by_type("filter", active_only=True)
    ]
    filter_ids = [
        filter_id for filter_id in filter_ids if filter_id in enabled_filter_ids
    ]

    # Sort filter_ids by priority, using the get_priority function
    filter_ids.sort(key=get_priority)

    for filter_id in filter_ids:
        filter = Functions.get_function_by_id(filter_id)
        if not filter:
            continue

        if filter_id in webui_app.state.FUNCTIONS:
            function_module = webui_app.state.FUNCTIONS[filter_id]
        else:
            function_module, _, _ = load_function_module_by_id(filter_id)
            webui_app.state.FUNCTIONS[filter_id] = function_module

        if hasattr(function_module, "valves") and hasattr(function_module, "Valves"):
            valves = Functions.get_function_valves_by_id(filter_id)
            function_module.valves = function_module.Valves(
                **(valves if valves else {})
            )

        if not hasattr(function_module, "outlet"):
            continue
        try:
            outlet = function_module.outlet

            # Get the signature of the function
            sig = inspect.signature(outlet)
            params = {"body": data}

            # Extra parameters to be passed to the function
            extra_params = {
                "__model__": model,
                "__id__": filter_id,
                "__event_emitter__": __event_emitter__,
                "__event_call__": __event_call__,
            }

            # Add extra params in contained in function signature
            for key, value in extra_params.items():
                if key in sig.parameters:
                    params[key] = value

            if "__user__" in sig.parameters:
                __user__ = {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                }

                try:
                    if hasattr(function_module, "UserValves"):
                        __user__["valves"] = function_module.UserValves(
                            **Functions.get_user_valves_by_id_and_user_id(
                                filter_id, user.id
                            )
                        )
                except Exception as e:
                    print(e)

                params = {**params, "__user__": __user__}

            if inspect.iscoroutinefunction(outlet):
                data = await outlet(**params)
            else:
                data = outlet(**params)

        except Exception as e:
            print(f"Error: {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(e)},
            )

    return data


@app.post("/api/chat/actions/{action_id}")
async def chat_action(action_id: str, form_data: dict, user=Depends(get_verified_user)):
    if "." in action_id:
        action_id, sub_action_id = action_id.split(".")
    else:
        sub_action_id = None

    action = Functions.get_function_by_id(action_id)
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )

    model_list = await get_all_models()
    models = {model["id"]: model for model in model_list}

    data = form_data
    model_id = data["model"]

    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )
    model = models[model_id]

    __event_emitter__ = get_event_emitter(
        {
            "chat_id": data["chat_id"],
            "message_id": data["id"],
            "session_id": data["session_id"],
        }
    )
    __event_call__ = get_event_call(
        {
            "chat_id": data["chat_id"],
            "message_id": data["id"],
            "session_id": data["session_id"],
        }
    )

    if action_id in webui_app.state.FUNCTIONS:
        function_module = webui_app.state.FUNCTIONS[action_id]
    else:
        function_module, _, _ = load_function_module_by_id(action_id)
        webui_app.state.FUNCTIONS[action_id] = function_module

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
            }

            # Add extra params in contained in function signature
            for key, value in extra_params.items():
                if key in sig.parameters:
                    params[key] = value

            if "__user__" in sig.parameters:
                __user__ = {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                }

                try:
                    if hasattr(function_module, "UserValves"):
                        __user__["valves"] = function_module.UserValves(
                            **Functions.get_user_valves_by_id_and_user_id(
                                action_id, user.id
                            )
                        )
                except Exception as e:
                    print(e)

                params = {**params, "__user__": __user__}

            if inspect.iscoroutinefunction(action):
                data = await action(**params)
            else:
                data = action(**params)

        except Exception as e:
            print(f"Error: {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(e)},
            )

    return data

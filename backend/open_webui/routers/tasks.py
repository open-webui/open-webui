from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from fastapi.responses import JSONResponse, RedirectResponse

from pydantic import BaseModel
from typing import Optional
import logging
import re

from open_webui.utils.chat import generate_chat_completion
from open_webui.utils.task import (
    title_generation_template,
    query_generation_template,
    image_prompt_generation_template,
    autocomplete_generation_template,
    tags_generation_template,
    emoji_generation_template,
    moa_response_generation_template,
)
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.constants import TASKS

from open_webui.routers.pipelines import process_pipeline_inlet_filter
from open_webui.utils.filter import (
    get_sorted_filter_ids,
    process_filter_functions,
)
from open_webui.utils.task import get_task_model_id

from open_webui.config import (
    DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_TAGS_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_QUERY_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_EMOJI_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_MOA_GENERATION_PROMPT_TEMPLATE,
)
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.models import Models
from open_webui.utils.access_control import has_access
from open_webui.utils.workspace_access import item_assigned_to_user_groups


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

# Gemini 2.5 Flash Lite model ID - required for all task features
REQUIRED_TASK_MODEL_ID = "@vertexai/gemini-2.5-flash-lite"


def user_has_access_to_task_model(user, models: dict) -> bool:
    """
    Check if the user has access to the required Gemini 2.5 Flash Lite model.
    This model is required for all task features (title, tags, autocomplete, query generation).
    """
    if REQUIRED_TASK_MODEL_ID not in models:
        return False
    
    model = models[REQUIRED_TASK_MODEL_ID]
    
    # Check if it's an arena model
    if model.get("arena"):
        access_control = model.get("info", {}).get("meta", {}).get("access_control", {})
        if not has_access(user.id, type="read", access_control=access_control):
            return False
    else:
        # Check access to the model in the database
        model_info = Models.get_model_by_id(REQUIRED_TASK_MODEL_ID)
        if not model_info:
            return False
        
        # Check access: user owns it, has explicit access, or has group access
        if not (user.id == model_info.user_id 
                or has_access(user.id, type="read", access_control=model_info.access_control)
                or item_assigned_to_user_groups(user.id, model_info, "read")):
            return False
    
    return True


##################################
#
# Task Endpoints
#
##################################


@router.get("/config")
async def get_task_config(request: Request, user=Depends(get_verified_user)):
    # Get available models for the user
    from open_webui.utils.models import get_all_models
    models = await get_all_models(request, user)
    
    # Check if user has access to the required Gemini 2.5 Flash Lite model
    has_task_model_access = user_has_access_to_task_model(user, models)
    
    # Get per-admin task config settings (inherits from group admin if user is in a group)
    task_model_external = request.app.state.config.TASK_MODEL_EXTERNAL.get(user.email)
    enable_title_generation = request.app.state.config.ENABLE_TITLE_GENERATION.get(user.email)
    enable_tags_generation = request.app.state.config.ENABLE_TAGS_GENERATION.get(user.email)
    enable_autocomplete_generation = request.app.state.config.ENABLE_AUTOCOMPLETE_GENERATION.get(user.email)
    enable_search_query_generation = request.app.state.config.ENABLE_SEARCH_QUERY_GENERATION.get(user.email)
    enable_retrieval_query_generation = request.app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION.get(user.email)
    
    # Auto-set TASK_MODEL_EXTERNAL to Gemini 2.5 Flash Lite if user has access
    # Otherwise, use the stored value (which might be empty)
    if has_task_model_access:
        # Auto-set to Gemini if not already set or if stored value is empty
        if not task_model_external or task_model_external == "":
            task_model_external = REQUIRED_TASK_MODEL_ID
    else:
        # User doesn't have access - ensure it's empty
        task_model_external = ""
    
    # Auto-enable/disable all task features based on model access
    # If user doesn't have access, disable all features regardless of stored config
    if not has_task_model_access:
        enable_title_generation = False
        enable_tags_generation = False
        enable_autocomplete_generation = False
        enable_search_query_generation = False
        enable_retrieval_query_generation = False
    
    return {
        "TASK_MODEL": request.app.state.config.TASK_MODEL,
        "TASK_MODEL_EXTERNAL": task_model_external,
        "TITLE_GENERATION_PROMPT_TEMPLATE": request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE,
        "IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE": request.app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE,
        "ENABLE_AUTOCOMPLETE_GENERATION": enable_autocomplete_generation,
        "AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH": request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH,
        "TAGS_GENERATION_PROMPT_TEMPLATE": request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE,
        "ENABLE_TAGS_GENERATION": enable_tags_generation,
        "ENABLE_TITLE_GENERATION": enable_title_generation,
        "ENABLE_SEARCH_QUERY_GENERATION": enable_search_query_generation,
        "ENABLE_RETRIEVAL_QUERY_GENERATION": enable_retrieval_query_generation,
        "QUERY_GENERATION_PROMPT_TEMPLATE": request.app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE,
        "TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE": request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
        "HAS_TASK_MODEL_ACCESS": has_task_model_access,  # Additional flag for frontend
    }


class TaskConfigForm(BaseModel):
    TASK_MODEL: Optional[str]
    TASK_MODEL_EXTERNAL: Optional[str]
    ENABLE_TITLE_GENERATION: bool
    TITLE_GENERATION_PROMPT_TEMPLATE: str
    IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE: str
    ENABLE_AUTOCOMPLETE_GENERATION: bool
    AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH: int
    TAGS_GENERATION_PROMPT_TEMPLATE: str
    ENABLE_TAGS_GENERATION: bool
    ENABLE_SEARCH_QUERY_GENERATION: bool
    ENABLE_RETRIEVAL_QUERY_GENERATION: bool
    QUERY_GENERATION_PROMPT_TEMPLATE: str
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE: str


@router.post("/config/update")
async def update_task_config(
    request: Request, form_data: TaskConfigForm, user=Depends(get_admin_user)
):
    # Get available models for the admin user
    from open_webui.utils.models import get_all_models
    models = await get_all_models(request, user)
    
    # Check if user has access to the required Gemini 2.5 Flash Lite model
    has_task_model_access = user_has_access_to_task_model(user, models)
    
    # Save per-admin task config settings (only admin can save, applies to their group)
    if has_task_model_access:
        # Force TASK_MODEL_EXTERNAL to be Gemini 2.5 Flash Lite if user has access
        request.app.state.config.TASK_MODEL_EXTERNAL.set(user.email, REQUIRED_TASK_MODEL_ID)
        # Save the enabled flags if user has access
        request.app.state.config.ENABLE_TITLE_GENERATION.set(user.email, form_data.ENABLE_TITLE_GENERATION)
        request.app.state.config.ENABLE_TAGS_GENERATION.set(user.email, form_data.ENABLE_TAGS_GENERATION)
        request.app.state.config.ENABLE_AUTOCOMPLETE_GENERATION.set(user.email, form_data.ENABLE_AUTOCOMPLETE_GENERATION)
        request.app.state.config.ENABLE_SEARCH_QUERY_GENERATION.set(user.email, form_data.ENABLE_SEARCH_QUERY_GENERATION)
        request.app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION.set(user.email, form_data.ENABLE_RETRIEVAL_QUERY_GENERATION)
    else:
        # User doesn't have access - clear model and disable all features
        request.app.state.config.TASK_MODEL_EXTERNAL.set(user.email, "")
        request.app.state.config.ENABLE_TITLE_GENERATION.set(user.email, False)
        request.app.state.config.ENABLE_TAGS_GENERATION.set(user.email, False)
        request.app.state.config.ENABLE_AUTOCOMPLETE_GENERATION.set(user.email, False)
        request.app.state.config.ENABLE_SEARCH_QUERY_GENERATION.set(user.email, False)
        request.app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION.set(user.email, False)
    
    # Save global configs (prompt templates and TASK_MODEL)
    request.app.state.config.TASK_MODEL = form_data.TASK_MODEL
    request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE = (
        form_data.TITLE_GENERATION_PROMPT_TEMPLATE
    )

    request.app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE = (
        form_data.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE
    )

    request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH = (
        form_data.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH
    )

    request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE = (
        form_data.TAGS_GENERATION_PROMPT_TEMPLATE
    )

    request.app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE = (
        form_data.QUERY_GENERATION_PROMPT_TEMPLATE
    )
    request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = (
        form_data.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
    )

    # Return updated config (same logic as get_task_config)
    task_model_external = request.app.state.config.TASK_MODEL_EXTERNAL.get(user.email)
    if has_task_model_access and (not task_model_external or task_model_external == ""):
        task_model_external = REQUIRED_TASK_MODEL_ID
    
    enable_title_generation = request.app.state.config.ENABLE_TITLE_GENERATION.get(user.email) if has_task_model_access else False
    enable_tags_generation = request.app.state.config.ENABLE_TAGS_GENERATION.get(user.email) if has_task_model_access else False
    enable_autocomplete_generation = request.app.state.config.ENABLE_AUTOCOMPLETE_GENERATION.get(user.email) if has_task_model_access else False
    enable_search_query_generation = request.app.state.config.ENABLE_SEARCH_QUERY_GENERATION.get(user.email) if has_task_model_access else False
    enable_retrieval_query_generation = request.app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION.get(user.email) if has_task_model_access else False

    return {
        "TASK_MODEL": request.app.state.config.TASK_MODEL,
        "TASK_MODEL_EXTERNAL": task_model_external,
        "ENABLE_TITLE_GENERATION": enable_title_generation,
        "TITLE_GENERATION_PROMPT_TEMPLATE": request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE,
        "IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE": request.app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE,
        "ENABLE_AUTOCOMPLETE_GENERATION": enable_autocomplete_generation,
        "AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH": request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH,
        "TAGS_GENERATION_PROMPT_TEMPLATE": request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE,
        "ENABLE_TAGS_GENERATION": enable_tags_generation,
        "ENABLE_SEARCH_QUERY_GENERATION": enable_search_query_generation,
        "ENABLE_RETRIEVAL_QUERY_GENERATION": enable_retrieval_query_generation,
        "QUERY_GENERATION_PROMPT_TEMPLATE": request.app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE,
        "TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE": request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
        "HAS_TASK_MODEL_ACCESS": has_task_model_access,
    }


@router.post("/title/completions")
async def generate_title(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        models = {
            request.state.model["id"]: request.state.model,
        }
    else:
        from open_webui.utils.models import get_all_models
        models = await get_all_models(request, user)
    
    # Check if user has access to the required Gemini 2.5 Flash Lite model
    if not user_has_access_to_task_model(user, models):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Title generation requires access to Gemini 2.5 Flash Lite model"},
        )

    # Check per-admin config (inherits from group admin if user is in a group)
    if not request.app.state.config.ENABLE_TITLE_GENERATION.get(user.email):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": "Title generation is disabled"},
        )

    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    # Use per-admin TASK_MODEL_EXTERNAL (inherits from group admin)
    task_model_id = get_task_model_id(
        model_id,
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL.get(user.email),
        models,
    )

    log.debug(
        f"generating chat title using model {task_model_id} for user {user.email} "
    )

    if request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE != "":
        template = request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE
    else:
        template = DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE

    messages = form_data["messages"]

    # Remove reasoning details from the messages
    for message in messages:
        message["content"] = re.sub(
            r"<details\s+type=\"reasoning\"[^>]*>.*?<\/details>",
            "",
            message["content"],
            flags=re.S,
        ).strip()

    content = title_generation_template(
        template,
        messages,
        {
            "name": user.name,
            "location": user.info.get("location") if user.info else None,
        },
    )

    payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        **(
            {"max_tokens": 1000}
            if models[task_model_id].get("owned_by") == "ollama"
            else {
                "max_completion_tokens": 1000,
            }
        ),
        "metadata": {
            **(request.state.metadata if hasattr(request.state, "metadata") else {}),
            "task": str(TASKS.TITLE_GENERATION),
            "task_body": form_data,
            "chat_id": form_data.get("chat_id", None),
        },
    }

    # Process the payload through the pipeline
    try:
        payload = await process_pipeline_inlet_filter(request, payload, user, models)
    except Exception as e:
        raise e

    try:
        return await generate_chat_completion(request, form_data=payload, user=user)
    except Exception as e:
        log.error("Exception occurred", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "An internal error has occurred."},
        )


@router.post("/tags/completions")
async def generate_chat_tags(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        models = {
            request.state.model["id"]: request.state.model,
        }
    else:
        from open_webui.utils.models import get_all_models
        models = await get_all_models(request, user)
    
    # Check if user has access to the required Gemini 2.5 Flash Lite model
    if not user_has_access_to_task_model(user, models):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Tags generation requires access to Gemini 2.5 Flash Lite model"},
        )

    # Check per-admin config (inherits from group admin if user is in a group)
    if not request.app.state.config.ENABLE_TAGS_GENERATION.get(user.email):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": "Tags generation is disabled"},
        )

    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    # Use per-admin TASK_MODEL_EXTERNAL (inherits from group admin)
    task_model_id = get_task_model_id(
        model_id,
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL.get(user.email),
        models,
    )

    log.debug(
        f"generating chat tags using model {task_model_id} for user {user.email} "
    )

    if request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE != "":
        template = request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE
    else:
        template = DEFAULT_TAGS_GENERATION_PROMPT_TEMPLATE

    content = tags_generation_template(
        template, form_data["messages"], {"name": user.name}
    )

    payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "metadata": {
            **(request.state.metadata if hasattr(request.state, "metadata") else {}),
            "task": str(TASKS.TAGS_GENERATION),
            "task_body": form_data,
            "chat_id": form_data.get("chat_id", None),
        },
    }

    # Process the payload through the pipeline
    try:
        payload = await process_pipeline_inlet_filter(request, payload, user, models)
    except Exception as e:
        raise e

    try:
        return await generate_chat_completion(request, form_data=payload, user=user)
    except Exception as e:
        log.error(f"Error generating chat completion: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal error has occurred."},
        )


@router.post("/image_prompt/completions")
async def generate_image_prompt(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        models = {
            request.state.model["id"]: request.state.model,
        }
    else:
        models = request.app.state.MODELS

    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    # Use per-admin TASK_MODEL_EXTERNAL (inherits from group admin)
    task_model_id = get_task_model_id(
        model_id,
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL.get(user.email),
        models,
    )

    log.debug(
        f"generating image prompt using model {task_model_id} for user {user.email} "
    )

    if request.app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE != "":
        template = request.app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE
    else:
        template = DEFAULT_IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE

    content = image_prompt_generation_template(
        template,
        form_data["messages"],
        user={
            "name": user.name,
        },
    )

    payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "metadata": {
            **(request.state.metadata if hasattr(request.state, "metadata") else {}),
            "task": str(TASKS.IMAGE_PROMPT_GENERATION),
            "task_body": form_data,
            "chat_id": form_data.get("chat_id", None),
        },
    }

    # Process the payload through the pipeline
    try:
        payload = await process_pipeline_inlet_filter(request, payload, user, models)
    except Exception as e:
        raise e

    try:
        return await generate_chat_completion(request, form_data=payload, user=user)
    except Exception as e:
        log.error("Exception occurred", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "An internal error has occurred."},
        )


@router.post("/queries/completions")
async def generate_queries(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        models = {
            request.state.model["id"]: request.state.model,
        }
    else:
        from open_webui.utils.models import get_all_models
        models = await get_all_models(request, user)
    
    # Check if user has access to the required Gemini 2.5 Flash Lite model
    if not user_has_access_to_task_model(user, models):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Query generation requires access to Gemini 2.5 Flash Lite model",
        )

    type = form_data.get("type")
    if type == "web_search":
        # Check per-admin config (inherits from group admin if user is in a group)
        if not request.app.state.config.ENABLE_SEARCH_QUERY_GENERATION.get(user.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Search query generation is disabled",
            )
    elif type == "retrieval":
        # Check per-admin config (inherits from group admin if user is in a group)
        if not request.app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION.get(user.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query generation is disabled",
            )

    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    # Use per-admin TASK_MODEL_EXTERNAL (inherits from group admin)
    task_model_id = get_task_model_id(
        model_id,
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL.get(user.email),
        models,
    )

    log.debug(
        f"generating {type} queries using model {task_model_id} for user {user.email}"
    )

    if (request.app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE).strip() != "":
        template = request.app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE
    else:
        template = DEFAULT_QUERY_GENERATION_PROMPT_TEMPLATE

    content = query_generation_template(
        template, form_data["messages"], {"name": user.name}
    )

    payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "metadata": {
            **(request.state.metadata if hasattr(request.state, "metadata") else {}),
            "task": str(TASKS.QUERY_GENERATION),
            "task_body": form_data,
            "chat_id": form_data.get("chat_id", None),
        },
    }

    # Process the payload through the pipeline
    try:
        payload = await process_pipeline_inlet_filter(request, payload, user, models)
    except Exception as e:
        raise e

    try:
        return await generate_chat_completion(request, form_data=payload, user=user)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(e)},
        )


@router.post("/auto/completions")
async def generate_autocompletion(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        models = {
            request.state.model["id"]: request.state.model,
        }
    else:
        from open_webui.utils.models import get_all_models
        models = await get_all_models(request, user)
    
    # Check if user has access to the required Gemini 2.5 Flash Lite model
    if not user_has_access_to_task_model(user, models):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Autocompletion generation requires access to Gemini 2.5 Flash Lite model",
        )
    
    # Check per-admin config (inherits from group admin if user is in a group)
    if not request.app.state.config.ENABLE_AUTOCOMPLETE_GENERATION.get(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Autocompletion generation is disabled",
        )

    type = form_data.get("type")
    prompt = form_data.get("prompt")
    messages = form_data.get("messages")

    if request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH > 0:
        if (
            len(prompt)
            > request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input prompt exceeds maximum length of {request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH}",
            )

    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    # Use per-admin TASK_MODEL_EXTERNAL (inherits from group admin)
    task_model_id = get_task_model_id(
        model_id,
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL.get(user.email),
        models,
    )

    log.debug(
        f"generating autocompletion using model {task_model_id} for user {user.email}"
    )

    if (request.app.state.config.AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE).strip() != "":
        template = request.app.state.config.AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE
    else:
        template = DEFAULT_AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE

    content = autocomplete_generation_template(
        template, prompt, messages, type, {"name": user.name}
    )

    payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "metadata": {
            **(request.state.metadata if hasattr(request.state, "metadata") else {}),
            "task": str(TASKS.AUTOCOMPLETE_GENERATION),
            "task_body": form_data,
            "chat_id": form_data.get("chat_id", None),
        },
    }

    # Process the payload through the pipeline
    try:
        payload = await process_pipeline_inlet_filter(request, payload, user, models)
    except Exception as e:
        raise e

    try:
        return await generate_chat_completion(request, form_data=payload, user=user)
    except Exception as e:
        log.error(f"Error generating chat completion: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal error has occurred."},
        )


@router.post("/emoji/completions")
async def generate_emoji(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):

    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        models = {
            request.state.model["id"]: request.state.model,
        }
    else:
        models = request.app.state.MODELS

    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    # Use per-admin TASK_MODEL_EXTERNAL (inherits from group admin)
    task_model_id = get_task_model_id(
        model_id,
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL.get(user.email),
        models,
    )

    log.debug(f"generating emoji using model {task_model_id} for user {user.email} ")

    template = DEFAULT_EMOJI_GENERATION_PROMPT_TEMPLATE

    content = emoji_generation_template(
        template,
        form_data["prompt"],
        {
            "name": user.name,
            "location": user.info.get("location") if user.info else None,
        },
    )

    payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        **(
            {"max_tokens": 4}
            if models[task_model_id].get("owned_by") == "ollama"
            else {
                "max_completion_tokens": 4,
            }
        ),
        "chat_id": form_data.get("chat_id", None),
        "metadata": {
            **(request.state.metadata if hasattr(request.state, "metadata") else {}),
            "task": str(TASKS.EMOJI_GENERATION),
            "task_body": form_data,
        },
    }

    # Process the payload through the pipeline
    try:
        payload = await process_pipeline_inlet_filter(request, payload, user, models)
    except Exception as e:
        raise e

    try:
        return await generate_chat_completion(request, form_data=payload, user=user)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(e)},
        )


@router.post("/moa/completions")
async def generate_moa_response(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):

    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        models = {
            request.state.model["id"]: request.state.model,
        }
    else:
        models = request.app.state.MODELS

    model_id = form_data["model"]

    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    # Use per-admin TASK_MODEL_EXTERNAL (inherits from group admin)
    task_model_id = get_task_model_id(
        model_id,
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL.get(user.email),
        models,
    )

    log.debug(f"generating MOA model {task_model_id} for user {user.email} ")

    template = DEFAULT_MOA_GENERATION_PROMPT_TEMPLATE

    content = moa_response_generation_template(
        template,
        form_data["prompt"],
        form_data["responses"],
    )

    payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": form_data.get("stream", False),
        "metadata": {
            **(request.state.metadata if hasattr(request.state, "metadata") else {}),
            "chat_id": form_data.get("chat_id", None),
            "task": str(TASKS.MOA_RESPONSE_GENERATION),
            "task_body": form_data,
        },
    }

    # Process the payload through the pipeline
    try:
        payload = await process_pipeline_inlet_filter(request, payload, user, models)
    except Exception as e:
        raise e

    try:
        return await generate_chat_completion(request, form_data=payload, user=user)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(e)},
        )

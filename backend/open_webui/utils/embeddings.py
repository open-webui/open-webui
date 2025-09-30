import logging
import sys

from fastapi import Request
from open_webui.models.users import UserModel
from open_webui.utils.filter import get_sorted_filter_ids, process_filter_functions
from open_webui.utils.models import check_model_access
from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL, BYPASS_MODEL_ACCESS_CONTROL

from open_webui.routers.openai import embeddings as openai_embeddings
from open_webui.routers.ollama import (
    embeddings as ollama_embeddings,
    GenerateEmbeddingsForm,
)


from open_webui.utils.payload import convert_embedding_payload_openai_to_ollama
from open_webui.utils.response import convert_embedding_response_ollama_to_openai

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


async def generate_embeddings(
    request: Request,
    form_data: dict,
    user: UserModel,
    bypass_filter: bool = False,
):
    """
    Dispatch and handle embeddings generation based on the model type (OpenAI, Ollama).

    Args:
        request (Request): The FastAPI request context.
        form_data (dict): The input data sent to the endpoint.
        user (UserModel): The authenticated user.
        bypass_filter (bool): If True, disables access filtering (default False).

    Returns:
        dict: The embeddings response, following OpenAI API compatibility.
    """
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    # Attach extra metadata from request.state if present
    if hasattr(request.state, "metadata"):
        if "metadata" not in form_data:
            form_data["metadata"] = request.state.metadata
        else:
            form_data["metadata"] = {
                **form_data["metadata"],
                **request.state.metadata,
            }

    # If "direct" flag present, use only that model
    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        models = {
            request.state.model["id"]: request.state.model,
        }
    else:
        models = request.app.state.MODELS

    model_id = form_data.get("model")
    if model_id not in models:
        raise Exception("Model not found")
    model = models[model_id]

    # Access filtering
    if not getattr(request.state, "direct", False):
        if not bypass_filter and user.role == "user":
            check_model_access(user, model)

    # === FILTER INLET ===
    # Get active filter ids for this model
    filter_ids = get_sorted_filter_ids(request, model)
    if filter_ids:
        from open_webui.models.functions import Functions

        filter_functions = [
            Functions.get_function_by_id(fid)
            for fid in filter_ids
            if Functions.get_function_by_id(fid)
        ]
        # Apply inlet filters
        form_data, _ = await process_filter_functions(
            request, filter_functions, "inlet", form_data, {"__user__": user}
        )

    # Ollama backend
    if model.get("owned_by") == "ollama":
        ollama_payload = convert_embedding_payload_openai_to_ollama(form_data)
        response = await ollama_embeddings(
            request=request,
            form_data=GenerateEmbeddingsForm(**ollama_payload),
            user=user,
        )
        # === FILTER OUTLET ===
        if filter_ids:
            response, _ = await process_filter_functions(
                request, filter_functions, "outlet", response, {"__user__": user}
            )
        return convert_embedding_response_ollama_to_openai(response)

    # Default: OpenAI or compatible backend
    response = await openai_embeddings(
        request=request,
        form_data=form_data,
        user=user,
    )
    # === FILTER OUTLET ===
    if filter_ids:
        response, _ = await process_filter_functions(
            request, filter_functions, "outlet", response, {"__user__": user}
        )
    return response

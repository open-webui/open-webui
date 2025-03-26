import asyncio
import base64
import io
import json
import logging
import mimetypes
import re
from pathlib import Path
from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from open_webui.config import CACHE_DIR
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import ENABLE_FORWARD_USER_INFO_HEADERS, SRC_LOG_LEVELS
from open_webui.routers.files import upload_file
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.images.comfyui import (
    ComfyUIGenerateImageForm,
    ComfyUIWorkflow,
    comfyui_generate_image,
)
from pydantic import BaseModel

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["IMAGES"])

IMAGE_CACHE_DIR = CACHE_DIR / "image" / "generations"
IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


router = APIRouter()


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "enabled": request.app.state.config.ENABLE_IMAGE_GENERATION,
        "engine": request.app.state.config.IMAGE_GENERATION_ENGINE,
        "prompt_generation": request.app.state.config.ENABLE_IMAGE_PROMPT_GENERATION,
        "openai": {
            "OPENAI_API_BASE_URL": request.app.state.config.IMAGES_OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": request.app.state.config.IMAGES_OPENAI_API_KEY,
        },
        "automatic1111": {
            "AUTOMATIC1111_BASE_URL": request.app.state.config.AUTOMATIC1111_BASE_URL,
            "AUTOMATIC1111_API_AUTH": request.app.state.config.AUTOMATIC1111_API_AUTH,
            "AUTOMATIC1111_CFG_SCALE": request.app.state.config.AUTOMATIC1111_CFG_SCALE,
            "AUTOMATIC1111_SAMPLER": request.app.state.config.AUTOMATIC1111_SAMPLER,
            "AUTOMATIC1111_SCHEDULER": request.app.state.config.AUTOMATIC1111_SCHEDULER,
        },
        "comfyui": {
            "COMFYUI_BASE_URL": request.app.state.config.COMFYUI_BASE_URL,
            "COMFYUI_API_KEY": request.app.state.config.COMFYUI_API_KEY,
            "COMFYUI_WORKFLOW": request.app.state.config.COMFYUI_WORKFLOW,
            "COMFYUI_WORKFLOW_NODES": request.app.state.config.COMFYUI_WORKFLOW_NODES,
        },
        "gemini": {
            "GEMINI_API_BASE_URL": request.app.state.config.IMAGES_GEMINI_API_BASE_URL,
            "GEMINI_API_KEY": request.app.state.config.IMAGES_GEMINI_API_KEY,
        },
    }


class OpenAIConfigForm(BaseModel):
    OPENAI_API_BASE_URL: str
    OPENAI_API_KEY: str


class Automatic1111ConfigForm(BaseModel):
    AUTOMATIC1111_BASE_URL: str
    AUTOMATIC1111_API_AUTH: str
    AUTOMATIC1111_CFG_SCALE: Optional[str | float | int]
    AUTOMATIC1111_SAMPLER: Optional[str]
    AUTOMATIC1111_SCHEDULER: Optional[str]


class ComfyUIConfigForm(BaseModel):
    COMFYUI_BASE_URL: str
    COMFYUI_API_KEY: str
    COMFYUI_WORKFLOW: str
    COMFYUI_WORKFLOW_NODES: list[dict]


class GeminiConfigForm(BaseModel):
    GEMINI_API_BASE_URL: str
    GEMINI_API_KEY: str


class ConfigForm(BaseModel):
    enabled: bool
    engine: str
    prompt_generation: bool
    openai: OpenAIConfigForm
    automatic1111: Automatic1111ConfigForm
    comfyui: ComfyUIConfigForm
    gemini: GeminiConfigForm


@router.post("/config/update")
async def update_config(
    request: Request, form_data: ConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.IMAGE_GENERATION_ENGINE = form_data.engine
    request.app.state.config.ENABLE_IMAGE_GENERATION = form_data.enabled

    request.app.state.config.ENABLE_IMAGE_PROMPT_GENERATION = (
        form_data.prompt_generation
    )

    request.app.state.config.IMAGES_OPENAI_API_BASE_URL = (
        form_data.openai.OPENAI_API_BASE_URL
    )
    request.app.state.config.IMAGES_OPENAI_API_KEY = form_data.openai.OPENAI_API_KEY

    request.app.state.config.IMAGES_GEMINI_API_BASE_URL = (
        form_data.gemini.GEMINI_API_BASE_URL
    )
    request.app.state.config.IMAGES_GEMINI_API_KEY = form_data.gemini.GEMINI_API_KEY

    request.app.state.config.AUTOMATIC1111_BASE_URL = (
        form_data.automatic1111.AUTOMATIC1111_BASE_URL
    )
    request.app.state.config.AUTOMATIC1111_API_AUTH = (
        form_data.automatic1111.AUTOMATIC1111_API_AUTH
    )

    request.app.state.config.AUTOMATIC1111_CFG_SCALE = (
        float(form_data.automatic1111.AUTOMATIC1111_CFG_SCALE)
        if form_data.automatic1111.AUTOMATIC1111_CFG_SCALE
        else None
    )
    request.app.state.config.AUTOMATIC1111_SAMPLER = (
        form_data.automatic1111.AUTOMATIC1111_SAMPLER
        if form_data.automatic1111.AUTOMATIC1111_SAMPLER
        else None
    )
    request.app.state.config.AUTOMATIC1111_SCHEDULER = (
        form_data.automatic1111.AUTOMATIC1111_SCHEDULER
        if form_data.automatic1111.AUTOMATIC1111_SCHEDULER
        else None
    )

    request.app.state.config.COMFYUI_BASE_URL = (
        form_data.comfyui.COMFYUI_BASE_URL.strip("/")
    )
    request.app.state.config.COMFYUI_API_KEY = form_data.comfyui.COMFYUI_API_KEY

    request.app.state.config.COMFYUI_WORKFLOW = form_data.comfyui.COMFYUI_WORKFLOW
    request.app.state.config.COMFYUI_WORKFLOW_NODES = (
        form_data.comfyui.COMFYUI_WORKFLOW_NODES
    )

    return {
        "enabled": request.app.state.config.ENABLE_IMAGE_GENERATION,
        "engine": request.app.state.config.IMAGE_GENERATION_ENGINE,
        "prompt_generation": request.app.state.config.ENABLE_IMAGE_PROMPT_GENERATION,
        "openai": {
            "OPENAI_API_BASE_URL": request.app.state.config.IMAGES_OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": request.app.state.config.IMAGES_OPENAI_API_KEY,
        },
        "automatic1111": {
            "AUTOMATIC1111_BASE_URL": request.app.state.config.AUTOMATIC1111_BASE_URL,
            "AUTOMATIC1111_API_AUTH": request.app.state.config.AUTOMATIC1111_API_AUTH,
            "AUTOMATIC1111_CFG_SCALE": request.app.state.config.AUTOMATIC1111_CFG_SCALE,
            "AUTOMATIC1111_SAMPLER": request.app.state.config.AUTOMATIC1111_SAMPLER,
            "AUTOMATIC1111_SCHEDULER": request.app.state.config.AUTOMATIC1111_SCHEDULER,
        },
        "comfyui": {
            "COMFYUI_BASE_URL": request.app.state.config.COMFYUI_BASE_URL,
            "COMFYUI_API_KEY": request.app.state.config.COMFYUI_API_KEY,
            "COMFYUI_WORKFLOW": request.app.state.config.COMFYUI_WORKFLOW,
            "COMFYUI_WORKFLOW_NODES": request.app.state.config.COMFYUI_WORKFLOW_NODES,
        },
        "gemini": {
            "GEMINI_API_BASE_URL": request.app.state.config.IMAGES_GEMINI_API_BASE_URL,
            "GEMINI_API_KEY": request.app.state.config.IMAGES_GEMINI_API_KEY,
        },
    }


def get_automatic1111_api_auth(request: Request):
    if request.app.state.config.AUTOMATIC1111_API_AUTH is None:
        return ""
    else:
        auth1111_byte_string = request.app.state.config.AUTOMATIC1111_API_AUTH.encode(
            "utf-8"
        )
        auth1111_base64_encoded_bytes = base64.b64encode(auth1111_byte_string)
        auth1111_base64_encoded_string = auth1111_base64_encoded_bytes.decode("utf-8")
        return f"Basic {auth1111_base64_encoded_string}"


@router.get("/config/url/verify")
async def verify_url(request: Request, user=Depends(get_admin_user)):
    if request.app.state.config.IMAGE_GENERATION_ENGINE == "automatic1111":
        try:
            r = requests.get(
                url=f"{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options",
                headers={"authorization": get_automatic1111_api_auth(request)},
            )
            r.raise_for_status()
            return True
        except Exception:
            request.app.state.config.ENABLE_IMAGE_GENERATION = False
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.INVALID_URL)
    elif request.app.state.config.IMAGE_GENERATION_ENGINE == "comfyui":

        headers = None
        if request.app.state.config.COMFYUI_API_KEY:
            headers = {
                "Authorization": f"Bearer {request.app.state.config.COMFYUI_API_KEY}"
            }

        try:
            r = requests.get(
                url=f"{request.app.state.config.COMFYUI_BASE_URL}/object_info",
                headers=headers,
            )
            r.raise_for_status()
            return True
        except Exception:
            request.app.state.config.ENABLE_IMAGE_GENERATION = False
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.INVALID_URL)
    else:
        return True


def set_image_model(request: Request, model: str):
    log.info(f"Setting image model to {model}")
    request.app.state.config.IMAGE_GENERATION_MODEL = model
    if request.app.state.config.IMAGE_GENERATION_ENGINE in ["", "automatic1111"]:
        api_auth = get_automatic1111_api_auth(request)
        r = requests.get(
            url=f"{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options",
            headers={"authorization": api_auth},
        )
        options = r.json()
        if model != options["sd_model_checkpoint"]:
            options["sd_model_checkpoint"] = model
            r = requests.post(
                url=f"{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options",
                json=options,
                headers={"authorization": api_auth},
            )
    return request.app.state.config.IMAGE_GENERATION_MODEL


def get_image_model(request):
    if request.app.state.config.IMAGE_GENERATION_ENGINE == "openai":
        return (
            request.app.state.config.IMAGE_GENERATION_MODEL
            if request.app.state.config.IMAGE_GENERATION_MODEL
            else "dall-e-2"
        )
    elif request.app.state.config.IMAGE_GENERATION_ENGINE == "gemini":
        return (
            request.app.state.config.IMAGE_GENERATION_MODEL
            if request.app.state.config.IMAGE_GENERATION_MODEL
            else "imagen-3.0-generate-002"
        )
    elif request.app.state.config.IMAGE_GENERATION_ENGINE == "comfyui":
        return (
            request.app.state.config.IMAGE_GENERATION_MODEL
            if request.app.state.config.IMAGE_GENERATION_MODEL
            else ""
        )
    elif (
        request.app.state.config.IMAGE_GENERATION_ENGINE == "automatic1111"
        or request.app.state.config.IMAGE_GENERATION_ENGINE == ""
    ):
        try:
            r = requests.get(
                url=f"{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options",
                headers={"authorization": get_automatic1111_api_auth(request)},
            )
            options = r.json()
            return options["sd_model_checkpoint"]
        except Exception as e:
            request.app.state.config.ENABLE_IMAGE_GENERATION = False
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))


class ImageConfigForm(BaseModel):
    MODEL: str
    IMAGE_SIZE: str
    IMAGE_STEPS: int


@router.get("/image/config")
async def get_image_config(request: Request, user=Depends(get_admin_user)):
    return {
        "MODEL": request.app.state.config.IMAGE_GENERATION_MODEL,
        "IMAGE_SIZE": request.app.state.config.IMAGE_SIZE,
        "IMAGE_STEPS": request.app.state.config.IMAGE_STEPS,
    }


@router.post("/image/config/update")
async def update_image_config(
    request: Request, form_data: ImageConfigForm, user=Depends(get_admin_user)
):
    set_image_model(request, form_data.MODEL)

    pattern = r"^\d+x\d+$"
    if re.match(pattern, form_data.IMAGE_SIZE):
        request.app.state.config.IMAGE_SIZE = form_data.IMAGE_SIZE
    else:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.INCORRECT_FORMAT("  (e.g., 512x512)."),
        )

    if form_data.IMAGE_STEPS >= 0:
        request.app.state.config.IMAGE_STEPS = form_data.IMAGE_STEPS
    else:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.INCORRECT_FORMAT("  (e.g., 50)."),
        )

    return {
        "MODEL": request.app.state.config.IMAGE_GENERATION_MODEL,
        "IMAGE_SIZE": request.app.state.config.IMAGE_SIZE,
        "IMAGE_STEPS": request.app.state.config.IMAGE_STEPS,
    }


@router.get("/models")
def get_models(request: Request, user=Depends(get_verified_user)):
    try:
        if request.app.state.config.IMAGE_GENERATION_ENGINE == "openai":
            return [
                {"id": "dall-e-2", "name": "DALL·E 2"},
                {"id": "dall-e-3", "name": "DALL·E 3"},
            ]
        elif request.app.state.config.IMAGE_GENERATION_ENGINE == "gemini":
            return [
                {"id": "imagen-3-0-generate-002", "name": "imagen-3.0 generate-002"},
            ]
        elif request.app.state.config.IMAGE_GENERATION_ENGINE == "comfyui":
            # TODO - get models from comfyui
            headers = {
                "Authorization": f"Bearer {request.app.state.config.COMFYUI_API_KEY}"
            }
            r = requests.get(
                url=f"{request.app.state.config.COMFYUI_BASE_URL}/object_info",
                headers=headers,
            )
            info = r.json()

            workflow = json.loads(request.app.state.config.COMFYUI_WORKFLOW)
            model_node_id = None

            for node in request.app.state.config.COMFYUI_WORKFLOW_NODES:
                if node["type"] == "model":
                    if node["node_ids"]:
                        model_node_id = node["node_ids"][0]
                    break

            if model_node_id:
                model_list_key = None

                log.info(workflow[model_node_id]["class_type"])
                for key in info[workflow[model_node_id]["class_type"]]["input"][
                    "required"
                ]:
                    if "_name" in key:
                        model_list_key = key
                        break

                if model_list_key:
                    return list(
                        map(
                            lambda model: {"id": model, "name": model},
                            info[workflow[model_node_id]["class_type"]]["input"][
                                "required"
                            ][model_list_key][0],
                        )
                    )
            else:
                return list(
                    map(
                        lambda model: {"id": model, "name": model},
                        info["CheckpointLoaderSimple"]["input"]["required"][
                            "ckpt_name"
                        ][0],
                    )
                )
        elif (
            request.app.state.config.IMAGE_GENERATION_ENGINE == "automatic1111"
            or request.app.state.config.IMAGE_GENERATION_ENGINE == ""
        ):
            r = requests.get(
                url=f"{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/sd-models",
                headers={"authorization": get_automatic1111_api_auth(request)},
            )
            models = r.json()
            return list(
                map(
                    lambda model: {"id": model["title"], "name": model["model_name"]},
                    models,
                )
            )
    except Exception as e:
        request.app.state.config.ENABLE_IMAGE_GENERATION = False
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))


class GenerateImageForm(BaseModel):
    model: Optional[str] = None
    prompt: str
    size: Optional[str] = None
    n: int = 1
    negative_prompt: Optional[str] = None


def load_b64_image_data(b64_str):
    try:
        if "," in b64_str:
            header, encoded = b64_str.split(",", 1)
            mime_type = header.split(";")[0]
            img_data = base64.b64decode(encoded)
        else:
            mime_type = "image/png"
            img_data = base64.b64decode(b64_str)
        return img_data, mime_type
    except Exception as e:
        log.exception(f"Error loading image data: {e}")
        return None


def load_url_image_data(url, headers=None):
    try:
        if headers:
            r = requests.get(url, headers=headers)
        else:
            r = requests.get(url)

        r.raise_for_status()
        if r.headers["content-type"].split("/")[0] == "image":
            mime_type = r.headers["content-type"]
            return r.content, mime_type
        else:
            log.error("Url does not point to an image.")
            return None

    except Exception as e:
        log.exception(f"Error saving image: {e}")
        return None


def upload_image(request, image_metadata, image_data, content_type, user):
    image_format = mimetypes.guess_extension(content_type)
    file = UploadFile(
        file=io.BytesIO(image_data),
        filename=f"generated-image{image_format}",  # will be converted to a unique ID on upload_file
        headers={
            "content-type": content_type,
        },
    )
    file_item = upload_file(request, file, user, file_metadata=image_metadata)
    url = request.app.url_path_for("get_file_content_by_id", id=file_item.id)
    return url


@router.post("/generations")
async def image_generations(
    request: Request,
    form_data: GenerateImageForm,
    user=Depends(get_verified_user),
):
    width, height = tuple(map(int, request.app.state.config.IMAGE_SIZE.split("x")))

    r = None
    try:
        if request.app.state.config.IMAGE_GENERATION_ENGINE == "openai":
            headers = {}
            headers["Authorization"] = (
                f"Bearer {request.app.state.config.IMAGES_OPENAI_API_KEY}"
            )
            headers["Content-Type"] = "application/json"

            if ENABLE_FORWARD_USER_INFO_HEADERS:
                headers["X-OpenWebUI-User-Name"] = user.name
                headers["X-OpenWebUI-User-Id"] = user.id
                headers["X-OpenWebUI-User-Email"] = user.email
                headers["X-OpenWebUI-User-Role"] = user.role

            data = {
                "model": (
                    request.app.state.config.IMAGE_GENERATION_MODEL
                    if request.app.state.config.IMAGE_GENERATION_MODEL != ""
                    else "dall-e-2"
                ),
                "prompt": form_data.prompt,
                "n": form_data.n,
                "size": (
                    form_data.size
                    if form_data.size
                    else request.app.state.config.IMAGE_SIZE
                ),
                "response_format": "b64_json",
            }

            # Use asyncio.to_thread for the requests.post call
            r = await asyncio.to_thread(
                requests.post,
                url=f"{request.app.state.config.IMAGES_OPENAI_API_BASE_URL}/images/generations",
                json=data,
                headers=headers,
            )

            r.raise_for_status()
            res = r.json()

            images = []

            for image in res["data"]:
                if image_url := image.get("url", None):
                    image_data, content_type = load_url_image_data(image_url, headers)
                else:
                    image_data, content_type = load_b64_image_data(image["b64_json"])

                url = upload_image(request, data, image_data, content_type, user)
                images.append({"url": url})
            return images

        elif request.app.state.config.IMAGE_GENERATION_ENGINE == "gemini":
            headers = {}
            headers["Content-Type"] = "application/json"
            headers["x-goog-api-key"] = request.app.state.config.IMAGES_GEMINI_API_KEY

            model = get_image_model(request)
            data = {
                "instances": {"prompt": form_data.prompt},
                "parameters": {
                    "sampleCount": form_data.n,
                    "outputOptions": {"mimeType": "image/png"},
                },
            }

            # Use asyncio.to_thread for the requests.post call
            r = await asyncio.to_thread(
                requests.post,
                url=f"{request.app.state.config.IMAGES_GEMINI_API_BASE_URL}/models/{model}:predict",
                json=data,
                headers=headers,
            )

            r.raise_for_status()
            res = r.json()

            images = []
            for image in res["predictions"]:
                image_data, content_type = load_b64_image_data(
                    image["bytesBase64Encoded"]
                )
                url = upload_image(request, data, image_data, content_type, user)
                images.append({"url": url})

            return images

        elif request.app.state.config.IMAGE_GENERATION_ENGINE == "comfyui":
            data = {
                "prompt": form_data.prompt,
                "width": width,
                "height": height,
                "n": form_data.n,
            }

            if request.app.state.config.IMAGE_STEPS is not None:
                data["steps"] = request.app.state.config.IMAGE_STEPS

            if form_data.negative_prompt is not None:
                data["negative_prompt"] = form_data.negative_prompt

            form_data = ComfyUIGenerateImageForm(
                **{
                    "workflow": ComfyUIWorkflow(
                        **{
                            "workflow": request.app.state.config.COMFYUI_WORKFLOW,
                            "nodes": request.app.state.config.COMFYUI_WORKFLOW_NODES,
                        }
                    ),
                    **data,
                }
            )
            res = await comfyui_generate_image(
                request.app.state.config.IMAGE_GENERATION_MODEL,
                form_data,
                user.id,
                request.app.state.config.COMFYUI_BASE_URL,
                request.app.state.config.COMFYUI_API_KEY,
            )
            log.debug(f"res: {res}")

            images = []

            for image in res["data"]:
                headers = None
                if request.app.state.config.COMFYUI_API_KEY:
                    headers = {
                        "Authorization": f"Bearer {request.app.state.config.COMFYUI_API_KEY}"
                    }

                image_data, content_type = load_url_image_data(image["url"], headers)
                url = upload_image(
                    request,
                    form_data.model_dump(exclude_none=True),
                    image_data,
                    content_type,
                    user,
                )
                images.append({"url": url})
            return images
        elif (
            request.app.state.config.IMAGE_GENERATION_ENGINE == "automatic1111"
            or request.app.state.config.IMAGE_GENERATION_ENGINE == ""
        ):
            if form_data.model:
                set_image_model(form_data.model)

            data = {
                "prompt": form_data.prompt,
                "batch_size": form_data.n,
                "width": width,
                "height": height,
            }

            if request.app.state.config.IMAGE_STEPS is not None:
                data["steps"] = request.app.state.config.IMAGE_STEPS

            if form_data.negative_prompt is not None:
                data["negative_prompt"] = form_data.negative_prompt

            if request.app.state.config.AUTOMATIC1111_CFG_SCALE:
                data["cfg_scale"] = request.app.state.config.AUTOMATIC1111_CFG_SCALE

            if request.app.state.config.AUTOMATIC1111_SAMPLER:
                data["sampler_name"] = request.app.state.config.AUTOMATIC1111_SAMPLER

            if request.app.state.config.AUTOMATIC1111_SCHEDULER:
                data["scheduler"] = request.app.state.config.AUTOMATIC1111_SCHEDULER

            # Use asyncio.to_thread for the requests.post call
            r = await asyncio.to_thread(
                requests.post,
                url=f"{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/txt2img",
                json=data,
                headers={"authorization": get_automatic1111_api_auth(request)},
            )

            res = r.json()
            log.debug(f"res: {res}")

            images = []

            for image in res["images"]:
                image_data, content_type = load_b64_image_data(image)
                url = upload_image(
                    request,
                    {**data, "info": res["info"]},
                    image_data,
                    content_type,
                    user,
                )
                images.append({"url": url})
            return images
    except Exception as e:
        error = e
        if r != None:
            data = r.json()
            if "error" in data:
                error = data["error"]["message"]
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(error))

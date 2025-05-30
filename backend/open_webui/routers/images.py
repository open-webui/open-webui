import asyncio
import base64
import io
import json
import logging
import mimetypes
import os
import re
from pathlib import Path
from typing import Optional

import requests
import replicate
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
        "replicate": {
            "REPLICATE_API_TOKEN": request.app.state.config.REPLICATE_API_TOKEN,
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


class ReplicateConfigForm(BaseModel):
    REPLICATE_API_TOKEN: str


class ConfigForm(BaseModel):
    enabled: bool
    engine: str
    prompt_generation: bool
    openai: OpenAIConfigForm
    automatic1111: Automatic1111ConfigForm
    comfyui: ComfyUIConfigForm
    gemini: GeminiConfigForm
    replicate: ReplicateConfigForm


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

    request.app.state.config.REPLICATE_API_TOKEN = form_data.replicate.REPLICATE_API_TOKEN
    

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
        "replicate": {
            "REPLICATE_API_TOKEN": request.app.state.config.REPLICATE_API_TOKEN,
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
                timeout=5,
            )
            r.raise_for_status()
            return {"status": True, "message": "URL verified successfully"}

        except requests.exceptions.RequestException as e:
            log.exception(e)
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.AUTOMATIC1111_CONNECTION_ERROR,
            )
    elif request.app.state.config.IMAGE_GENERATION_ENGINE == "comfyui":
        try:
            r = requests.get(
                url=f"{request.app.state.config.COMFYUI_BASE_URL}/object_info",
                timeout=5,
            )
            r.raise_for_status()
            return {"status": True, "message": "URL verified successfully"}
        except requests.exceptions.RequestException as e:
            log.exception(e)
            raise HTTPException(
                status_code=400, detail=ERROR_MESSAGES.COMFYUI_CONNECTION_ERROR
            )

    return {"status": False, "message": "URL verification not supported for this engine"}


def set_image_model(request: Request, model: str):
    log.info(f"Setting image model to {model}")
    request.app.state.config.IMAGE_GENERATION_MODEL = model
    if request.app.state.config.IMAGE_GENERATION_ENGINE in ["", "automatic1111"]:
        try:
            r = requests.post(
                url=f"{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options",
                headers={"authorization": get_automatic1111_api_auth(request)},
                json={"sd_model_checkpoint": model},
                timeout=5,
            )
            r.raise_for_status()
        except Exception as e:
            log.exception(e)
            request.app.state.config.ENABLE_IMAGE_GENERATION = False
            raise HTTPException(
                status_code=400,
                detail=f"{ERROR_MESSAGES.AUTOMATIC1111_SET_MODEL_ERROR}{e}",
            )


def get_image_model(request):
    if request.app.state.config.IMAGE_GENERATION_ENGINE == "openai":
        return (
            request.app.state.config.IMAGE_GENERATION_MODEL
            if request.app.state.config.IMAGE_GENERATION_MODEL
            else "dall-e-3"
        )
    elif request.app.state.config.IMAGE_GENERATION_ENGINE == "gemini":
        return (
            request.app.state.config.IMAGE_GENERATION_MODEL
            if request.app.state.config.IMAGE_GENERATION_MODEL
            else "gemini-1.5-flash"
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
                timeout=5,
            )
            r.raise_for_status()
            return r.json()["sd_model_checkpoint"]
        except Exception as e:
            log.error(e)
            request.app.state.config.ENABLE_IMAGE_GENERATION = False
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.AUTOMATIC1111_GET_MODEL_ERROR,
            )
    elif request.app.state.config.IMAGE_GENERATION_ENGINE == "replicate":
        return (
            request.app.state.config.IMAGE_GENERATION_MODEL
            if request.app.state.config.IMAGE_GENERATION_MODEL
            else "black-forest-labs/flux-1.1-pro-ultra"
        )

    return None


class ImageConfigForm(BaseModel):
    MODEL: str
    IMAGE_SIZE: str
    IMAGE_STEPS: int


@router.get("/image/config")
async def get_image_config(request: Request, user=Depends(get_admin_user)):
    return {
        "MODEL": get_image_model(request),
        "IMAGE_SIZE": request.app.state.config.IMAGE_SIZE,
        "IMAGE_STEPS": request.app.state.config.IMAGE_STEPS,
    }


@router.post("/image/config/update")
async def update_image_config(
    request: Request, form_data: ImageConfigForm, user=Depends(get_admin_user)
):
    set_image_model(request, form_data.MODEL)
    request.app.state.config.IMAGE_SIZE = form_data.IMAGE_SIZE
    request.app.state.config.IMAGE_STEPS = form_data.IMAGE_STEPS

    return {
        "MODEL": request.app.state.config.IMAGE_GENERATION_MODEL,
        "IMAGE_SIZE": request.app.state.config.IMAGE_SIZE,
        "IMAGE_STEPS": request.app.state.config.IMAGE_STEPS,
    }


@router.get("/models")
def get_models(request: Request, user=Depends(get_verified_user)):
    if not request.app.state.config.ENABLE_IMAGE_GENERATION:
        return []

    if request.app.state.config.IMAGE_GENERATION_ENGINE == "openai":
        return [
            {"id": "dall-e-3", "name": "DALL·E 3"},
            {"id": "dall-e-2", "name": "DALL·E 2"},
            {
                "id": "gpt-image-1",
                "name": "GPT Image 1 (Internal Test)",
            },
        ]
    elif request.app.state.config.IMAGE_GENERATION_ENGINE == "gemini":
        return [
            {
                "id": request.app.state.config.IMAGE_GENERATION_MODEL or "gemini-1.5-flash",
                "name": request.app.state.config.IMAGE_GENERATION_MODEL or "Gemini 1.5 Flash",
            }
        ]

    elif request.app.state.config.IMAGE_GENERATION_ENGINE == "comfyui":
        try:
            r = requests.get(
                url=f"{request.app.state.config.COMFYUI_BASE_URL}/object_info/CheckpointLoaderSimple",
                timeout=5,
            )
            r.raise_for_status()
            checkpoints = r.json().get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [])
            if checkpoints and isinstance(checkpoints[0], list):
                 return [{"id": model_name, "name": model_name} for model_name in checkpoints[0]]
            return []


        except Exception as e:
            log.exception(e)
            raise HTTPException(
                status_code=400, detail=ERROR_MESSAGES.COMFYUI_GET_MODELS_ERROR
            )

    elif (
        request.app.state.config.IMAGE_GENERATION_ENGINE == "automatic1111"
        or request.app.state.config.IMAGE_GENERATION_ENGINE == ""
    ):
        try:
            r = requests.get(
                url=f"{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/sd-models",
                headers={"authorization": get_automatic1111_api_auth(request)},
                timeout=5,
            )
            r.raise_for_status()
            return [
                {"id": model["title"], "name": model["model_name"]} for model in r.json()
            ]
        except Exception as e:
            log.exception(e)
            request.app.state.config.ENABLE_IMAGE_GENERATION = False
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.AUTOMATIC1111_GET_MODELS_ERROR,
            )
    elif request.app.state.config.IMAGE_GENERATION_ENGINE == "replicate":
        try:
            return get_replicate_models(request.app.state.config.REPLICATE_API_TOKEN)
        except Exception as e:
            log.exception(f"Error fetching Replicate models: {e}")
            # Fallback to configured model
            return [{"id": "black-forest-labs/flux-1.1-pro-ultra", "name": "FLUX 1.1 Pro Ultra"}]

    return []


class GenerateImageForm(BaseModel):
    model: Optional[str] = None
    prompt: str
    size: Optional[str] = None
    n: int = 1
    negative_prompt: Optional[str] = None
    aspect_ratio: Optional[str] = None


def load_b64_image_data(b64_str):
    try:
        padding = "=" * (4 - len(b64_str) % 4)
        b64_str_padded = b64_str + padding
        image_data = base64.b64decode(b64_str_padded)
        return image_data
    except Exception as e:
        log.error(f"Error decoding base64 string: {e}")
        return None


def load_url_image_data(url, headers=None):
    try:
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        log.error(f"Error loading image from URL ({url}): {e}")
        return None


def upload_image(request, image_data, content_type, metadata, user):
    filename = f"{IMAGE_CACHE_DIR}/{metadata.get('id', 'temp')}.{mimetypes.guess_extension(content_type) or '.png'}"

    with open(filename, "wb") as f:
        f.write(image_data)

    upload_file_obj = UploadFile(Path(filename))

    try:
        file_body = asyncio.run(
            upload_file(
                request=request,
                file=upload_file_obj,
                user=user,
                meta=json.dumps(metadata),
            )
        )
        log.info(f"Uploaded image: {file_body}")
        return file_body

    except Exception as e:
        log.error(f"Error uploading image: {e}")
        return {
            "url": None,
            "b64_json": base64.b64encode(image_data).decode("utf-8"),
        }


@router.post("/generations")
async def image_generations(
    request: Request,
    form_data: GenerateImageForm,
    user=Depends(get_verified_user),
):
    if not request.app.state.config.ENABLE_IMAGE_GENERATION:
        raise HTTPException(
            status_code=400, detail=ERROR_MESSAGES.IMAGE_GENERATION_DISABLED
        )

    image_data_list = []

    if request.app.state.config.IMAGE_GENERATION_ENGINE == "openai":
        try:
            headers = {
                "Authorization": f"Bearer {request.app.state.config.IMAGES_OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
            if ENABLE_FORWARD_USER_INFO_HEADERS and hasattr(user, "id"):
                headers["X-User-Id"] = user.id
                headers["X-User-Email"] = user.email
                headers["X-User-Name"] = user.name
                headers["X-User-Role"] = user.role

            model = (
                form_data.model
                if form_data.model
                else (
                    request.app.state.config.IMAGE_GENERATION_MODEL
                    if request.app.state.config.IMAGE_GENERATION_MODEL != ""
                    else "dall-e-3"
                )
            )

            quality = "standard"
            style = "vivid"

            if "gpt-image-1" in model:
                payload = {
                    "model": model,
                    "prompt": form_data.prompt,
                    "n": form_data.n,
                    "size": form_data.size
                    if form_data.size
                    else request.app.state.config.IMAGE_SIZE,
                    "quality": quality,
                    "style": style,
                }

            else:
                payload = {
                    "model": model,
                    "prompt": form_data.prompt,
                    "n": form_data.n,
                    "size": form_data.size
                    if form_data.size
                    else request.app.state.config.IMAGE_SIZE,
                }
                if model == "dall-e-3":
                    payload["quality"] = quality
                    payload["style"] = style
            

            r = requests.post(
                f"{request.app.state.config.IMAGES_OPENAI_API_BASE_URL}/v1/images/generations",
                headers=headers,
                json=payload,
                timeout=120,
            )
            r.raise_for_status()
            res = r.json()

            for item in res["data"]:
                if "b64_json" in item:
                    image_data = load_b64_image_data(item["b64_json"])
                    image_data_list.append(
                        {
                            "url": None,
                            "b64_json": item["b64_json"],
                        }
                    )
                elif "url" in item:
                    image_content = load_url_image_data(item["url"])
                    if image_content:
                         image_data_list.append(
                            {
                                "url": item["url"],
                                "b64_json": base64.b64encode(image_content).decode("utf-8"),
                            }
                        )

        except Exception as e:
            log.exception(e)
            raise HTTPException(status_code=500, detail=f"{ERROR_MESSAGES.OPENAI_ERROR}{e}")
    elif request.app.state.config.IMAGE_GENERATION_ENGINE == "gemini":
        try:
            log.warning("Gemini image generation is not fully implemented yet.")
            raise HTTPException(status_code=501, detail="Gemini image generation not yet implemented in this version.")


        except Exception as e:
            log.exception(e)
            raise HTTPException(status_code=500, detail=f"Gemini Error: {e}")

    elif request.app.state.config.IMAGE_GENERATION_ENGINE == "comfyui":
        try:
            comfyui_form = ComfyUIGenerateImageForm(
                prompt=form_data.prompt,
                negative_prompt=form_data.negative_prompt,
                count=form_data.n,
                steps=request.app.state.config.IMAGE_STEPS,
                width=int(form_data.size.split("x")[0]) if form_data.size else int(request.app.state.config.IMAGE_SIZE.split("x")[0]),
                height=int(form_data.size.split("x")[1]) if form_data.size else int(request.app.state.config.IMAGE_SIZE.split("x")[1]),
                model=(
                    form_data.model
                    if form_data.model
                    else get_image_model(request)
                ),
            )

            results = await comfyui_generate_image(request, comfyui_form)
            for res_item in results:
                if "b64_json" in res_item:
                    image_data_list.append(res_item)

        except Exception as e:
            log.exception(e)
            raise HTTPException(
                status_code=500, detail=f"{ERROR_MESSAGES.COMFYUI_ERROR}{e}"
            )

    elif (
        request.app.state.config.IMAGE_GENERATION_ENGINE == "automatic1111"
        or request.app.state.config.IMAGE_GENERATION_ENGINE == ""
    ):
        try:
            payload = {
                "prompt": form_data.prompt,
                "negative_prompt": form_data.negative_prompt,
                "batch_size": form_data.n,
                "steps": request.app.state.config.IMAGE_STEPS,
                "cfg_scale": request.app.state.config.AUTOMATIC1111_CFG_SCALE,
                "sampler_name": request.app.state.config.AUTOMATIC1111_SAMPLER,
                "scheduler": request.app.state.config.AUTOMATIC1111_SCHEDULER,
            }

            width, height = map(int, request.app.state.config.IMAGE_SIZE.split("x"))
            if form_data.size:
                width, height = map(int, form_data.size.split("x"))

            payload["width"] = width
            payload["height"] = height
            
            override_settings = {}
            if form_data.model:
                 override_settings["sd_model_checkpoint"] = form_data.model


            if override_settings:
                payload["override_settings"] = override_settings


            r = requests.post(
                url=f"{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/txt2img",
                headers={"authorization": get_automatic1111_api_auth(request)},
                json=payload,
                timeout=120,
            )
            r.raise_for_status()
            res = r.json()

            for image_b64 in res.get("images", []):
                image_data_list.append({"url": None, "b64_json": image_b64})

        except Exception as e:
            log.exception(e)
            raise HTTPException(
                status_code=500, detail=f"{ERROR_MESSAGES.AUTOMATIC1111_ERROR}{e}"
            )
    elif request.app.state.config.IMAGE_GENERATION_ENGINE == "replicate":
        try:
            if not request.app.state.config.REPLICATE_API_TOKEN:
                raise HTTPException(status_code=400, detail="Replicate API token is not configured.")

            os.environ["REPLICATE_API_TOKEN"] = request.app.state.config.REPLICATE_API_TOKEN
            
            # Use the model selected by the user, or fall back to the saved model, or finally default
            model_version = (
                form_data.model
                if form_data.model
                else (
                    request.app.state.config.IMAGE_GENERATION_MODEL
                    if request.app.state.config.IMAGE_GENERATION_MODEL
                    else "black-forest-labs/flux-1.1-pro-ultra"
                )
            )
            
            # Build input parameters
            input_params = {"prompt": form_data.prompt}
            
            # Add negative prompt if provided (some models support it)
            if form_data.negative_prompt:
                input_params["negative_prompt"] = form_data.negative_prompt
            
            # Handle size/aspect ratio for FLUX models
            if form_data.size or form_data.aspect_ratio:
                if form_data.aspect_ratio:
                    input_params["aspect_ratio"] = form_data.aspect_ratio
                elif form_data.size:
                    # Convert size to aspect ratio for FLUX models
                    try:
                        width, height = map(int, form_data.size.split("x"))
                        if width == height:
                            input_params["aspect_ratio"] = "1:1"
                        elif width > height:
                            if width / height >= 1.7:
                                input_params["aspect_ratio"] = "16:9"
                            elif width / height >= 1.4:
                                input_params["aspect_ratio"] = "3:2"
                            else:
                                input_params["aspect_ratio"] = "4:3"
                        else:  # height > width
                            if height / width >= 1.7:
                                input_params["aspect_ratio"] = "9:16"
                            elif height / width >= 1.4:
                                input_params["aspect_ratio"] = "2:3"
                            else:
                                input_params["aspect_ratio"] = "3:4"
                    except (ValueError, ZeroDivisionError):
                        input_params["aspect_ratio"] = "1:1"
            else:
                # Default aspect ratio
                input_params["aspect_ratio"] = "1:1"
            
            log.info(f"Generating image with Replicate model: {model_version}")
            log.info(f"Input parameters: {input_params}")

            # Generate images
            for i in range(form_data.n):
                try:
                    log.info(f"Starting Replicate generation {i+1}/{form_data.n}")
                    
                    # Run the model
                    run_output = replicate.run(model_version, input=input_params)
                    log.info(f"Replicate output type: {type(run_output)}")
                    log.info(f"Replicate output: {run_output}")
                    
                    # Handle different output types
                    if isinstance(run_output, str):
                        # Single URL
                        image_url = run_output
                        log.info(f"Got single image URL: {image_url}")
                        image_data_list.append({
                            "url": image_url,
                            "b64_json": None,
                        })
                        
                    elif isinstance(run_output, list):
                        # Multiple URLs
                        for url in run_output:
                            if isinstance(url, str):
                                log.info(f"Got image URL from list: {url}")
                                image_data_list.append({
                                    "url": url,
                                    "b64_json": None,
                                })
                    
                    else:
                        log.warning(f"Unexpected output type from Replicate: {type(run_output)}")
                        log.warning(f"Output value: {str(run_output)[:200]}...")
                        
                        # Try to convert to string and treat as URL
                        try:
                            url_str = str(run_output)
                            if url_str.startswith(('http://', 'https://')):
                                log.info(f"Converted output to URL: {url_str}")
                                image_data_list.append({
                                    "url": url_str,
                                    "b64_json": None,
                                })
                            else:
                                log.error(f"Output doesn't look like a URL: {url_str}")
                        except Exception as e:
                            log.error(f"Could not handle unexpected output: {e}")
                
                except Exception as e:
                    log.error(f"Error in Replicate generation {i+1}: {e}")
                    # Continue with other generations instead of failing completely
                    continue

            # Check if we got any images
            if not image_data_list:
                raise HTTPException(status_code=500, detail="Failed to generate any images from Replicate")

        except HTTPException:
            raise
        except Exception as e:
            log.exception(f"Replicate generation error: {e}")
            raise HTTPException(status_code=500, detail=f"Replicate Error: {str(e)}")

    else:
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.ENGINE_NOT_SUPPORTED)

    return image_data_list


def get_replicate_models(api_token: str):
    """Fetch available image generation models from Replicate API with fallback to cached list"""
    
    # Static list of popular image generation models as fallback
    cached_models = [
        {
            "id": "black-forest-labs/flux-1.1-pro-ultra",
            "name": "FLUX 1.1 Pro Ultra",
            "description": "Fastest, highest quality FLUX model for professional image generation"
        },
        {
            "id": "black-forest-labs/flux-1.1-pro", 
            "name": "FLUX 1.1 Pro",
            "description": "High quality FLUX model with excellent prompt adherence"
        },
        {
            "id": "black-forest-labs/flux-schnell",
            "name": "FLUX Schnell",
            "description": "Fast FLUX model for quick image generation"
        },
        {
            "id": "black-forest-labs/flux-dev",
            "name": "FLUX Dev",
            "description": "Development version of FLUX with latest features"
        },
        {
            "id": "stability-ai/stable-diffusion-3.5-large",
            "name": "Stable Diffusion 3.5 Large",
            "description": "Latest large Stable Diffusion model"
        },
        {
            "id": "stability-ai/stable-diffusion-3.5-large-turbo",
            "name": "Stable Diffusion 3.5 Large Turbo",
            "description": "Fast version of SD 3.5 Large"
        },
        {
            "id": "stability-ai/stable-diffusion-3",
            "name": "Stable Diffusion 3",
            "description": "Advanced Stable Diffusion model"
        },
        {
            "id": "stability-ai/sdxl",
            "name": "Stable Diffusion XL",
            "description": "High resolution Stable Diffusion model"
        },
        {
            "id": "runwayml/stable-diffusion-v1-5",
            "name": "Stable Diffusion v1.5",
            "description": "Classic Stable Diffusion model"
        },
        {
            "id": "fofr/sdxl-emoji",
            "name": "SDXL Emoji",
            "description": "Specialized model for emoji-style images"
        },
        {
            "id": "tencentarc/photomaker",
            "name": "PhotoMaker",
            "description": "Portrait and headshot generation"
        },
        {
            "id": "lucataco/realistic-vision-v5",
            "name": "Realistic Vision v5",
            "description": "Photorealistic image generation"
        },
        {
            "id": "playgroundai/playground-v2.5-1024px-aesthetic",
            "name": "Playground v2.5",
            "description": "High quality aesthetic image generation"
        },
        {
            "id": "ai-forever/kandinsky-2.2",
            "name": "Kandinsky 2.2",
            "description": "Multilingual text-to-image model"
        }
    ]
    
    # If no API token, return cached models
    if not api_token:
        return cached_models
    
    try:
        # Set the API token for the replicate client
        os.environ["REPLICATE_API_TOKEN"] = api_token
        
        # Try to fetch a few key models to verify API access
        # We'll do this with a short timeout to avoid blocking
        verified_models = []
        test_models = [
            "black-forest-labs/flux-1.1-pro-ultra",
            "black-forest-labs/flux-1.1-pro", 
            "stability-ai/stable-diffusion-3.5-large"
        ]
        
        import time
        start_time = time.time()
        
        for model_string in test_models:
            # Stop if we've spent more than 3 seconds trying
            if time.time() - start_time > 3:
                break
                
            try:
                # Quick check to see if model exists
                model = replicate.models.get(model_string)
                if model and hasattr(model, 'latest_version') and model.latest_version:
                    # Find this model in our cached list and mark it as verified
                    for cached_model in cached_models:
                        if cached_model["id"] == model_string:
                            verified_models.append({
                                **cached_model,
                                "verified": True,
                                "description": model.description or cached_model["description"]
                            })
                            break
            except Exception as e:
                log.debug(f"Could not verify model {model_string}: {e}")
                continue
        
        # If we successfully verified some models, prioritize them
        if verified_models:
            # Put verified models first, then remaining cached models
            verified_ids = {m["id"] for m in verified_models}
            remaining_models = [m for m in cached_models if m["id"] not in verified_ids]
            return verified_models + remaining_models
        else:
            # If verification failed, just return cached models
            log.info("Model verification failed, using cached model list")
            return cached_models
            
    except Exception as e:
        log.warning(f"Error fetching Replicate models, using cached list: {e}")
        return cached_models

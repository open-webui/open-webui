import asyncio
import base64
import json
import logging
import mimetypes
import re
import uuid
from pathlib import Path
from typing import Optional

import requests
from open_webui.apps.images.utils.comfyui import (
    ComfyUIGenerateImageForm,
    ComfyUIWorkflow,
    comfyui_generate_image,
)
from open_webui.config import (
    AUTOMATIC1111_API_AUTH,
    AUTOMATIC1111_BASE_URL,
    CACHE_DIR,
    COMFYUI_BASE_URL,
    COMFYUI_WORKFLOW,
    COMFYUI_WORKFLOW_NODES,
    CORS_ALLOW_ORIGIN,
    ENABLE_IMAGE_GENERATION,
    IMAGE_GENERATION_ENGINE,
    IMAGE_GENERATION_MODEL,
    IMAGE_SIZE,
    IMAGE_STEPS,
    IMAGES_OPENAI_API_BASE_URL,
    IMAGES_OPENAI_API_KEY,
    AppConfig,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from open_webui.utils.utils import get_admin_user, get_verified_user

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["IMAGES"])

IMAGE_CACHE_DIR = Path(CACHE_DIR).joinpath("./image/generations/")
IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.config = AppConfig()

app.state.config.ENGINE = IMAGE_GENERATION_ENGINE
app.state.config.ENABLED = ENABLE_IMAGE_GENERATION

app.state.config.OPENAI_API_BASE_URL = IMAGES_OPENAI_API_BASE_URL
app.state.config.OPENAI_API_KEY = IMAGES_OPENAI_API_KEY

app.state.config.MODEL = IMAGE_GENERATION_MODEL

app.state.config.AUTOMATIC1111_BASE_URL = AUTOMATIC1111_BASE_URL
app.state.config.AUTOMATIC1111_API_AUTH = AUTOMATIC1111_API_AUTH
app.state.config.COMFYUI_BASE_URL = COMFYUI_BASE_URL
app.state.config.COMFYUI_WORKFLOW = COMFYUI_WORKFLOW
app.state.config.COMFYUI_WORKFLOW_NODES = COMFYUI_WORKFLOW_NODES

app.state.config.IMAGE_SIZE = IMAGE_SIZE
app.state.config.IMAGE_STEPS = IMAGE_STEPS


@app.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "enabled": app.state.config.ENABLED,
        "engine": app.state.config.ENGINE,
        "openai": {
            "OPENAI_API_BASE_URL": app.state.config.OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": app.state.config.OPENAI_API_KEY,
        },
        "automatic1111": {
            "AUTOMATIC1111_BASE_URL": app.state.config.AUTOMATIC1111_BASE_URL,
            "AUTOMATIC1111_API_AUTH": app.state.config.AUTOMATIC1111_API_AUTH,
        },
        "comfyui": {
            "COMFYUI_BASE_URL": app.state.config.COMFYUI_BASE_URL,
            "COMFYUI_WORKFLOW": app.state.config.COMFYUI_WORKFLOW,
            "COMFYUI_WORKFLOW_NODES": app.state.config.COMFYUI_WORKFLOW_NODES,
        },
    }


class OpenAIConfigForm(BaseModel):
    OPENAI_API_BASE_URL: str
    OPENAI_API_KEY: str


class Automatic1111ConfigForm(BaseModel):
    AUTOMATIC1111_BASE_URL: str
    AUTOMATIC1111_API_AUTH: str


class ComfyUIConfigForm(BaseModel):
    COMFYUI_BASE_URL: str
    COMFYUI_WORKFLOW: str
    COMFYUI_WORKFLOW_NODES: list[dict]


class ConfigForm(BaseModel):
    enabled: bool
    engine: str
    openai: OpenAIConfigForm
    automatic1111: Automatic1111ConfigForm
    comfyui: ComfyUIConfigForm


@app.post("/config/update")
async def update_config(form_data: ConfigForm, user=Depends(get_admin_user)):
    app.state.config.ENGINE = form_data.engine
    app.state.config.ENABLED = form_data.enabled

    app.state.config.OPENAI_API_BASE_URL = form_data.openai.OPENAI_API_BASE_URL
    app.state.config.OPENAI_API_KEY = form_data.openai.OPENAI_API_KEY

    app.state.config.AUTOMATIC1111_BASE_URL = (
        form_data.automatic1111.AUTOMATIC1111_BASE_URL
    )
    app.state.config.AUTOMATIC1111_API_AUTH = (
        form_data.automatic1111.AUTOMATIC1111_API_AUTH
    )

    app.state.config.COMFYUI_BASE_URL = form_data.comfyui.COMFYUI_BASE_URL.strip("/")
    app.state.config.COMFYUI_WORKFLOW = form_data.comfyui.COMFYUI_WORKFLOW
    app.state.config.COMFYUI_WORKFLOW_NODES = form_data.comfyui.COMFYUI_WORKFLOW_NODES

    return {
        "enabled": app.state.config.ENABLED,
        "engine": app.state.config.ENGINE,
        "openai": {
            "OPENAI_API_BASE_URL": app.state.config.OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": app.state.config.OPENAI_API_KEY,
        },
        "automatic1111": {
            "AUTOMATIC1111_BASE_URL": app.state.config.AUTOMATIC1111_BASE_URL,
            "AUTOMATIC1111_API_AUTH": app.state.config.AUTOMATIC1111_API_AUTH,
        },
        "comfyui": {
            "COMFYUI_BASE_URL": app.state.config.COMFYUI_BASE_URL,
            "COMFYUI_WORKFLOW": app.state.config.COMFYUI_WORKFLOW,
            "COMFYUI_WORKFLOW_NODES": app.state.config.COMFYUI_WORKFLOW_NODES,
        },
    }


def get_automatic1111_api_auth():
    if app.state.config.AUTOMATIC1111_API_AUTH is None:
        return ""
    else:
        auth1111_byte_string = app.state.config.AUTOMATIC1111_API_AUTH.encode("utf-8")
        auth1111_base64_encoded_bytes = base64.b64encode(auth1111_byte_string)
        auth1111_base64_encoded_string = auth1111_base64_encoded_bytes.decode("utf-8")
        return f"Basic {auth1111_base64_encoded_string}"


@app.get("/config/url/verify")
async def verify_url(user=Depends(get_admin_user)):
    if app.state.config.ENGINE == "automatic1111":
        try:
            r = requests.get(
                url=f"{app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options",
                headers={"authorization": get_automatic1111_api_auth()},
            )
            r.raise_for_status()
            return True
        except Exception:
            app.state.config.ENABLED = False
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.INVALID_URL)
    elif app.state.config.ENGINE == "comfyui":
        try:
            r = requests.get(url=f"{app.state.config.COMFYUI_BASE_URL}/object_info")
            r.raise_for_status()
            return True
        except Exception:
            app.state.config.ENABLED = False
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.INVALID_URL)
    else:
        return True


def set_image_model(model: str):
    log.info(f"Setting image model to {model}")
    app.state.config.MODEL = model
    if app.state.config.ENGINE in ["", "automatic1111"]:
        api_auth = get_automatic1111_api_auth()
        r = requests.get(
            url=f"{app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options",
            headers={"authorization": api_auth},
        )
        options = r.json()
        if model != options["sd_model_checkpoint"]:
            options["sd_model_checkpoint"] = model
            r = requests.post(
                url=f"{app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options",
                json=options,
                headers={"authorization": api_auth},
            )
    return app.state.config.MODEL


def get_image_model():
    if app.state.config.ENGINE == "openai":
        return app.state.config.MODEL if app.state.config.MODEL else "dall-e-2"
    elif app.state.config.ENGINE == "comfyui":
        return app.state.config.MODEL if app.state.config.MODEL else ""
    elif app.state.config.ENGINE == "automatic1111" or app.state.config.ENGINE == "":
        try:
            r = requests.get(
                url=f"{app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options",
                headers={"authorization": get_automatic1111_api_auth()},
            )
            options = r.json()
            return options["sd_model_checkpoint"]
        except Exception as e:
            app.state.config.ENABLED = False
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))


class ImageConfigForm(BaseModel):
    MODEL: str
    IMAGE_SIZE: str
    IMAGE_STEPS: int


@app.get("/image/config")
async def get_image_config(user=Depends(get_admin_user)):
    return {
        "MODEL": app.state.config.MODEL,
        "IMAGE_SIZE": app.state.config.IMAGE_SIZE,
        "IMAGE_STEPS": app.state.config.IMAGE_STEPS,
    }


@app.post("/image/config/update")
async def update_image_config(form_data: ImageConfigForm, user=Depends(get_admin_user)):

    set_image_model(form_data.MODEL)

    pattern = r"^\d+x\d+$"
    if re.match(pattern, form_data.IMAGE_SIZE):
        app.state.config.IMAGE_SIZE = form_data.IMAGE_SIZE
    else:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.INCORRECT_FORMAT("  (e.g., 512x512)."),
        )

    if form_data.IMAGE_STEPS >= 0:
        app.state.config.IMAGE_STEPS = form_data.IMAGE_STEPS
    else:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.INCORRECT_FORMAT("  (e.g., 50)."),
        )

    return {
        "MODEL": app.state.config.MODEL,
        "IMAGE_SIZE": app.state.config.IMAGE_SIZE,
        "IMAGE_STEPS": app.state.config.IMAGE_STEPS,
    }


@app.get("/models")
def get_models(user=Depends(get_verified_user)):
    try:
        if app.state.config.ENGINE == "openai":
            return [
                {"id": "dall-e-2", "name": "DALL·E 2"},
                {"id": "dall-e-3", "name": "DALL·E 3"},
            ]
        elif app.state.config.ENGINE == "comfyui":
            # TODO - get models from comfyui
            r = requests.get(url=f"{app.state.config.COMFYUI_BASE_URL}/object_info")
            info = r.json()

            workflow = json.loads(app.state.config.COMFYUI_WORKFLOW)
            model_node_id = None

            for node in app.state.config.COMFYUI_WORKFLOW_NODES:
                if node["type"] == "model":
                    if node["node_ids"]:
                        model_node_id = node["node_ids"][0]
                    break

            if model_node_id:
                model_list_key = None

                print(workflow[model_node_id]["class_type"])
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
            app.state.config.ENGINE == "automatic1111" or app.state.config.ENGINE == ""
        ):
            r = requests.get(
                url=f"{app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/sd-models",
                headers={"authorization": get_automatic1111_api_auth()},
            )
            models = r.json()
            return list(
                map(
                    lambda model: {"id": model["title"], "name": model["model_name"]},
                    models,
                )
            )
    except Exception as e:
        app.state.config.ENABLED = False
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))


class GenerateImageForm(BaseModel):
    model: Optional[str] = None
    prompt: str
    size: Optional[str] = None
    n: int = 1
    negative_prompt: Optional[str] = None


def save_b64_image(b64_str):
    try:
        image_id = str(uuid.uuid4())

        if "," in b64_str:
            header, encoded = b64_str.split(",", 1)
            mime_type = header.split(";")[0]

            img_data = base64.b64decode(encoded)
            image_format = mimetypes.guess_extension(mime_type)

            image_filename = f"{image_id}{image_format}"
            file_path = IMAGE_CACHE_DIR / f"{image_filename}"
            with open(file_path, "wb") as f:
                f.write(img_data)
            return image_filename
        else:
            image_filename = f"{image_id}.png"
            file_path = IMAGE_CACHE_DIR.joinpath(image_filename)

            img_data = base64.b64decode(b64_str)

            # Write the image data to a file
            with open(file_path, "wb") as f:
                f.write(img_data)
            return image_filename

    except Exception as e:
        log.exception(f"Error saving image: {e}")
        return None


def save_url_image(url):
    image_id = str(uuid.uuid4())
    try:
        r = requests.get(url)
        r.raise_for_status()
        if r.headers["content-type"].split("/")[0] == "image":
            mime_type = r.headers["content-type"]
            image_format = mimetypes.guess_extension(mime_type)

            if not image_format:
                raise ValueError("Could not determine image type from MIME type")

            image_filename = f"{image_id}{image_format}"

            file_path = IMAGE_CACHE_DIR.joinpath(f"{image_filename}")
            with open(file_path, "wb") as image_file:
                for chunk in r.iter_content(chunk_size=8192):
                    image_file.write(chunk)
            return image_filename
        else:
            log.error("Url does not point to an image.")
            return None

    except Exception as e:
        log.exception(f"Error saving image: {e}")
        return None


@app.post("/generations")
async def image_generations(
    form_data: GenerateImageForm,
    user=Depends(get_verified_user),
):
    width, height = tuple(map(int, app.state.config.IMAGE_SIZE.split("x")))

    r = None
    try:
        if app.state.config.ENGINE == "openai":
            headers = {}
            headers["Authorization"] = f"Bearer {app.state.config.OPENAI_API_KEY}"
            headers["Content-Type"] = "application/json"

            data = {
                "model": (
                    app.state.config.MODEL
                    if app.state.config.MODEL != ""
                    else "dall-e-2"
                ),
                "prompt": form_data.prompt,
                "n": form_data.n,
                "size": (
                    form_data.size if form_data.size else app.state.config.IMAGE_SIZE
                ),
                "response_format": "b64_json",
            }

            r = requests.post(
                url=f"{app.state.config.OPENAI_API_BASE_URL}/images/generations",
                json=data,
                headers=headers,
            )

            r.raise_for_status()
            res = r.json()

            images = []

            for image in res["data"]:
                image_filename = save_b64_image(image["b64_json"])
                images.append({"url": f"/cache/image/generations/{image_filename}"})
                file_body_path = IMAGE_CACHE_DIR.joinpath(f"{image_filename}.json")

                with open(file_body_path, "w") as f:
                    json.dump(data, f)

            return images

        elif app.state.config.ENGINE == "comfyui":
            data = {
                "prompt": form_data.prompt,
                "width": width,
                "height": height,
                "n": form_data.n,
            }

            if app.state.config.IMAGE_STEPS is not None:
                data["steps"] = app.state.config.IMAGE_STEPS

            if form_data.negative_prompt is not None:
                data["negative_prompt"] = form_data.negative_prompt

            form_data = ComfyUIGenerateImageForm(
                **{
                    "workflow": ComfyUIWorkflow(
                        **{
                            "workflow": app.state.config.COMFYUI_WORKFLOW,
                            "nodes": app.state.config.COMFYUI_WORKFLOW_NODES,
                        }
                    ),
                    **data,
                }
            )
            res = await comfyui_generate_image(
                app.state.config.MODEL,
                form_data,
                user.id,
                app.state.config.COMFYUI_BASE_URL,
            )
            log.debug(f"res: {res}")

            images = []

            for image in res["data"]:
                image_filename = save_url_image(image["url"])
                images.append({"url": f"/cache/image/generations/{image_filename}"})
                file_body_path = IMAGE_CACHE_DIR.joinpath(f"{image_filename}.json")

                with open(file_body_path, "w") as f:
                    json.dump(form_data.model_dump(exclude_none=True), f)

            log.debug(f"images: {images}")
            return images
        elif (
            app.state.config.ENGINE == "automatic1111" or app.state.config.ENGINE == ""
        ):
            if form_data.model:
                set_image_model(form_data.model)

            data = {
                "prompt": form_data.prompt,
                "batch_size": form_data.n,
                "width": width,
                "height": height,
            }

            if app.state.config.IMAGE_STEPS is not None:
                data["steps"] = app.state.config.IMAGE_STEPS

            if form_data.negative_prompt is not None:
                data["negative_prompt"] = form_data.negative_prompt

            # Use asyncio.to_thread for the requests.post call
            r = await asyncio.to_thread(
                requests.post,
                url=f"{app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/txt2img",
                json=data,
                headers={"authorization": get_automatic1111_api_auth()},
            )

            res = r.json()
            log.debug(f"res: {res}")

            images = []

            for image in res["images"]:
                image_filename = save_b64_image(image)
                images.append({"url": f"/cache/image/generations/{image_filename}"})
                file_body_path = IMAGE_CACHE_DIR.joinpath(f"{image_filename}.json")

                with open(file_body_path, "w") as f:
                    json.dump({**data, "info": res["info"]}, f)

            return images
    except Exception as e:
        error = e
        if r != None:
            data = r.json()
            if "error" in data:
                error = data["error"]["message"]
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(error))

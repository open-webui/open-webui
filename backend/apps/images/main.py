import re
import requests
from fastapi import (
    FastAPI,
    Request,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel

from constants import ERROR_MESSAGES
from utils.utils import (
    get_current_user,
    get_admin_user,
)

from apps.images.utils.comfyui import ImageGenerationPayload, comfyui_generate_image
from utils.misc import calculate_sha256
from typing import Optional
from pydantic import BaseModel
from pathlib import Path
import mimetypes
import uuid
import base64
import json
import logging

from config import (
    SRC_LOG_LEVELS,
    CACHE_DIR,
    IMAGE_GENERATION_ENGINE,
    ENABLE_IMAGE_GENERATION,
    AUTOMATIC1111_BASE_URL,
    COMFYUI_BASE_URL,
    IMAGES_OPENAI_API_BASE_URL,
    IMAGES_OPENAI_API_KEY,
    IMAGE_GENERATION_MODEL,
    IMAGE_SIZE,
    IMAGE_STEPS,
    AppConfig,
)


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["IMAGES"])

IMAGE_CACHE_DIR = Path(CACHE_DIR).joinpath("./image/generations/")
IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
app.state.config.COMFYUI_BASE_URL = COMFYUI_BASE_URL


app.state.config.IMAGE_SIZE = IMAGE_SIZE
app.state.config.IMAGE_STEPS = IMAGE_STEPS


@app.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "engine": app.state.config.ENGINE,
        "enabled": app.state.config.ENABLED,
    }


class ConfigUpdateForm(BaseModel):
    engine: str
    enabled: bool


@app.post("/config/update")
async def update_config(form_data: ConfigUpdateForm, user=Depends(get_admin_user)):
    app.state.config.ENGINE = form_data.engine
    app.state.config.ENABLED = form_data.enabled
    return {
        "engine": app.state.config.ENGINE,
        "enabled": app.state.config.ENABLED,
    }


class EngineUrlUpdateForm(BaseModel):
    AUTOMATIC1111_BASE_URL: Optional[str] = None
    COMFYUI_BASE_URL: Optional[str] = None


@app.get("/url")
async def get_engine_url(user=Depends(get_admin_user)):
    return {
        "AUTOMATIC1111_BASE_URL": app.state.config.AUTOMATIC1111_BASE_URL,
        "COMFYUI_BASE_URL": app.state.config.COMFYUI_BASE_URL,
    }


@app.post("/url/update")
async def update_engine_url(
    form_data: EngineUrlUpdateForm, user=Depends(get_admin_user)
):

    if form_data.AUTOMATIC1111_BASE_URL == None:
        app.state.config.AUTOMATIC1111_BASE_URL = AUTOMATIC1111_BASE_URL
    else:
        url = form_data.AUTOMATIC1111_BASE_URL.strip("/")
        try:
            r = requests.head(url)
            app.state.config.AUTOMATIC1111_BASE_URL = url
        except Exception as e:
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))

    if form_data.COMFYUI_BASE_URL == None:
        app.state.config.COMFYUI_BASE_URL = COMFYUI_BASE_URL
    else:
        url = form_data.COMFYUI_BASE_URL.strip("/")

        try:
            r = requests.head(url)
            app.state.config.COMFYUI_BASE_URL = url
        except Exception as e:
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))

    return {
        "AUTOMATIC1111_BASE_URL": app.state.config.AUTOMATIC1111_BASE_URL,
        "COMFYUI_BASE_URL": app.state.config.COMFYUI_BASE_URL,
        "status": True,
    }


class OpenAIConfigUpdateForm(BaseModel):
    url: str
    key: str


@app.get("/openai/config")
async def get_openai_config(user=Depends(get_admin_user)):
    return {
        "OPENAI_API_BASE_URL": app.state.config.OPENAI_API_BASE_URL,
        "OPENAI_API_KEY": app.state.config.OPENAI_API_KEY,
    }


@app.post("/openai/config/update")
async def update_openai_config(
    form_data: OpenAIConfigUpdateForm, user=Depends(get_admin_user)
):
    if form_data.key == "":
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.API_KEY_NOT_FOUND)

    app.state.config.OPENAI_API_BASE_URL = form_data.url
    app.state.config.OPENAI_API_KEY = form_data.key

    return {
        "status": True,
        "OPENAI_API_BASE_URL": app.state.config.OPENAI_API_BASE_URL,
        "OPENAI_API_KEY": app.state.config.OPENAI_API_KEY,
    }


class ImageSizeUpdateForm(BaseModel):
    size: str


@app.get("/size")
async def get_image_size(user=Depends(get_admin_user)):
    return {"IMAGE_SIZE": app.state.config.IMAGE_SIZE}


@app.post("/size/update")
async def update_image_size(
    form_data: ImageSizeUpdateForm, user=Depends(get_admin_user)
):
    pattern = r"^\d+x\d+$"  # Regular expression pattern
    if re.match(pattern, form_data.size):
        app.state.config.IMAGE_SIZE = form_data.size
        return {
            "IMAGE_SIZE": app.state.config.IMAGE_SIZE,
            "status": True,
        }
    else:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.INCORRECT_FORMAT("  (e.g., 512x512)."),
        )


class ImageStepsUpdateForm(BaseModel):
    steps: int


@app.get("/steps")
async def get_image_size(user=Depends(get_admin_user)):
    return {"IMAGE_STEPS": app.state.config.IMAGE_STEPS}


@app.post("/steps/update")
async def update_image_size(
    form_data: ImageStepsUpdateForm, user=Depends(get_admin_user)
):
    if form_data.steps >= 0:
        app.state.config.IMAGE_STEPS = form_data.steps
        return {
            "IMAGE_STEPS": app.state.config.IMAGE_STEPS,
            "status": True,
        }
    else:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.INCORRECT_FORMAT("  (e.g., 50)."),
        )


@app.get("/models")
def get_models(user=Depends(get_current_user)):
    try:
        if app.state.config.ENGINE == "openai":
            return [
                {"id": "dall-e-2", "name": "DALL·E 2"},
                {"id": "dall-e-3", "name": "DALL·E 3"},
            ]
        elif app.state.config.ENGINE == "comfyui":

            r = requests.get(url=f"{app.state.config.COMFYUI_BASE_URL}/object_info")
            info = r.json()

            return list(
                map(
                    lambda model: {"id": model, "name": model},
                    info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0],
                )
            )

        else:
            r = requests.get(
                url=f"{app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/sd-models"
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


@app.get("/models/default")
async def get_default_model(user=Depends(get_admin_user)):
    try:
        if app.state.config.ENGINE == "openai":
            return {
                "model": (
                    app.state.config.MODEL if app.state.config.MODEL else "dall-e-2"
                )
            }
        elif app.state.config.ENGINE == "comfyui":
            return {"model": (app.state.config.MODEL if app.state.config.MODEL else "")}
        else:
            r = requests.get(
                url=f"{app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options"
            )
            options = r.json()
            return {"model": options["sd_model_checkpoint"]}
    except Exception as e:
        app.state.config.ENABLED = False
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))


class UpdateModelForm(BaseModel):
    model: str


def set_model_handler(model: str):
    if app.state.config.ENGINE in ["openai", "comfyui"]:
        app.state.config.MODEL = model
        return app.state.config.MODEL
    else:
        r = requests.get(
            url=f"{app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options"
        )
        options = r.json()

        if model != options["sd_model_checkpoint"]:
            options["sd_model_checkpoint"] = model
            r = requests.post(
                url=f"{app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options",
                json=options,
            )

        return options


@app.post("/models/default/update")
def update_default_model(
    form_data: UpdateModelForm,
    user=Depends(get_current_user),
):
    return set_model_handler(form_data.model)


class GenerateImageForm(BaseModel):
    model: Optional[str] = None
    prompt: str
    n: int = 1
    size: Optional[str] = None
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
            log.error(f"Url does not point to an image.")
            return None

    except Exception as e:
        log.exception(f"Error saving image: {e}")
        return None


@app.post("/generations")
def generate_image(
    form_data: GenerateImageForm,
    user=Depends(get_current_user),
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

            data = ImageGenerationPayload(**data)

            res = comfyui_generate_image(
                app.state.config.MODEL,
                data,
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
                    json.dump(data.model_dump(exclude_none=True), f)

            log.debug(f"images: {images}")
            return images
        else:
            if form_data.model:
                set_model_handler(form_data.model)

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

            r = requests.post(
                url=f"{app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/txt2img",
                json=data,
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

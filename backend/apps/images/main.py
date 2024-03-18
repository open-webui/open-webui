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
from utils.misc import calculate_sha256
from typing import Optional
from pydantic import BaseModel
from pathlib import Path
import uuid
import base64
import json

from config import CACHE_DIR, AUTOMATIC1111_BASE_URL


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

app.state.ENGINE = ""
app.state.ENABLED = False

app.state.OPENAI_API_KEY = ""
app.state.MODEL = ""


app.state.AUTOMATIC1111_BASE_URL = AUTOMATIC1111_BASE_URL

app.state.IMAGE_SIZE = "512x512"
app.state.IMAGE_STEPS = 50


@app.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {"engine": app.state.ENGINE, "enabled": app.state.ENABLED}


class ConfigUpdateForm(BaseModel):
    engine: str
    enabled: bool


@app.post("/config/update")
async def update_config(form_data: ConfigUpdateForm, user=Depends(get_admin_user)):
    app.state.ENGINE = form_data.engine
    app.state.ENABLED = form_data.enabled
    return {"engine": app.state.ENGINE, "enabled": app.state.ENABLED}


class UrlUpdateForm(BaseModel):
    url: str


@app.get("/url")
async def get_automatic1111_url(user=Depends(get_admin_user)):
    return {"AUTOMATIC1111_BASE_URL": app.state.AUTOMATIC1111_BASE_URL}


@app.post("/url/update")
async def update_automatic1111_url(
    form_data: UrlUpdateForm, user=Depends(get_admin_user)
):

    if form_data.url == "":
        app.state.AUTOMATIC1111_BASE_URL = AUTOMATIC1111_BASE_URL
    else:
        url = form_data.url.strip("/")
        try:
            r = requests.head(url)
            app.state.AUTOMATIC1111_BASE_URL = url
        except Exception as e:
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))

    return {
        "AUTOMATIC1111_BASE_URL": app.state.AUTOMATIC1111_BASE_URL,
        "status": True,
    }


class OpenAIKeyUpdateForm(BaseModel):
    key: str


@app.get("/key")
async def get_openai_key(user=Depends(get_admin_user)):
    return {"OPENAI_API_KEY": app.state.OPENAI_API_KEY}


@app.post("/key/update")
async def update_openai_key(
    form_data: OpenAIKeyUpdateForm, user=Depends(get_admin_user)
):

    if form_data.key == "":
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.API_KEY_NOT_FOUND)

    app.state.OPENAI_API_KEY = form_data.key
    return {
        "OPENAI_API_KEY": app.state.OPENAI_API_KEY,
        "status": True,
    }


class ImageSizeUpdateForm(BaseModel):
    size: str


@app.get("/size")
async def get_image_size(user=Depends(get_admin_user)):
    return {"IMAGE_SIZE": app.state.IMAGE_SIZE}


@app.post("/size/update")
async def update_image_size(
    form_data: ImageSizeUpdateForm, user=Depends(get_admin_user)
):
    pattern = r"^\d+x\d+$"  # Regular expression pattern
    if re.match(pattern, form_data.size):
        app.state.IMAGE_SIZE = form_data.size
        return {
            "IMAGE_SIZE": app.state.IMAGE_SIZE,
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
    return {"IMAGE_STEPS": app.state.IMAGE_STEPS}


@app.post("/steps/update")
async def update_image_size(
    form_data: ImageStepsUpdateForm, user=Depends(get_admin_user)
):
    if form_data.steps >= 0:
        app.state.IMAGE_STEPS = form_data.steps
        return {
            "IMAGE_STEPS": app.state.IMAGE_STEPS,
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
        if app.state.ENGINE == "openai":
            return [
                {"id": "dall-e-2", "name": "DALL·E 2"},
                {"id": "dall-e-3", "name": "DALL·E 3"},
            ]
        else:
            r = requests.get(
                url=f"{app.state.AUTOMATIC1111_BASE_URL}/sdapi/v1/sd-models"
            )
            models = r.json()
            return list(
                map(
                    lambda model: {"id": model["title"], "name": model["model_name"]},
                    models,
                )
            )
    except Exception as e:
        app.state.ENABLED = False
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))


@app.get("/models/default")
async def get_default_model(user=Depends(get_admin_user)):
    try:
        if app.state.ENGINE == "openai":
            return {"model": app.state.MODEL if app.state.MODEL else "dall-e-2"}
        else:
            r = requests.get(url=f"{app.state.AUTOMATIC1111_BASE_URL}/sdapi/v1/options")
            options = r.json()
            return {"model": options["sd_model_checkpoint"]}
    except Exception as e:
        app.state.ENABLED = False
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))


class UpdateModelForm(BaseModel):
    model: str


def set_model_handler(model: str):

    if app.state.ENGINE == "openai":
        app.state.MODEL = model
        return app.state.MODEL
    else:
        r = requests.get(url=f"{app.state.AUTOMATIC1111_BASE_URL}/sdapi/v1/options")
        options = r.json()

        if model != options["sd_model_checkpoint"]:
            options["sd_model_checkpoint"] = model
            r = requests.post(
                url=f"{app.state.AUTOMATIC1111_BASE_URL}/sdapi/v1/options", json=options
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
    image_id = str(uuid.uuid4())
    file_path = IMAGE_CACHE_DIR.joinpath(f"{image_id}.png")

    try:
        # Split the base64 string to get the actual image data
        img_data = base64.b64decode(b64_str)

        # Write the image data to a file
        with open(file_path, "wb") as f:
            f.write(img_data)

        return image_id
    except Exception as e:
        print(f"Error saving image: {e}")
        return None


@app.post("/generations")
def generate_image(
    form_data: GenerateImageForm,
    user=Depends(get_current_user),
):

    r = None
    try:
        if app.state.ENGINE == "openai":

            headers = {}
            headers["Authorization"] = f"Bearer {app.state.OPENAI_API_KEY}"
            headers["Content-Type"] = "application/json"

            data = {
                "model": app.state.MODEL if app.state.MODEL != "" else "dall-e-2",
                "prompt": form_data.prompt,
                "n": form_data.n,
                "size": form_data.size if form_data.size else app.state.IMAGE_SIZE,
                "response_format": "b64_json",
            }

            r = requests.post(
                url=f"https://api.openai.com/v1/images/generations",
                json=data,
                headers=headers,
            )

            r.raise_for_status()
            res = r.json()

            images = []

            for image in res["data"]:
                image_id = save_b64_image(image["b64_json"])
                images.append({"url": f"/cache/image/generations/{image_id}.png"})
                file_body_path = IMAGE_CACHE_DIR.joinpath(f"{image_id}.json")

                with open(file_body_path, "w") as f:
                    json.dump(data, f)

            return images

        else:
            if form_data.model:
                set_model_handler(form_data.model)

            width, height = tuple(map(int, app.state.IMAGE_SIZE.split("x")))

            data = {
                "prompt": form_data.prompt,
                "batch_size": form_data.n,
                "width": width,
                "height": height,
            }

            if app.state.IMAGE_STEPS != None:
                data["steps"] = app.state.IMAGE_STEPS

            if form_data.negative_prompt != None:
                data["negative_prompt"] = form_data.negative_prompt

            r = requests.post(
                url=f"{app.state.AUTOMATIC1111_BASE_URL}/sdapi/v1/txt2img",
                json=data,
            )

            res = r.json()

            print(res)

            images = []

            for image in res["images"]:
                image_id = save_b64_image(image)
                images.append({"url": f"/cache/image/generations/{image_id}.png"})
                file_body_path = IMAGE_CACHE_DIR.joinpath(f"{image_id}.json")

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

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
from config import AUTOMATIC1111_BASE_URL

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.AUTOMATIC1111_BASE_URL = AUTOMATIC1111_BASE_URL
app.state.ENABLED = app.state.AUTOMATIC1111_BASE_URL != ""
app.state.IMAGE_SIZE = "512x512"
app.state.IMAGE_STEPS = 50


@app.get("/enabled", response_model=bool)
async def get_enable_status(request: Request, user=Depends(get_admin_user)):
    return app.state.ENABLED


@app.get("/enabled/toggle", response_model=bool)
async def toggle_enabled(request: Request, user=Depends(get_admin_user)):
    try:
        r = requests.head(app.state.AUTOMATIC1111_BASE_URL)
        app.state.ENABLED = not app.state.ENABLED
        return app.state.ENABLED
    except Exception as e:
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))


class UrlUpdateForm(BaseModel):
    url: str


@app.get("/url")
async def get_openai_url(user=Depends(get_admin_user)):
    return {"AUTOMATIC1111_BASE_URL": app.state.AUTOMATIC1111_BASE_URL}


@app.post("/url/update")
async def update_openai_url(form_data: UrlUpdateForm, user=Depends(get_admin_user)):

    if form_data.url == "":
        app.state.AUTOMATIC1111_BASE_URL = AUTOMATIC1111_BASE_URL
    else:
        app.state.AUTOMATIC1111_BASE_URL = form_data.url.strip("/")

    return {
        "AUTOMATIC1111_BASE_URL": app.state.AUTOMATIC1111_BASE_URL,
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
        r = requests.get(url=f"{app.state.AUTOMATIC1111_BASE_URL}/sdapi/v1/sd-models")
        models = r.json()
        return models
    except Exception as e:
        app.state.ENABLED = False
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))


@app.get("/models/default")
async def get_default_model(user=Depends(get_admin_user)):
    try:
        r = requests.get(url=f"{app.state.AUTOMATIC1111_BASE_URL}/sdapi/v1/options")
        options = r.json()

        return {"model": options["sd_model_checkpoint"]}
    except Exception as e:
        app.state.ENABLED = False
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))


class UpdateModelForm(BaseModel):
    model: str


def set_model_handler(model: str):
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
    size: str = "512x512"
    negative_prompt: Optional[str] = None


@app.post("/generations")
def generate_image(
    form_data: GenerateImageForm,
    user=Depends(get_current_user),
):

    print(form_data)

    try:
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

        print(data)

        r = requests.post(
            url=f"{app.state.AUTOMATIC1111_BASE_URL}/sdapi/v1/txt2img",
            json=data,
        )

        return r.json()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))

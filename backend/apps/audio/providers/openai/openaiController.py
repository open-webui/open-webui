from fastapi import (APIRouter, Request, HTTPException, Depends)
from fastapi.responses import FileResponse
import requests
import hashlib
import json

from apps.audio.settings import get_config, SPEECH_CACHE_DIR, log
from apps.audio.providers.openai.openaiModel import OpenAIConfigUpdateForm
from apps.audio.providers.openai.openaiService import get_openai_tts_config, get_openai_stt_config
from utils.utils import (get_verified_user, get_admin_user)
from constants import ERROR_MESSAGES


router = APIRouter(
     prefix="/openai",
     dependencies=[Depends(get_config)]
)

@router.post("tts/config/update")
async def update_openai_tts_config(
    form_data: OpenAIConfigUpdateForm, user=Depends(get_admin_user), config=Depends(get_config)
):
    if form_data.OPENAI_API_KEY == "":
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.API_KEY_NOT_FOUND)

    config.TTS_OPENAI_API_BASE_URL = form_data.OPENAI_API_BASE_URL
    config.TTS_OPENAI_API_KEY = form_data.OPENAI_API_KEY

    return get_openai_tts_config()


@router.post("stt/config/update")
async def update_openai_stt_config(
    form_data: OpenAIConfigUpdateForm, user=Depends(get_admin_user), config =Depends(get_config)
):
    if form_data.OPENAI_API_KEY == "":
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.API_KEY_NOT_FOUND)

    config.STT_OPENAI_API_BASE_URL = form_data.OPENAI_API_BASE_URL
    config.STT_OPENAI_API_KEY = form_data.OPENAI_API_KEY

    return get_openai_stt_config()


@router.post("/speech")
async def speech(request: Request, user=Depends(get_verified_user), config=Depends(get_config)):
    body = await request.body()
    name = hashlib.sha256(body).hexdigest()

    file_path = SPEECH_CACHE_DIR.joinpath(f"{name}.mp3")
    file_body_path = SPEECH_CACHE_DIR.joinpath(f"{name}.json")

    # Check if the file already exists in the cache
    if file_path.is_file():
        return FileResponse(file_path)

    headers = {}
    headers["Authorization"] = f"Bearer {config.TTS_OPENAI_API_KEY}"
    headers["Content-Type"] = "application/json"

    try:
        body = body.decode("utf-8")
        body = json.loads(body)
        body["model"] = config.TTS_MODEL
        body = json.dumps(body).encode("utf-8")
    except Exception as e:
        pass

    r = None
    try:
        r = requests.post(
            url=f"{config.TTS_OPENAI_API_BASE_URL}/audio/speech",
            data=body,
            headers=headers,
            stream=True,
        )

        r.raise_for_status()

        # Save the streaming content to a file
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        with open(file_body_path, "w") as f:
            json.dump(json.loads(body.decode("utf-8")), f)

        # Return the saved file
        return FileResponse(file_path)

    except Exception as e:
        log.exception(e)
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"External: {res['error']['message']}"
            except:
                error_detail = f"External: {e}"

        raise HTTPException(
            status_code=r.status_code if r != None else 500,
            detail=error_detail,
        )

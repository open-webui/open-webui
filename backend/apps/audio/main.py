import os
from fastapi import (
    Depends,
    HTTPException,
    status,
    UploadFile,
    File
)
from apps.audio.settings import app, log
from apps.audio.providers.alltalk.alltalkController import app as alltalk_app
from apps.audio.providers.openai.openai import router as openai_app

from faster_whisper import WhisperModel

from constants import ERROR_MESSAGES
from utils.utils import (get_current_user, get_admin_user)
from config import (
    UPLOAD_DIR,
    WHISPER_MODEL,
    WHISPER_MODEL_DIR,
    WHISPER_MODEL_AUTO_UPDATE,
    DEVICE_TYPE,
)

app.include_router(alltalk_app)
app.include_router(openai_app)

# setting device type for whisper model
whisper_device_type = DEVICE_TYPE if DEVICE_TYPE and DEVICE_TYPE == "cuda" else "cpu"
log.info(f"whisper_device_type: {whisper_device_type}")


@app.get("/config")
async def get_audio_config(user=Depends(get_admin_user)):
    return {
        "openai":{
            "OPENAI_API_BASE_URL": app.state.config.OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": app.state.config.OPENAI_API_KEY,
            "OPENAI_API_MODEL": app.state.config.OPENAI_API_MODEL,
            "OPENAI_API_VOICE": app.state.config.OPENAI_API_VOICE,
        },
        "alltalk":{
            "ALLTALK_API_BASE_URL": app.state.config.ALLTALK_API_BASE_URL,
            "ALLTALK_API_MODEL": app.state.config.ALLTALK_API_MODEL,
            "ALLTALK_API_VOICE": app.state.config.ALLTALK_API_VOICE,
        }
    }


@app.post("/transcriptions")
def transcribe(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    log.info(f"file.content_type: {file.content_type}")

    if file.content_type not in ["audio/mpeg", "audio/wav"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_NOT_SUPPORTED,
        )

    try:
        filename = file.filename
        file_path = f"{UPLOAD_DIR}/{filename}"
        contents = file.file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
            f.close()

        whisper_kwargs = {
            "model_size_or_path": WHISPER_MODEL,
            "device": whisper_device_type,
            "compute_type": "int8",
            "download_root": WHISPER_MODEL_DIR,
            "local_files_only": not WHISPER_MODEL_AUTO_UPDATE,
        }

        log.debug(f"whisper_kwargs: {whisper_kwargs}")

        try:
            model = WhisperModel(**whisper_kwargs)
        except:
            log.warning(
                "WhisperModel initialization failed, attempting download with local_files_only=False"
            )
            whisper_kwargs["local_files_only"] = False
            model = WhisperModel(**whisper_kwargs)

        segments, info = model.transcribe(file_path, beam_size=5)
        log.info(
            "Detected language '%s' with probability %f"
            % (info.language, info.language_probability)
        )

        transcript = "".join([segment.text for segment in list(segments)])

        return {"text": transcript.strip()}

    except Exception as e:
        log.exception(e)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )

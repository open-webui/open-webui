import os
from fastapi import (Depends, HTTPException, status, UploadFile, File)
from faster_whisper import WhisperModel
from pydantic import BaseModel
from pydub import AudioSegment
from pydub.utils import mediainfo
import uuid
import requests
import json

from apps.audio.settings import app, log, WHISPER_DEVICE_TYPE
from apps.audio.model import AudioConfigUpdateForm, STTGeneralConfigForm, TTSGeneralConfigForm

from apps.audio.providers.alltalk.alltalkController import app as alltalk_app
from apps.audio.providers.alltalk.alltalkService import get_alltalk_tts_config
from apps.audio.providers.openai.openaiController import router as openai_app
from apps.audio.providers.openai.openaiService import get_openai_tts_config, get_openai_stt_config

from constants import ERROR_MESSAGES
from utils.utils import (get_current_user, get_admin_user)

from config import (
    CACHE_DIR,
    WHISPER_MODEL,
    WHISPER_MODEL_DIR,
    WHISPER_MODEL_AUTO_UPDATE
)

app.include_router(alltalk_app)
app.include_router(openai_app)

def is_mp4_audio(file_path):
    """Check if the given file is an MP4 audio file."""
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return False

    info = mediainfo(file_path)
    if (
        info.get("codec_name") == "aac"
        and info.get("codec_type") == "audio"
        and info.get("codec_tag_string") == "mp4a"
    ):
        return True
    return False


def convert_mp4_to_wav(file_path, output_path):
    """Convert MP4 audio file to WAV format."""
    audio = AudioSegment.from_file(file_path, format="mp4")
    audio.export(output_path, format="wav")
    print(f"Converted {file_path} to {output_path}")


@app.get("/config")
async def get_audio_config(user=Depends(get_admin_user)) -> AudioConfigUpdateForm:
    return {
        "tts": {
            "openai": get_openai_tts_config(),
            "alltalk": get_alltalk_tts_config(),
            "general": {
                "ENGINE": app.state.config.TTS_ENGINE,
                "MODEL": app.state.config.TTS_MODEL,
                "VOICE": app.state.config.TTS_VOICE
            }
        },
        "stt": {
            "openai": get_openai_stt_config(),
            "general": {
                "ENGINE": app.state.config.STT_ENGINE,
                "MODEL": app.state.config.STT_MODEL
            }
        }
    }


@app.post("/general/tts/config/update")
async def update_audio_tts_config(
    form_data: TTSGeneralConfigForm, user=Depends(get_admin_user)
) -> TTSGeneralConfigForm:
    app.state.config.TTS_ENGINE = form_data.ENGINE
    app.state.config.TTS_MODEL = form_data.MODEL
    app.state.config.TTS_VOICE = form_data.VOICE

    return {
        "ENGINE": app.state.config.TTS_ENGINE,
        "MODEL": app.state.config.TTS_MODEL,
        "VOICE": app.state.config.TTS_VOICE
    }


@app.post("/general/stt/config/update")
async def update_audio_stt_config(
    form_data: STTGeneralConfigForm, user=Depends(get_admin_user)
) -> STTGeneralConfigForm:
    app.state.config.STT_ENGINE = form_data.ENGINE
    app.state.config.STT_MODEL = form_data.MODEL

    return {
        "ENGINE": app.state.config.STT_ENGINE,
        "MODEL": app.state.config.STT_MODEL
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
        ext = file.filename.split(".")[-1]

        id = uuid.uuid4()
        filename = f"{id}.{ext}"

        file_dir = f"{CACHE_DIR}/audio/transcriptions"
        os.makedirs(file_dir, exist_ok=True)
        file_path = f"{file_dir}/{filename}"

        print(filename)

        contents = file.file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
            f.close()

        if app.state.config.STT_ENGINE == "":
            whisper_kwargs = {
                "model_size_or_path": WHISPER_MODEL,
                "device": WHISPER_DEVICE_TYPE,
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

            data = {"text": transcript.strip()}

            # save the transcript to a json file
            transcript_file = f"{file_dir}/{id}.json"
            with open(transcript_file, "w") as f:
                json.dump(data, f)

            print(data)

            return data

        elif app.state.config.STT_ENGINE == "openai":
            if is_mp4_audio(file_path):
                print("is_mp4_audio")
                os.rename(file_path, file_path.replace(".wav", ".mp4"))
                # Convert MP4 audio file to WAV format
                convert_mp4_to_wav(file_path.replace(".wav", ".mp4"), file_path)

            headers = {"Authorization": f"Bearer {app.state.config.STT_OPENAI_API_KEY}"}

            files = {"file": (filename, open(file_path, "rb"))}
            data = {"model": "whisper-1"}

            print(files, data)

            r = None
            try:
                r = requests.post(
                    url=f"{app.state.config.STT_OPENAI_API_BASE_URL}/audio/transcriptions",
                    headers=headers,
                    files=files,
                    data=data,
                )

                r.raise_for_status()

                data = r.json()

                # save the transcript to a json file
                transcript_file = f"{file_dir}/{id}.json"
                with open(transcript_file, "w") as f:
                    json.dump(data, f)

                print(data)
                return data
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

    except Exception as e:
        log.exception(e)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )

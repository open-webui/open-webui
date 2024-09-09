import hashlib
import json
import logging
import os
import uuid
from functools import lru_cache
from pathlib import Path

import requests
from open_webui.config import (
    AUDIO_STT_ENGINE,
    AUDIO_STT_MODEL,
    AUDIO_STT_OPENAI_API_BASE_URL,
    AUDIO_STT_OPENAI_API_KEY,
    AUDIO_TTS_API_KEY,
    AUDIO_TTS_ENGINE,
    AUDIO_TTS_MODEL,
    AUDIO_TTS_OPENAI_API_BASE_URL,
    AUDIO_TTS_OPENAI_API_KEY,
    AUDIO_TTS_SPLIT_ON,
    AUDIO_TTS_VOICE,
    CACHE_DIR,
    CORS_ALLOW_ORIGIN,
    DEVICE_TYPE,
    WHISPER_MODEL,
    WHISPER_MODEL_AUTO_UPDATE,
    WHISPER_MODEL_DIR,
    AppConfig,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from open_webui.utils.utils import get_admin_user, get_current_user, get_verified_user
from open_webui.apps.audio.services.audio_compression import AudioCompressionService

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["AUDIO"])

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.config = AppConfig()

app.state.config.STT_OPENAI_API_BASE_URL = AUDIO_STT_OPENAI_API_BASE_URL
app.state.config.STT_OPENAI_API_KEY = AUDIO_STT_OPENAI_API_KEY
app.state.config.STT_ENGINE = AUDIO_STT_ENGINE
app.state.config.STT_MODEL = AUDIO_STT_MODEL

app.state.config.TTS_OPENAI_API_BASE_URL = AUDIO_TTS_OPENAI_API_BASE_URL
app.state.config.TTS_OPENAI_API_KEY = AUDIO_TTS_OPENAI_API_KEY
app.state.config.TTS_ENGINE = AUDIO_TTS_ENGINE
app.state.config.TTS_MODEL = AUDIO_TTS_MODEL
app.state.config.TTS_VOICE = AUDIO_TTS_VOICE
app.state.config.TTS_API_KEY = AUDIO_TTS_API_KEY
app.state.config.TTS_SPLIT_ON = AUDIO_TTS_SPLIT_ON

# setting device type for whisper model
whisper_device_type = DEVICE_TYPE if DEVICE_TYPE and DEVICE_TYPE == "cuda" else "cpu"
log.info(f"whisper_device_type: {whisper_device_type}")

SPEECH_CACHE_DIR = Path(CACHE_DIR).joinpath("./audio/speech/")
SPEECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE_MB = 25  # Maximum file size in megabytes
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert to bytes


class TTSConfigForm(BaseModel):
    OPENAI_API_BASE_URL: str
    OPENAI_API_KEY: str
    API_KEY: str
    ENGINE: str
    MODEL: str
    VOICE: str
    SPLIT_ON: str


class STTConfigForm(BaseModel):
    OPENAI_API_BASE_URL: str
    OPENAI_API_KEY: str
    ENGINE: str
    MODEL: str


class AudioConfigUpdateForm(BaseModel):
    tts: TTSConfigForm
    stt: STTConfigForm


from pydub import AudioSegment
from pydub.utils import mediainfo


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
async def get_audio_config(user=Depends(get_admin_user)):
    return {
        "tts": {
            "OPENAI_API_BASE_URL": app.state.config.TTS_OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": app.state.config.TTS_OPENAI_API_KEY,
            "API_KEY": app.state.config.TTS_API_KEY,
            "ENGINE": app.state.config.TTS_ENGINE,
            "MODEL": app.state.config.TTS_MODEL,
            "VOICE": app.state.config.TTS_VOICE,
            "SPLIT_ON": app.state.config.TTS_SPLIT_ON,
        },
        "stt": {
            "OPENAI_API_BASE_URL": app.state.config.STT_OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": app.state.config.STT_OPENAI_API_KEY,
            "ENGINE": app.state.config.STT_ENGINE,
            "MODEL": app.state.config.STT_MODEL,
        },
    }


@app.post("/config/update")
async def update_audio_config(
    form_data: AudioConfigUpdateForm, user=Depends(get_admin_user)
):
    app.state.config.TTS_OPENAI_API_BASE_URL = form_data.tts.OPENAI_API_BASE_URL
    app.state.config.TTS_OPENAI_API_KEY = form_data.tts.OPENAI_API_KEY
    app.state.config.TTS_API_KEY = form_data.tts.API_KEY
    app.state.config.TTS_ENGINE = form_data.tts.ENGINE
    app.state.config.TTS_MODEL = form_data.tts.MODEL
    app.state.config.TTS_VOICE = form_data.tts.VOICE
    app.state.config.TTS_SPLIT_ON = form_data.tts.SPLIT_ON

    app.state.config.STT_OPENAI_API_BASE_URL = form_data.stt.OPENAI_API_BASE_URL
    app.state.config.STT_OPENAI_API_KEY = form_data.stt.OPENAI_API_KEY
    app.state.config.STT_ENGINE = form_data.stt.ENGINE
    app.state.config.STT_MODEL = form_data.stt.MODEL

    return {
        "tts": {
            "OPENAI_API_BASE_URL": app.state.config.TTS_OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": app.state.config.TTS_OPENAI_API_KEY,
            "API_KEY": app.state.config.TTS_API_KEY,
            "ENGINE": app.state.config.TTS_ENGINE,
            "MODEL": app.state.config.TTS_MODEL,
            "VOICE": app.state.config.TTS_VOICE,
            "SPLIT_ON": app.state.config.TTS_SPLIT_ON,
        },
        "stt": {
            "OPENAI_API_BASE_URL": app.state.config.STT_OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": app.state.config.STT_OPENAI_API_KEY,
            "ENGINE": app.state.config.STT_ENGINE,
            "MODEL": app.state.config.STT_MODEL,
        },
    }


@app.post("/speech")
async def speech(request: Request, user=Depends(get_verified_user)):
    body = await request.body()
    name = hashlib.sha256(body).hexdigest()

    file_path = SPEECH_CACHE_DIR.joinpath(f"{name}.mp3")
    file_body_path = SPEECH_CACHE_DIR.joinpath(f"{name}.json")

    # Check if the file already exists in the cache
    if file_path.is_file():
        return FileResponse(file_path)

    if app.state.config.TTS_ENGINE == "openai":
        headers = {}
        headers["Authorization"] = f"Bearer {app.state.config.TTS_OPENAI_API_KEY}"
        headers["Content-Type"] = "application/json"

        try:
            body = body.decode("utf-8")
            body = json.loads(body)
            body["model"] = app.state.config.TTS_MODEL
            body = json.dumps(body).encode("utf-8")
        except Exception:
            pass

        r = None
        try:
            r = requests.post(
                url=f"{app.state.config.TTS_OPENAI_API_BASE_URL}/audio/speech",
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
                except Exception:
                    error_detail = f"External: {e}"

            raise HTTPException(
                status_code=r.status_code if r != None else 500,
                detail=error_detail,
            )

    elif app.state.config.TTS_ENGINE == "elevenlabs":
        payload = None
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            log.exception(e)
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        voice_id = payload.get("voice", "")

        if voice_id not in get_available_voices():
            raise HTTPException(
                status_code=400,
                detail="Invalid voice id",
            )

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": app.state.config.TTS_API_KEY,
        }

        data = {
            "text": payload["input"],
            "model_id": app.state.config.TTS_MODEL,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
        }

        try:
            r = requests.post(url, json=data, headers=headers)

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
                except Exception:
                    error_detail = f"External: {e}"

            raise HTTPException(
                status_code=r.status_code if r != None else 500,
                detail=error_detail,
            )


def handle_default_stt(file_path: str, file_dir: str, id: uuid.UUID) -> dict:
    from faster_whisper import WhisperModel

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
    except Exception:
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

    # Save the transcript to a JSON file
    transcript_file = f"{file_dir}/{id}.json"
    with open(transcript_file, "w") as f:
        json.dump(data, f)

    return data


def handle_openai_stt(file_path: str, file_dir: str, filename: str, id: uuid.UUID) -> dict:
    if is_mp4_audio(file_path):
        os.rename(file_path, file_path.replace(".wav", ".mp4"))
        # Convert MP4 audio file to WAV format
        convert_mp4_to_wav(file_path.replace(".wav", ".mp4"), file_path)

    headers = {"Authorization": f"Bearer {app.state.config.STT_OPENAI_API_KEY}"}

    files = {"file": (filename, open(file_path, "rb"))}
    data = {"model": app.state.config.STT_MODEL}

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

        # Save the transcript to a JSON file
        transcript_file = f"{file_dir}/{id}.json"
        with open(transcript_file, "w") as f:
            json.dump(data, f)

        return data
    except Exception as e:
        log.exception(e)
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"External: {res['error']['message']}"
            except Exception:
                error_detail = f"External: {e}"

        raise HTTPException(
            status_code=r.status_code if r is not None else 500,
            detail=error_detail,
        )

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

        # Compress the audio if its size exceeds the 25MB limit
        file_size = len(contents)
        print(f"File size before: {file_size}")

        # Pre-compression check:
        # If the file is larger than the maximum allowed size, we attempt to compress it.
        # This avoids unnecessary processing for files that are already small enough.
        if file_size > MAX_FILE_SIZE_BYTES:
            
            # Initialize the AudioCompressionService with optional silence removal
            # Silence removal is enabled here, and the silence duration is set to 3 seconds.
            compression_service = AudioCompressionService()
            
            # Call the compress_audio method to attempt to reduce the file size
            compressed_file_path, filename = compression_service.compress_audio(file_path, MAX_FILE_SIZE_BYTES)
            
            # Post-compression check:
            # If the compressed file path is different from the original, 
            # it means compression was performed and we need to update the file path and size.
            if compressed_file_path != file_path:
                file_path = compressed_file_path
                file_size = os.path.getsize(file_path)  # Get the new size after compression
                print(f"File compressed. New size: {file_size}")
            else:
                # If the file path hasn't changed, it means compression was either not needed 
                # (file was already small enough) or was unsuccessful.
                print("Compression not needed or unsuccessful")

        # Final size check after compression:
        # Even after compression, we must ensure that the file still meets the size limit.
        # If the file size exceeds the limit, we raise an exception.
        print(f"Final file size: {file_size}")
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=ERROR_MESSAGES.FILE_SIZE_EXCEEDS_LIMIT(MAX_FILE_SIZE_BYTES),
            )

        # Handle transcription based on the STT engine configured
        if app.state.config.STT_ENGINE == "":
            data = handle_default_stt(file_path, file_dir, id)
        elif app.state.config.STT_ENGINE == "openai":
            data = handle_openai_stt(file_path, file_dir, filename, id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported STT engine.",
            )
        
        return data

    except Exception as e:
        log.exception(e)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


def get_available_models() -> list[dict]:
    if app.state.config.TTS_ENGINE == "openai":
        return [{"id": "tts-1"}, {"id": "tts-1-hd"}]
    elif app.state.config.TTS_ENGINE == "elevenlabs":
        headers = {
            "xi-api-key": app.state.config.TTS_API_KEY,
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(
                "https://api.elevenlabs.io/v1/models", headers=headers
            )
            response.raise_for_status()
            models = response.json()
            return [
                {"name": model["name"], "id": model["model_id"]} for model in models
            ]
        except requests.RequestException as e:
            log.error(f"Error fetching voices: {str(e)}")
    return []


@app.get("/models")
async def get_models(user=Depends(get_verified_user)):
    return {"models": get_available_models()}


def get_available_voices() -> dict:
    """Returns {voice_id: voice_name} dict"""
    ret = {}
    if app.state.config.TTS_ENGINE == "openai":
        ret = {
            "alloy": "alloy",
            "echo": "echo",
            "fable": "fable",
            "onyx": "onyx",
            "nova": "nova",
            "shimmer": "shimmer",
        }
    elif app.state.config.TTS_ENGINE == "elevenlabs":
        try:
            ret = get_elevenlabs_voices()
        except Exception:
            # Avoided @lru_cache with exception
            pass

    return ret


@lru_cache
def get_elevenlabs_voices() -> dict:
    """
    Note, set the following in your .env file to use Elevenlabs:
    AUDIO_TTS_ENGINE=elevenlabs
    AUDIO_TTS_API_KEY=sk_...  # Your Elevenlabs API key
    AUDIO_TTS_VOICE=EXAVITQu4vr4xnSDxMaL  # From https://api.elevenlabs.io/v1/voices
    AUDIO_TTS_MODEL=eleven_multilingual_v2
    """
    headers = {
        "xi-api-key": app.state.config.TTS_API_KEY,
        "Content-Type": "application/json",
    }
    try:
        # TODO: Add retries
        response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers)
        response.raise_for_status()
        voices_data = response.json()

        voices = {}
        for voice in voices_data.get("voices", []):
            voices[voice["voice_id"]] = voice["name"]
    except requests.RequestException as e:
        # Avoid @lru_cache with exception
        log.error(f"Error fetching voices: {str(e)}")
        raise RuntimeError(f"Error fetching voices: {str(e)}")

    return voices


@app.get("/voices")
async def get_voices(user=Depends(get_verified_user)):
    return {"voices": [{"id": k, "name": v} for k, v in get_available_voices().items()]}

import hashlib
import json
import logging
import os
import uuid
import time
import html
import base64
import re
from functools import lru_cache
from pydub import AudioSegment
from pydub.silence import split_on_silence
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fnmatch import fnmatch
import aiohttp
import aiofiles
import requests
import mimetypes
import asyncio
from urllib.parse import urlencode

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

import websockets


from open_webui.utils.auth import get_admin_user, get_verified_user, get_verified_user_or_none
from open_webui.utils.headers import include_user_info_headers
from open_webui.config import (
    WHISPER_MODEL_AUTO_UPDATE,
    WHISPER_MODEL_DIR,
    CACHE_DIR,
    WHISPER_LANGUAGE,
    ELEVENLABS_API_BASE_URL,
)

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import (
    ENV,
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
    SRC_LOG_LEVELS,
    DEVICE_TYPE,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    REDIS_KEY_PREFIX,
)
from open_webui.models.users import Users
from open_webui.models.stt_credit_ledger import record_stt_credits_charge, record_tts_credits_charge
from open_webui.utils.auth import decode_token
from open_webui.utils.stt_credits import (
    AUTH_REQUIRED_MESSAGE_KA,
    LIMIT_EXHAUSTED_MESSAGE_KA,
    acquire_session_lock,
    charge_committed_transcript,
    committed_segment_signature,
    count_credits,
    get_credits_status,
    refresh_session_lock,
    release_session_lock,
    SESSION_LOCK_REFRESH_SECONDS,
)


router = APIRouter()

# Constants
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes
AZURE_MAX_FILE_SIZE_MB = 200
AZURE_MAX_FILE_SIZE = AZURE_MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["AUDIO"])

SPEECH_CACHE_DIR = CACHE_DIR / "audio" / "speech"
SPEECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)


##########################################
#
# Utility functions
#
##########################################

from pydub import AudioSegment
from pydub.utils import mediainfo


def is_audio_conversion_required(file_path):
    """
    Check if the given audio file needs conversion to mp3.
    """
    SUPPORTED_FORMATS = {"flac", "m4a", "mp3", "mp4", "mpeg", "wav", "webm"}

    if not os.path.isfile(file_path):
        log.error(f"File not found: {file_path}")
        return False

    try:
        info = mediainfo(file_path)
        codec_name = info.get("codec_name", "").lower()
        codec_type = info.get("codec_type", "").lower()
        codec_tag_string = info.get("codec_tag_string", "").lower()

        if codec_name == "aac" and codec_type == "audio" and codec_tag_string == "mp4a":
            # File is AAC/mp4a audio, recommend mp3 conversion
            return True

        # If the codec name is in the supported formats
        if codec_name in SUPPORTED_FORMATS:
            return False

        return True
    except Exception as e:
        log.error(f"Error getting audio format: {e}")
        return False


def convert_audio_to_mp3(file_path):
    """Convert audio file to mp3 format."""
    try:
        output_path = os.path.splitext(file_path)[0] + ".mp3"
        audio = AudioSegment.from_file(file_path)
        audio.export(output_path, format="mp3")
        log.info(f"Converted {file_path} to {output_path}")
        return output_path
    except Exception as e:
        log.error(f"Error converting audio file: {e}")
        return None


def set_faster_whisper_model(model: str, auto_update: bool = False):
    whisper_model = None
    if model:
        from faster_whisper import WhisperModel

        faster_whisper_kwargs = {
            "model_size_or_path": model,
            "device": DEVICE_TYPE if DEVICE_TYPE and DEVICE_TYPE == "cuda" else "cpu",
            "compute_type": "int8",
            "download_root": WHISPER_MODEL_DIR,
            "local_files_only": not auto_update,
        }

        try:
            whisper_model = WhisperModel(**faster_whisper_kwargs)
        except Exception:
            log.warning(
                "WhisperModel initialization failed, attempting download with local_files_only=False"
            )
            faster_whisper_kwargs["local_files_only"] = False
            whisper_model = WhisperModel(**faster_whisper_kwargs)
    return whisper_model


##########################################
#
# Audio API
#
##########################################


class TTSConfigForm(BaseModel):
    OPENAI_API_BASE_URL: str
    OPENAI_API_KEY: str
    OPENAI_PARAMS: Optional[dict] = None
    API_KEY: str
    ENGINE: str
    MODEL: str
    VOICE: str
    SPLIT_ON: str
    AZURE_SPEECH_REGION: str
    AZURE_SPEECH_BASE_URL: str
    AZURE_SPEECH_OUTPUT_FORMAT: str


class STTConfigForm(BaseModel):
    OPENAI_API_BASE_URL: str
    OPENAI_API_KEY: str
    ELEVENLABS_API_KEY: str = ""
    ENGINE: str
    MODEL: str
    SUPPORTED_CONTENT_TYPES: list[str] = []
    WHISPER_MODEL: str
    DEEPGRAM_API_KEY: str
    AZURE_API_KEY: str
    AZURE_REGION: str
    AZURE_LOCALES: str
    AZURE_BASE_URL: str
    AZURE_MAX_SPEAKERS: str
    MISTRAL_API_KEY: str
    MISTRAL_API_BASE_URL: str
    MISTRAL_USE_CHAT_COMPLETIONS: bool


class AudioConfigUpdateForm(BaseModel):
    tts: TTSConfigForm
    stt: STTConfigForm


@router.get("/config")
async def get_audio_config(request: Request, user=Depends(get_admin_user)):
    return {
        "tts": {
            "OPENAI_API_BASE_URL": request.app.state.config.TTS_OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": request.app.state.config.TTS_OPENAI_API_KEY,
            "OPENAI_PARAMS": request.app.state.config.TTS_OPENAI_PARAMS,
            "API_KEY": request.app.state.config.TTS_API_KEY,
            "ENGINE": request.app.state.config.TTS_ENGINE,
            "MODEL": request.app.state.config.TTS_MODEL,
            "VOICE": request.app.state.config.TTS_VOICE,
            "SPLIT_ON": request.app.state.config.TTS_SPLIT_ON,
            "AZURE_SPEECH_REGION": request.app.state.config.TTS_AZURE_SPEECH_REGION,
            "AZURE_SPEECH_BASE_URL": request.app.state.config.TTS_AZURE_SPEECH_BASE_URL,
            "AZURE_SPEECH_OUTPUT_FORMAT": request.app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT,
        },
        "stt": {
            "OPENAI_API_BASE_URL": request.app.state.config.STT_OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": request.app.state.config.STT_OPENAI_API_KEY,
            "ELEVENLABS_API_KEY": request.app.state.config.AUDIO_STT_ELEVENLABS_API_KEY,
            "ENGINE": request.app.state.config.STT_ENGINE,
            "MODEL": request.app.state.config.STT_MODEL,
            "SUPPORTED_CONTENT_TYPES": request.app.state.config.STT_SUPPORTED_CONTENT_TYPES,
            "WHISPER_MODEL": request.app.state.config.WHISPER_MODEL,
            "DEEPGRAM_API_KEY": request.app.state.config.DEEPGRAM_API_KEY,
            "AZURE_API_KEY": request.app.state.config.AUDIO_STT_AZURE_API_KEY,
            "AZURE_REGION": request.app.state.config.AUDIO_STT_AZURE_REGION,
            "AZURE_LOCALES": request.app.state.config.AUDIO_STT_AZURE_LOCALES,
            "AZURE_BASE_URL": request.app.state.config.AUDIO_STT_AZURE_BASE_URL,
            "AZURE_MAX_SPEAKERS": request.app.state.config.AUDIO_STT_AZURE_MAX_SPEAKERS,
            "MISTRAL_API_KEY": request.app.state.config.AUDIO_STT_MISTRAL_API_KEY,
            "MISTRAL_API_BASE_URL": request.app.state.config.AUDIO_STT_MISTRAL_API_BASE_URL,
            "MISTRAL_USE_CHAT_COMPLETIONS": request.app.state.config.AUDIO_STT_MISTRAL_USE_CHAT_COMPLETIONS,
        },
    }


@router.post("/config/update")
async def update_audio_config(
    request: Request, form_data: AudioConfigUpdateForm, user=Depends(get_admin_user)
):
    if form_data.stt.ENGINE == "elevenlabs" and not form_data.stt.ELEVENLABS_API_KEY:
        raise HTTPException(status_code=400, detail="ElevenLabs STT requires an API key")

    request.app.state.config.TTS_OPENAI_API_BASE_URL = form_data.tts.OPENAI_API_BASE_URL
    request.app.state.config.TTS_OPENAI_API_KEY = form_data.tts.OPENAI_API_KEY
    request.app.state.config.TTS_OPENAI_PARAMS = form_data.tts.OPENAI_PARAMS
    request.app.state.config.TTS_API_KEY = form_data.tts.API_KEY
    request.app.state.config.TTS_ENGINE = form_data.tts.ENGINE
    request.app.state.config.TTS_MODEL = form_data.tts.MODEL
    request.app.state.config.TTS_VOICE = form_data.tts.VOICE
    request.app.state.config.TTS_SPLIT_ON = form_data.tts.SPLIT_ON
    request.app.state.config.TTS_AZURE_SPEECH_REGION = form_data.tts.AZURE_SPEECH_REGION
    request.app.state.config.TTS_AZURE_SPEECH_BASE_URL = (
        form_data.tts.AZURE_SPEECH_BASE_URL
    )
    request.app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT = (
        form_data.tts.AZURE_SPEECH_OUTPUT_FORMAT
    )

    request.app.state.config.STT_OPENAI_API_BASE_URL = form_data.stt.OPENAI_API_BASE_URL
    request.app.state.config.STT_OPENAI_API_KEY = form_data.stt.OPENAI_API_KEY
    request.app.state.config.AUDIO_STT_ELEVENLABS_API_KEY = form_data.stt.ELEVENLABS_API_KEY
    request.app.state.config.STT_ENGINE = form_data.stt.ENGINE
    request.app.state.config.STT_MODEL = form_data.stt.MODEL
    request.app.state.config.STT_SUPPORTED_CONTENT_TYPES = (
        form_data.stt.SUPPORTED_CONTENT_TYPES
    )

    request.app.state.config.WHISPER_MODEL = form_data.stt.WHISPER_MODEL
    request.app.state.config.DEEPGRAM_API_KEY = form_data.stt.DEEPGRAM_API_KEY
    request.app.state.config.AUDIO_STT_AZURE_API_KEY = form_data.stt.AZURE_API_KEY
    request.app.state.config.AUDIO_STT_AZURE_REGION = form_data.stt.AZURE_REGION
    request.app.state.config.AUDIO_STT_AZURE_LOCALES = form_data.stt.AZURE_LOCALES
    request.app.state.config.AUDIO_STT_AZURE_BASE_URL = form_data.stt.AZURE_BASE_URL
    request.app.state.config.AUDIO_STT_AZURE_MAX_SPEAKERS = (
        form_data.stt.AZURE_MAX_SPEAKERS
    )
    request.app.state.config.AUDIO_STT_MISTRAL_API_KEY = form_data.stt.MISTRAL_API_KEY
    request.app.state.config.AUDIO_STT_MISTRAL_API_BASE_URL = (
        form_data.stt.MISTRAL_API_BASE_URL
    )
    request.app.state.config.AUDIO_STT_MISTRAL_USE_CHAT_COMPLETIONS = (
        form_data.stt.MISTRAL_USE_CHAT_COMPLETIONS
    )

    if request.app.state.config.STT_ENGINE == "":
        request.app.state.faster_whisper_model = set_faster_whisper_model(
            form_data.stt.WHISPER_MODEL, WHISPER_MODEL_AUTO_UPDATE
        )
    else:
        request.app.state.faster_whisper_model = None

    return {
        "tts": {
            "ENGINE": request.app.state.config.TTS_ENGINE,
            "MODEL": request.app.state.config.TTS_MODEL,
            "VOICE": request.app.state.config.TTS_VOICE,
            "OPENAI_API_BASE_URL": request.app.state.config.TTS_OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": request.app.state.config.TTS_OPENAI_API_KEY,
            "OPENAI_PARAMS": request.app.state.config.TTS_OPENAI_PARAMS,
            "API_KEY": request.app.state.config.TTS_API_KEY,
            "SPLIT_ON": request.app.state.config.TTS_SPLIT_ON,
            "AZURE_SPEECH_REGION": request.app.state.config.TTS_AZURE_SPEECH_REGION,
            "AZURE_SPEECH_BASE_URL": request.app.state.config.TTS_AZURE_SPEECH_BASE_URL,
            "AZURE_SPEECH_OUTPUT_FORMAT": request.app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT,
        },
        "stt": {
            "OPENAI_API_BASE_URL": request.app.state.config.STT_OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": request.app.state.config.STT_OPENAI_API_KEY,
            "ELEVENLABS_API_KEY": request.app.state.config.AUDIO_STT_ELEVENLABS_API_KEY,
            "ENGINE": request.app.state.config.STT_ENGINE,
            "MODEL": request.app.state.config.STT_MODEL,
            "SUPPORTED_CONTENT_TYPES": request.app.state.config.STT_SUPPORTED_CONTENT_TYPES,
            "WHISPER_MODEL": request.app.state.config.WHISPER_MODEL,
            "DEEPGRAM_API_KEY": request.app.state.config.DEEPGRAM_API_KEY,
            "AZURE_API_KEY": request.app.state.config.AUDIO_STT_AZURE_API_KEY,
            "AZURE_REGION": request.app.state.config.AUDIO_STT_AZURE_REGION,
            "AZURE_LOCALES": request.app.state.config.AUDIO_STT_AZURE_LOCALES,
            "AZURE_BASE_URL": request.app.state.config.AUDIO_STT_AZURE_BASE_URL,
            "AZURE_MAX_SPEAKERS": request.app.state.config.AUDIO_STT_AZURE_MAX_SPEAKERS,
            "MISTRAL_API_KEY": request.app.state.config.AUDIO_STT_MISTRAL_API_KEY,
            "MISTRAL_API_BASE_URL": request.app.state.config.AUDIO_STT_MISTRAL_API_BASE_URL,
            "MISTRAL_USE_CHAT_COMPLETIONS": request.app.state.config.AUDIO_STT_MISTRAL_USE_CHAT_COMPLETIONS,
        },
    }


def load_speech_pipeline(request):
    from transformers import pipeline
    from datasets import load_dataset

    if request.app.state.speech_synthesiser is None:
        request.app.state.speech_synthesiser = pipeline(
            "text-to-speech", "microsoft/speecht5_tts"
        )

    if request.app.state.speech_speaker_embeddings_dataset is None:
        request.app.state.speech_speaker_embeddings_dataset = load_dataset(
            "Matthijs/cmu-arctic-xvectors", split="validation"
        )


_VOICE_AUDIO_EXT_MEDIA_TYPES: dict[str, str] = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "opus": "audio/opus",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "m4a": "audio/mp4",
}


def _speech_cache_key(*, body: bytes, request: Request) -> str:
    return hashlib.sha256(
        body
        + str(request.app.state.config.TTS_ENGINE).encode("utf-8")
        + str(request.app.state.config.TTS_MODEL).encode("utf-8")
    ).hexdigest()


def _sanitize_audio_ext(ext: str | None) -> str:
    ext = (ext or "").strip().lower()
    if ext.startswith("."):
        ext = ext[1:]
    return ext or "mp3"


def _guess_media_type_for_ext(ext: str) -> str:
    ext = _sanitize_audio_ext(ext)
    return (
        _VOICE_AUDIO_EXT_MEDIA_TYPES.get(ext)
        or mimetypes.types_map.get(f".{ext}")
        or "application/octet-stream"
    )


def _tts_output_ext(*, request: Request, payload: dict) -> str:
    engine = str(request.app.state.config.TTS_ENGINE or "")
    if engine == "openai":
        response_format = payload.get("response_format")
        if isinstance(response_format, str) and response_format.strip():
            return _sanitize_audio_ext(response_format)
        return "mp3"

    if engine == "azure":
        output_format = str(request.app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT or "").lower()
        if "riff" in output_format or "pcm" in output_format:
            return "wav"
        if "mp3" in output_format:
            return "mp3"
        return "mp3"

    if engine == "transformers":
        return "wav"

    return "mp3"


def _speech_cache_paths(*, cache_key: str, ext: str) -> tuple[os.PathLike, os.PathLike]:
    safe_ext = _sanitize_audio_ext(ext)
    file_path = SPEECH_CACHE_DIR.joinpath(f"{cache_key}.{safe_ext}")
    file_body_path = SPEECH_CACHE_DIR.joinpath(f"{cache_key}.json")
    return file_path, file_body_path


async def _synthesize_speech_to_cache(
    request: Request,
    *,
    user,
    payload: dict,
    cache_key: str,
) -> tuple[os.PathLike, str, str]:
    """
    Returns: (file_path, ext, media_type)
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Normalize provider-specific defaults/overrides without duplicating TTS logic.
    engine = str(request.app.state.config.TTS_ENGINE or "")
    working_payload = dict(payload)

    if engine == "openai":
        working_payload["model"] = request.app.state.config.TTS_MODEL
        working_payload = {
            **working_payload,
            **(request.app.state.config.TTS_OPENAI_PARAMS or {}),
        }

    ext = _tts_output_ext(request=request, payload=working_payload)
    media_type = _guess_media_type_for_ext(ext)
    file_path, file_body_path = _speech_cache_paths(cache_key=cache_key, ext=ext)

    if file_path.is_file():
        return file_path, ext, media_type

    r = None

    if engine == "openai":
        try:
            timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {request.app.state.config.TTS_OPENAI_API_KEY}",
                }
                if ENABLE_FORWARD_USER_INFO_HEADERS and user is not None:
                    headers = include_user_info_headers(headers, user)

                r = await session.post(
                    url=f"{request.app.state.config.TTS_OPENAI_API_BASE_URL}/audio/speech",
                    json=working_payload,
                    headers=headers,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                )

                r.raise_for_status()

                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(await r.read())

                async with aiofiles.open(file_body_path, "w") as f:
                    await f.write(json.dumps(working_payload))

            return file_path, ext, media_type

        except Exception as e:
            log.exception(e)
            detail = "Server Connection Error"
            status_code = 500

            if r is not None:
                status_code = getattr(r, "status", 500) or 500
                try:
                    res = await r.json()
                    if "error" in res:
                        detail = f"External: {res['error']}"
                except Exception:
                    detail = f"External: {e}"

            raise HTTPException(status_code=status_code, detail=detail)

    if engine == "elevenlabs":
        if not request.app.state.config.TTS_API_KEY:
            raise HTTPException(status_code=400, detail="TTS is not configured")

        voice_id = str(working_payload.get("voice") or request.app.state.config.TTS_VOICE or "")
        if not voice_id:
            raise HTTPException(status_code=400, detail="TTS voice is not configured")

        if voice_id not in get_available_voices(request):
            raise HTTPException(status_code=400, detail="Invalid configured voice id")

        try:
            timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
                async with session.post(
                    f"{ELEVENLABS_API_BASE_URL}/v1/text-to-speech/{voice_id}",
                    json={
                        "text": working_payload.get("input", ""),
                        "model_id": request.app.state.config.TTS_MODEL,
                        "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
                    },
                    headers={
                        "Accept": _guess_media_type_for_ext(ext),
                        "Content-Type": "application/json",
                        "xi-api-key": request.app.state.config.TTS_API_KEY,
                    },
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    r.raise_for_status()

                    async with aiofiles.open(file_path, "wb") as f:
                        await f.write(await r.read())

                    async with aiofiles.open(file_body_path, "w") as f:
                        await f.write(json.dumps(working_payload))

            return file_path, ext, media_type

        except Exception as e:
            log.exception(e)
            detail = None

            try:
                if r is not None and getattr(r, "status", 200) != 200:
                    res = await r.json()
                    if "error" in res:
                        detail = f"External: {res['error'].get('message', '')}"
            except Exception:
                detail = f"External: {e}"

            raise HTTPException(
                status_code=getattr(r, "status", 500) if r else 500,
                detail=detail if detail else "Server Connection Error",
            )

    if engine == "azure":
        region = request.app.state.config.TTS_AZURE_SPEECH_REGION or "eastus"
        base_url = request.app.state.config.TTS_AZURE_SPEECH_BASE_URL
        voice_name = str(working_payload.get("voice") or request.app.state.config.TTS_VOICE or "")
        if not voice_name:
            raise HTTPException(status_code=400, detail="TTS voice is not configured")

        locale = "-".join(voice_name.split("-")[:1])
        output_format = request.app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT

        try:
            data = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{locale}">
                <voice name="{voice_name}">{html.escape(str(working_payload.get("input", "")))}</voice>
            </speak>"""
            timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
                async with session.post(
                    (base_url or f"https://{region}.tts.speech.microsoft.com")
                    + "/cognitiveservices/v1",
                    headers={
                        "Ocp-Apim-Subscription-Key": request.app.state.config.TTS_API_KEY,
                        "Content-Type": "application/ssml+xml",
                        "X-Microsoft-OutputFormat": output_format,
                    },
                    data=data,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    r.raise_for_status()

                    async with aiofiles.open(file_path, "wb") as f:
                        await f.write(await r.read())

                    async with aiofiles.open(file_body_path, "w") as f:
                        await f.write(json.dumps(working_payload))

                    return file_path, ext, media_type

        except Exception as e:
            log.exception(e)
            detail = None

            try:
                if r is not None and getattr(r, "status", 200) != 200:
                    res = await r.json()
                    if "error" in res:
                        detail = f"External: {res['error'].get('message', '')}"
            except Exception:
                detail = f"External: {e}"

            raise HTTPException(
                status_code=getattr(r, "status", 500) if r else 500,
                detail=detail if detail else "Server Connection Error",
            )

    if engine == "transformers":
        import torch
        import soundfile as sf

        load_speech_pipeline(request)

        embeddings_dataset = request.app.state.speech_speaker_embeddings_dataset

        speaker_index = 6799
        try:
            speaker_index = embeddings_dataset["filename"].index(
                request.app.state.config.TTS_MODEL
            )
        except Exception:
            pass

        speaker_embedding = torch.tensor(
            embeddings_dataset[speaker_index]["xvector"]
        ).unsqueeze(0)

        speech = request.app.state.speech_synthesiser(
            str(working_payload.get("input", "")),
            forward_params={"speaker_embeddings": speaker_embedding},
        )

        sf.write(file_path, speech["audio"], samplerate=speech["sampling_rate"])

        async with aiofiles.open(file_body_path, "w") as f:
            await f.write(json.dumps(working_payload))

        return file_path, ext, media_type

    raise HTTPException(status_code=400, detail="TTS is not configured")


def _find_cached_voice_file(*, audio_id: str) -> tuple[os.PathLike, str, str] | None:
    if not re.fullmatch(r"[0-9a-f]{64}", audio_id or ""):
        return None

    for ext in ("mp3", "wav", "ogg", "opus", "aac", "flac", "m4a"):
        file_path = SPEECH_CACHE_DIR.joinpath(f"{audio_id}.{ext}")
        if file_path.is_file():
            return file_path, ext, _guess_media_type_for_ext(ext)

    return None


@router.post("/speech")
async def speech(request: Request, user=Depends(get_verified_user)):
    body = await request.body()
    cache_key = _speech_cache_key(body=body, request=request)

    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    is_admin = getattr(user, "role", None) == "admin"
    credits_needed = count_credits(str(payload.get("input", "")))
    redis = request.app.state.redis
    now_ts = None
    status_before = None
    free_limit = None

    if not is_admin and credits_needed > 0:
        if redis is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Credits system is not available.",
            )

        now_ts = int(time.time())
        free_limit = int(getattr(request.app.state.config, "AUDIO_CREDITS_FREE_AUTH", 0) or 0)
        status_before = await get_credits_status(
            redis, user_id=user.id, now_ts=now_ts, free_limit=free_limit
        )
        if status_before.total_remaining < credits_needed:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient credits for voice generation",
            )

    file_path, _ext, media_type = await _synthesize_speech_to_cache(
        request,
        user=user,
        payload=payload,
        cache_key=cache_key,
    )

    charged = False
    if (
        not is_admin
        and credits_needed > 0
        and redis is not None
        and now_ts is not None
        and status_before is not None
    ):
        voice = str(payload.get("voice") or request.app.state.config.TTS_VOICE or "").strip()
        signature_source = f"tts:speech:{cache_key}:{voice}"
        signature = hashlib.sha256(signature_source.encode("utf-8")).hexdigest()

        status_after, charged, _exhausted_after = await charge_committed_transcript(
            redis,
            user_id=user.id,
            credits_needed=credits_needed,
            signature=signature,
            now_ts=now_ts,
            free_limit=free_limit,
        )

        if charged:
            free_to_use = min(status_before.free_remaining, credits_needed)
            paid_to_use = max(0, credits_needed - free_to_use)
            record_tts_credits_charge(
                user_id=user.id,
                reference_id=signature,
                credits=credits_needed,
                free_credits=free_to_use,
                paid_credits=paid_to_use,
                meta={
                    "engine": str(request.app.state.config.TTS_ENGINE or ""),
                    "model": str(request.app.state.config.TTS_MODEL or ""),
                    "voice": voice,
                    "chars": credits_needed,
                    "cache_key": cache_key,
                    "endpoint": "speech",
                },
                now_ts=now_ts,
            )

    return FileResponse(file_path, media_type=media_type)


class VoiceGenerateForm(BaseModel):
    message_id: str | None = None
    input: str
    voice: str | None = None
    model: str | None = None


def _get_or_set_anon_id(request: Request, response: Response) -> str:
    anon_id = (
        request.headers.get("X-OWUI-ANON-ID")
        or request.cookies.get("owui_anon_id")
        or ""
    ).strip()
    if anon_id:
        return anon_id

    anon_id = uuid.uuid4().hex
    response.set_cookie(
        key="owui_anon_id",
        value=anon_id,
        max_age=60 * 60 * 24 * 365,
        samesite="lax",
    )
    return anon_id


@router.get("/voice/status")
async def voice_status(
    request: Request,
    response: Response,
    user=Depends(get_verified_user_or_none),
):
    if user is None:
        _get_or_set_anon_id(request, response)

    is_admin = getattr(user, "role", None) == "admin"
    tts_engine = str(request.app.state.config.TTS_ENGINE or "")
    tts_configured = bool(tts_engine)
    redis_available = request.app.state.redis is not None
    credits_required = not is_admin
    available = bool(tts_configured and (not credits_required or redis_available))

    return {
        "available": available,
        "tts_configured": tts_configured,
        "tts_engine": tts_engine,
        "default_voice": request.app.state.config.TTS_VOICE,
        "credits_required": credits_required,
        "redis_available": redis_available,
    }


@router.post("/voice")
async def generate_voice(
    request: Request,
    response: Response,
    form_data: VoiceGenerateForm,
    user=Depends(get_verified_user_or_none),
):
    input_text = str(form_data.input or "")
    selected_voice = (
        str(form_data.voice).strip()
        if form_data.voice is not None
        else str(request.app.state.config.TTS_VOICE or "").strip()
    )

    tts_payload: dict = {
        "input": input_text,
        "voice": selected_voice,
        **({"model": form_data.model} if form_data.model else {}),
    }

    body_bytes = json.dumps(tts_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    cache_key = _speech_cache_key(body=body_bytes, request=request)

    is_admin = getattr(user, "role", None) == "admin"

    credits_needed = count_credits(input_text)
    redis = request.app.state.redis
    subject_id: str | None = None
    now_ts: int | None = None
    status_before = None
    free_limit: int | None = None

    if not is_admin and credits_needed > 0:
        if redis is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Voice generation temporarily unavailable",
            )

        subject_id = user.id if user is not None else f"anon:{_get_or_set_anon_id(request, response)}"
        now_ts = int(time.time())
        free_limit = (
            int(getattr(request.app.state.config, "AUDIO_CREDITS_FREE_AUTH", 0) or 0)
            if user is not None
            else int(getattr(request.app.state.config, "AUDIO_CREDITS_FREE_ANON", 0) or 0)
        )
        status_before = await get_credits_status(
            redis, user_id=subject_id, now_ts=now_ts, free_limit=free_limit
        )

        if user is None and status_before.free_remaining < credits_needed:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please sign in to continue voice generation",
            )

        if user is not None and status_before.total_remaining < credits_needed:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient credits for voice generation",
            )

    file_path, ext, media_type = await _synthesize_speech_to_cache(
        request,
        user=user,
        payload=tts_payload,
        cache_key=cache_key,
    )

    data_url: str | None = None
    try:
        async with aiofiles.open(file_path, "rb") as f:
            audio_bytes = await f.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        data_url = f"data:{media_type};base64,{audio_b64}"
    except Exception:
        data_url = None

    charged = False
    if not is_admin and credits_needed > 0 and redis is not None and subject_id and now_ts and status_before:
        signature_source = f"tts:{form_data.message_id or cache_key}:{cache_key}:{selected_voice}"
        signature = hashlib.sha256(signature_source.encode("utf-8")).hexdigest()

        status_after, charged, _exhausted_after = await charge_committed_transcript(
            redis,
            user_id=subject_id,
            credits_needed=credits_needed,
            signature=signature,
            now_ts=now_ts,
            free_limit=free_limit,
        )

        if charged:
            free_to_use = min(status_before.free_remaining, credits_needed)
            paid_to_use = max(0, credits_needed - free_to_use)
            record_tts_credits_charge(
                user_id=subject_id,
                reference_id=signature,
                credits=credits_needed,
                free_credits=free_to_use,
                paid_credits=paid_to_use,
                meta={
                    "engine": str(request.app.state.config.TTS_ENGINE or ""),
                    "model": str(request.app.state.config.TTS_MODEL or ""),
                    "voice": selected_voice,
                    "chars": credits_needed,
                    "cache_key": cache_key,
                    **({"message_id": form_data.message_id} if form_data.message_id else {}),
                },
                now_ts=now_ts,
            )

    play_url = f"/api/v1/audio/voice/{cache_key}"
    download_url = f"/api/v1/audio/voice/{cache_key}/download"

    return {
        "id": cache_key,
        "ext": ext,
        "media_type": media_type,
        "data_url": data_url,
        "play_url": play_url,
        "download_url": download_url,
        "charged": charged,
    }


@router.get("/voice/{audio_id}")
async def get_voice(audio_id: str):
    found = _find_cached_voice_file(audio_id=audio_id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")
    file_path, _ext, media_type = found
    return FileResponse(file_path, media_type=media_type)


@router.get("/voice/{audio_id}/download")
async def download_voice(audio_id: str):
    found = _find_cached_voice_file(audio_id=audio_id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")
    file_path, ext, media_type = found
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=f"voice-{audio_id}.{ext}",
    )


def transcription_handler(request, file_path, metadata, user=None):
    filename = os.path.basename(file_path)
    file_dir = os.path.dirname(file_path)
    id = filename.split(".")[0]

    metadata = metadata or {}

    languages = [
        metadata.get("language", None) if not WHISPER_LANGUAGE else WHISPER_LANGUAGE,
        None,  # Always fallback to None in case transcription fails
    ]

    if request.app.state.config.STT_ENGINE == "":
        if request.app.state.faster_whisper_model is None:
            request.app.state.faster_whisper_model = set_faster_whisper_model(
                request.app.state.config.WHISPER_MODEL
            )

        model = request.app.state.faster_whisper_model
        segments, info = model.transcribe(
            file_path,
            beam_size=5,
            vad_filter=request.app.state.config.WHISPER_VAD_FILTER,
            language=languages[0],
        )
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

        log.debug(data)
        return data
    elif request.app.state.config.STT_ENGINE == "openai":
        r = None
        try:
            for language in languages:
                payload = {
                    "model": request.app.state.config.STT_MODEL,
                }

                if language:
                    payload["language"] = language

                headers = {
                    "Authorization": f"Bearer {request.app.state.config.STT_OPENAI_API_KEY}"
                }
                if user and ENABLE_FORWARD_USER_INFO_HEADERS:
                    headers = include_user_info_headers(headers, user)

                r = requests.post(
                    url=f"{request.app.state.config.STT_OPENAI_API_BASE_URL}/audio/transcriptions",
                    headers=headers,
                    files={"file": (filename, open(file_path, "rb"))},
                    data=payload,
                )

                if r.status_code == 200:
                    # Successful transcription
                    break

            r.raise_for_status()
            data = r.json()

            # save the transcript to a json file
            transcript_file = f"{file_dir}/{id}.json"
            with open(transcript_file, "w") as f:
                json.dump(data, f)

            return data
        except Exception as e:
            log.exception(e)

            detail = None
            if r is not None:
                try:
                    res = r.json()
                    if "error" in res:
                        detail = f"External: {res['error'].get('message', '')}"
                except Exception:
                    detail = f"External: {e}"

            raise Exception(detail if detail else "Server Connection Error")

    elif request.app.state.config.STT_ENGINE == "elevenlabs":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ElevenLabs STT is supported only via realtime voice mode.",
        )

    elif request.app.state.config.STT_ENGINE == "deepgram":
        try:
            # Determine the MIME type of the file
            mime, _ = mimetypes.guess_type(file_path)
            if not mime:
                mime = "audio/wav"  # fallback to wav if undetectable

            # Read the audio file
            with open(file_path, "rb") as f:
                file_data = f.read()

            # Build headers and parameters
            headers = {
                "Authorization": f"Token {request.app.state.config.DEEPGRAM_API_KEY}",
                "Content-Type": mime,
            }

            for language in languages:
                params = {}
                if request.app.state.config.STT_MODEL:
                    params["model"] = request.app.state.config.STT_MODEL

                if language:
                    params["language"] = language

                # Make request to Deepgram API
                r = requests.post(
                    "https://api.deepgram.com/v1/listen?smart_format=true",
                    headers=headers,
                    params=params,
                    data=file_data,
                )

                if r.status_code == 200:
                    # Successful transcription
                    break

            r.raise_for_status()
            response_data = r.json()

            # Extract transcript from Deepgram response
            try:
                transcript = response_data["results"]["channels"][0]["alternatives"][
                    0
                ].get("transcript", "")
            except (KeyError, IndexError) as e:
                log.error(f"Malformed response from Deepgram: {str(e)}")
                raise Exception(
                    "Failed to parse Deepgram response - unexpected response format"
                )
            data = {"text": transcript.strip()}

            # Save transcript
            transcript_file = f"{file_dir}/{id}.json"
            with open(transcript_file, "w") as f:
                json.dump(data, f)

            return data

        except Exception as e:
            log.exception(e)
            detail = None
            if r is not None:
                try:
                    res = r.json()
                    if "error" in res:
                        detail = f"External: {res['error'].get('message', '')}"
                except Exception:
                    detail = f"External: {e}"
            raise Exception(detail if detail else "Server Connection Error")

    elif request.app.state.config.STT_ENGINE == "azure":
        # Check file exists and size
        if not os.path.exists(file_path):
            raise HTTPException(status_code=400, detail="Audio file not found")

        # Check file size (Azure has a larger limit of 200MB)
        file_size = os.path.getsize(file_path)
        if file_size > AZURE_MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds Azure's limit of {AZURE_MAX_FILE_SIZE_MB}MB",
            )

        api_key = request.app.state.config.AUDIO_STT_AZURE_API_KEY
        region = request.app.state.config.AUDIO_STT_AZURE_REGION or "eastus"
        locales = request.app.state.config.AUDIO_STT_AZURE_LOCALES
        base_url = request.app.state.config.AUDIO_STT_AZURE_BASE_URL
        max_speakers = request.app.state.config.AUDIO_STT_AZURE_MAX_SPEAKERS or 3

        # IF NO LOCALES, USE DEFAULTS
        if len(locales) < 2:
            locales = [
                "en-US",
                "es-ES",
                "es-MX",
                "fr-FR",
                "hi-IN",
                "it-IT",
                "de-DE",
                "en-GB",
                "en-IN",
                "ja-JP",
                "ko-KR",
                "pt-BR",
                "zh-CN",
            ]
            locales = ",".join(locales)

        if not api_key or not region:
            raise HTTPException(
                status_code=400,
                detail="Azure API key is required for Azure STT",
            )

        r = None
        try:
            # Prepare the request
            data = {
                "definition": json.dumps(
                    {
                        "locales": locales.split(","),
                        "diarization": {"maxSpeakers": max_speakers, "enabled": True},
                    }
                    if locales
                    else {}
                )
            }

            url = (
                base_url or f"https://{region}.api.cognitive.microsoft.com"
            ) + "/speechtotext/transcriptions:transcribe?api-version=2024-11-15"

            # Use context manager to ensure file is properly closed
            with open(file_path, "rb") as audio_file:
                r = requests.post(
                    url=url,
                    files={"audio": audio_file},
                    data=data,
                    headers={
                        "Ocp-Apim-Subscription-Key": api_key,
                    },
                )

            r.raise_for_status()
            response = r.json()

            # Extract transcript from response
            if not response.get("combinedPhrases"):
                raise ValueError("No transcription found in response")

            # Get the full transcript from combinedPhrases
            transcript = response["combinedPhrases"][0].get("text", "").strip()
            if not transcript:
                raise ValueError("Empty transcript in response")

            data = {"text": transcript}

            # Save transcript to json file (consistent with other providers)
            transcript_file = f"{file_dir}/{id}.json"
            with open(transcript_file, "w") as f:
                json.dump(data, f)

            log.debug(data)
            return data

        except (KeyError, IndexError, ValueError) as e:
            log.exception("Error parsing Azure response")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse Azure response: {str(e)}",
            )
        except requests.exceptions.RequestException as e:
            log.exception(e)
            detail = None

            try:
                if r is not None and r.status_code != 200:
                    res = r.json()
                    if "error" in res:
                        detail = f"External: {res['error'].get('message', '')}"
            except Exception:
                detail = f"External: {e}"

            raise HTTPException(
                status_code=getattr(r, "status_code", 500) if r else 500,
                detail=detail if detail else "Server Connection Error",
            )

    elif request.app.state.config.STT_ENGINE == "mistral":
        # Check file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=400, detail="Audio file not found")

        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds limit of {MAX_FILE_SIZE_MB}MB",
            )

        api_key = request.app.state.config.AUDIO_STT_MISTRAL_API_KEY
        api_base_url = (
            request.app.state.config.AUDIO_STT_MISTRAL_API_BASE_URL
            or "https://api.mistral.ai/v1"
        )
        use_chat_completions = (
            request.app.state.config.AUDIO_STT_MISTRAL_USE_CHAT_COMPLETIONS
        )

        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="Mistral API key is required for Mistral STT",
            )

        r = None
        try:
            # Use voxtral-mini-latest as the default model for transcription
            model = request.app.state.config.STT_MODEL or "voxtral-mini-latest"

            log.info(
                f"Mistral STT - model: {model}, "
                f"method: {'chat_completions' if use_chat_completions else 'transcriptions'}"
            )

            if use_chat_completions:
                # Use chat completions API with audio input
                # This method requires mp3 or wav format
                audio_file_to_use = file_path

                if is_audio_conversion_required(file_path):
                    log.debug("Converting audio to mp3 for chat completions API")
                    converted_path = convert_audio_to_mp3(file_path)
                    if converted_path:
                        audio_file_to_use = converted_path
                    else:
                        log.error("Audio conversion failed")
                        raise HTTPException(
                            status_code=500,
                            detail="Audio conversion failed. Chat completions API requires mp3 or wav format.",
                        )

                # Read and encode audio file as base64
                with open(audio_file_to_use, "rb") as audio_file:
                    audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")

                # Prepare chat completions request
                url = f"{api_base_url}/chat/completions"

                # Add language instruction if specified
                language = metadata.get("language", None) if metadata else None
                if language:
                    text_instruction = f"Transcribe this audio exactly as spoken in {language}. Do not translate it."
                else:
                    text_instruction = "Transcribe this audio exactly as spoken in its original language. Do not translate it to another language."

                payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_audio",
                                    "input_audio": audio_base64,
                                },
                                {"type": "text", "text": text_instruction},
                            ],
                        }
                    ],
                }

                r = requests.post(
                    url=url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                )

                r.raise_for_status()
                response = r.json()

                # Extract transcript from chat completion response
                transcript = (
                    response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                if not transcript:
                    raise ValueError("Empty transcript in response")

                data = {"text": transcript}

            else:
                # Use dedicated transcriptions API
                url = f"{api_base_url}/audio/transcriptions"

                # Determine the MIME type
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = "audio/webm"

                # Use context manager to ensure file is properly closed
                with open(file_path, "rb") as audio_file:
                    files = {"file": (filename, audio_file, mime_type)}
                    data_form = {"model": model}

                    # Add language if specified in metadata
                    language = metadata.get("language", None) if metadata else None
                    if language:
                        data_form["language"] = language

                    r = requests.post(
                        url=url,
                        files=files,
                        data=data_form,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                        },
                    )

                r.raise_for_status()
                response = r.json()

                # Extract transcript from response
                transcript = response.get("text", "").strip()
                if not transcript:
                    raise ValueError("Empty transcript in response")

                data = {"text": transcript}

            # Save transcript to json file (consistent with other providers)
            transcript_file = f"{file_dir}/{id}.json"
            with open(transcript_file, "w") as f:
                json.dump(data, f)

            log.debug(data)
            return data

        except ValueError as e:
            log.exception("Error parsing Mistral response")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse Mistral response: {str(e)}",
            )
        except requests.exceptions.RequestException as e:
            log.exception(e)
            detail = None

            try:
                if r is not None and r.status_code != 200:
                    res = r.json()
                    if "error" in res:
                        detail = f"External: {res['error'].get('message', '')}"
                    else:
                        detail = f"External: {r.text}"
            except Exception:
                detail = f"External: {e}"

            raise HTTPException(
                status_code=getattr(r, "status_code", 500) if r else 500,
                detail=detail if detail else "Server Connection Error",
            )


def transcribe(
    request: Request, file_path: str, metadata: Optional[dict] = None, user=None
):
    log.info(f"transcribe: {file_path} {metadata}")

    if is_audio_conversion_required(file_path):
        file_path = convert_audio_to_mp3(file_path)

    try:
        file_path = compress_audio(file_path)
    except Exception as e:
        log.exception(e)

    # Always produce a list of chunk paths (could be one entry if small)
    try:
        chunk_paths = split_audio(file_path, MAX_FILE_SIZE)
        print(f"Chunk paths: {chunk_paths}")
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )

    results = []
    try:
        with ThreadPoolExecutor() as executor:
            # Submit tasks for each chunk_path
            futures = [
                executor.submit(
                    transcription_handler, request, chunk_path, metadata, user
                )
                for chunk_path in chunk_paths
            ]
            # Gather results as they complete
            for future in futures:
                try:
                    results.append(future.result())
                except HTTPException as http_exc:
                    raise http_exc
                except Exception as transcribe_exc:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Error transcribing chunk: {transcribe_exc}",
                    )
    finally:
        # Clean up only the temporary chunks, never the original file
        for chunk_path in chunk_paths:
            if chunk_path != file_path and os.path.isfile(chunk_path):
                try:
                    os.remove(chunk_path)
                except Exception:
                    pass

    return {
        "text": " ".join([result["text"] for result in results]),
    }


def compress_audio(file_path):
    if os.path.getsize(file_path) > MAX_FILE_SIZE:
        id = os.path.splitext(os.path.basename(file_path))[
            0
        ]  # Handles names with multiple dots
        file_dir = os.path.dirname(file_path)

        audio = AudioSegment.from_file(file_path)
        audio = audio.set_frame_rate(16000).set_channels(1)  # Compress audio

        compressed_path = os.path.join(file_dir, f"{id}_compressed.mp3")
        audio.export(compressed_path, format="mp3", bitrate="32k")
        # log.debug(f"Compressed audio to {compressed_path}")  # Uncomment if log is defined

        return compressed_path
    else:
        return file_path


def split_audio(file_path, max_bytes, format="mp3", bitrate="32k"):
    """
    Splits audio into chunks not exceeding max_bytes.
    Returns a list of chunk file paths. If audio fits, returns list with original path.
    """
    file_size = os.path.getsize(file_path)
    if file_size <= max_bytes:
        return [file_path]  # Nothing to split

    audio = AudioSegment.from_file(file_path)
    duration_ms = len(audio)
    orig_size = file_size

    approx_chunk_ms = max(int(duration_ms * (max_bytes / orig_size)) - 1000, 1000)
    chunks = []
    start = 0
    i = 0

    base, _ = os.path.splitext(file_path)

    while start < duration_ms:
        end = min(start + approx_chunk_ms, duration_ms)
        chunk = audio[start:end]
        chunk_path = f"{base}_chunk_{i}.{format}"
        chunk.export(chunk_path, format=format, bitrate=bitrate)

        # Reduce chunk duration if still too large
        while os.path.getsize(chunk_path) > max_bytes and (end - start) > 5000:
            end = start + ((end - start) // 2)
            chunk = audio[start:end]
            chunk.export(chunk_path, format=format, bitrate=bitrate)

        if os.path.getsize(chunk_path) > max_bytes:
            os.remove(chunk_path)
            raise Exception("Audio chunk cannot be reduced below max file size.")

        chunks.append(chunk_path)
        start = end
        i += 1

    return chunks


@router.post("/transcriptions")
async def transcription(
    request: Request,
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    user=Depends(get_verified_user),
):
    log.info(f"file.content_type: {file.content_type}")

    stt_supported_content_types = getattr(
        request.app.state.config, "STT_SUPPORTED_CONTENT_TYPES", []
    )

    if not any(
        fnmatch(file.content_type, content_type)
        for content_type in (
            stt_supported_content_types
            if stt_supported_content_types
            and any(t.strip() for t in stt_supported_content_types)
            else ["audio/*", "video/webm"]
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_NOT_SUPPORTED,
        )

    try:
        ext = file.filename.split(".")[-1]
        id = uuid.uuid4()

        filename = f"{id}.{ext}"
        contents = file.file.read()

        file_dir = f"{CACHE_DIR}/audio/transcriptions"
        os.makedirs(file_dir, exist_ok=True)
        file_path = f"{file_dir}/{filename}"

        with open(file_path, "wb") as f:
            f.write(contents)

        try:
            metadata = None

            if language:
                metadata = {"language": language}

            result = await asyncio.to_thread(transcribe, request, file_path, metadata, user)

            is_admin = getattr(user, "role", None) == "admin"
            if not is_admin:
                redis = request.app.state.redis
                if redis is None:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Credits system is not available.",
                    )

                text = result.get("text") if isinstance(result, dict) else ""
                text = text if isinstance(text, str) else ""

                credits_needed = count_credits(text)
                if credits_needed > 0:
                    now_ts = int(time.time())
                    free_limit = int(
                        getattr(request.app.state.config, "AUDIO_CREDITS_FREE_AUTH", 0) or 0
                    )
                    status_before = await get_credits_status(
                        redis, user_id=user.id, now_ts=now_ts, free_limit=free_limit
                    )
                    if status_before.total_remaining < credits_needed:
                        raise HTTPException(
                            status_code=status.HTTP_402_PAYMENT_REQUIRED,
                            detail="Insufficient credits for voice transcription",
                        )

                    signature_source = f"stt:file:{id}:{credits_needed}:{file.filename or ''}"
                    signature = hashlib.sha256(signature_source.encode("utf-8")).hexdigest()
                    status_after, charged, _exhausted_after = await charge_committed_transcript(
                        redis,
                        user_id=user.id,
                        credits_needed=credits_needed,
                        signature=signature,
                        now_ts=now_ts,
                        free_limit=free_limit,
                    )
                    if charged:
                        free_to_use = min(status_before.free_remaining, credits_needed)
                        paid_to_use = max(0, credits_needed - free_to_use)
                        record_stt_credits_charge(
                            user_id=user.id,
                            signature=signature,
                            credits=credits_needed,
                            free_credits=free_to_use,
                            paid_credits=paid_to_use,
                            now_ts=now_ts,
                        )
                        log.info(
                            "STT transcription credits charged user_id=%s credits=%s free_remaining=%s paid_balance=%s total_remaining=%s",
                            user.id,
                            credits_needed,
                            status_after.free_remaining,
                            status_after.paid_balance,
                            status_after.total_remaining,
                        )

            return {
                **result,
                "filename": os.path.basename(file_path),
            }

        except Exception as e:
            log.exception(e)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e),
            )

    except Exception as e:
        log.exception(e)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


def get_available_models(request: Request) -> list[dict]:
    available_models = []
    if request.app.state.config.TTS_ENGINE == "openai":
        # Use custom endpoint if not using the official OpenAI API URL
        if not request.app.state.config.TTS_OPENAI_API_BASE_URL.startswith(
            "https://api.openai.com"
        ):
            try:
                response = requests.get(
                    f"{request.app.state.config.TTS_OPENAI_API_BASE_URL}/audio/models"
                )
                response.raise_for_status()
                data = response.json()
                available_models = data.get("models", [])
            except Exception as e:
                log.error(f"Error fetching models from custom endpoint: {str(e)}")
                available_models = [{"id": "tts-1"}, {"id": "tts-1-hd"}]
        else:
            available_models = [{"id": "tts-1"}, {"id": "tts-1-hd"}]
    elif request.app.state.config.TTS_ENGINE == "elevenlabs":
        try:
            response = requests.get(
                f"{ELEVENLABS_API_BASE_URL}/v1/models",
                headers={
                    "xi-api-key": request.app.state.config.TTS_API_KEY,
                    "Content-Type": "application/json",
                },
                timeout=5,
            )
            response.raise_for_status()
            models = response.json()

            available_models = [
                {"name": model["name"], "id": model["model_id"]} for model in models
            ]
        except requests.RequestException as e:
            log.error(f"Error fetching voices: {str(e)}")
    return available_models


@router.get("/models")
async def get_models(request: Request, user=Depends(get_verified_user)):
    return {"models": get_available_models(request)}


def get_available_voices(request) -> dict:
    """Returns {voice_id: voice_name} dict"""
    available_voices = {}
    if request.app.state.config.TTS_ENGINE == "openai":
        # Use custom endpoint if not using the official OpenAI API URL
        if not request.app.state.config.TTS_OPENAI_API_BASE_URL.startswith(
            "https://api.openai.com"
        ):
            try:
                response = requests.get(
                    f"{request.app.state.config.TTS_OPENAI_API_BASE_URL}/audio/voices"
                )
                response.raise_for_status()
                data = response.json()
                voices_list = data.get("voices", [])
                available_voices = {voice["id"]: voice["name"] for voice in voices_list}
            except Exception as e:
                log.error(f"Error fetching voices from custom endpoint: {str(e)}")
                available_voices = {
                    "alloy": "alloy",
                    "echo": "echo",
                    "fable": "fable",
                    "onyx": "onyx",
                    "nova": "nova",
                    "shimmer": "shimmer",
                }
        else:
            available_voices = {
                "alloy": "alloy",
                "echo": "echo",
                "fable": "fable",
                "onyx": "onyx",
                "nova": "nova",
                "shimmer": "shimmer",
            }
    elif request.app.state.config.TTS_ENGINE == "elevenlabs":
        try:
            available_voices = get_elevenlabs_voices(
                api_key=request.app.state.config.TTS_API_KEY
            )
        except Exception:
            # Avoided @lru_cache with exception
            pass
    elif request.app.state.config.TTS_ENGINE == "azure":
        try:
            region = request.app.state.config.TTS_AZURE_SPEECH_REGION
            base_url = request.app.state.config.TTS_AZURE_SPEECH_BASE_URL
            url = (
                base_url or f"https://{region}.tts.speech.microsoft.com"
            ) + "/cognitiveservices/voices/list"
            headers = {
                "Ocp-Apim-Subscription-Key": request.app.state.config.TTS_API_KEY
            }

            response = requests.get(url, headers=headers)
            response.raise_for_status()
            voices = response.json()

            for voice in voices:
                available_voices[voice["ShortName"]] = (
                    f"{voice['DisplayName']} ({voice['ShortName']})"
                )
        except requests.RequestException as e:
            log.error(f"Error fetching voices: {str(e)}")

    return available_voices


@lru_cache
def get_elevenlabs_voices(api_key: str) -> dict:
    """
    Note, set the following in your .env file to use Elevenlabs:
    AUDIO_TTS_ENGINE=elevenlabs
    AUDIO_TTS_API_KEY=sk_...  # Your Elevenlabs API key
    AUDIO_TTS_VOICE=EXAVITQu4vr4xnSDxMaL  # From https://api.elevenlabs.io/v1/voices
    AUDIO_TTS_MODEL=eleven_multilingual_v2
    """

    try:
        # TODO: Add retries
        response = requests.get(
            f"{ELEVENLABS_API_BASE_URL}/v1/voices",
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            },
        )
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


@router.get("/voices")
async def get_voices(request: Request, user=Depends(get_verified_user_or_none)):
    return {
        "voices": [
            {"id": k, "name": v} for k, v in get_available_voices(request).items()
        ]
    }


def _get_elevenlabs_realtime_ws_url(base_url: str, *, model_id: str | None) -> str:
    if base_url.startswith("https://"):
        ws_base_url = "wss://" + base_url[len("https://") :]
    elif base_url.startswith("http://"):
        ws_base_url = "ws://" + base_url[len("http://") :]
    else:
        ws_base_url = base_url

    params: dict[str, str] = {
        "audio_format": "pcm_16000",
        "language_code": "kat",
        "commit_strategy": "vad",
        "include_timestamps": "true",
    }

    params["model_id"] = model_id or "scribe_v2_realtime"

    return f"{ws_base_url}/v1/speech-to-text/realtime?{urlencode(params)}"


async def _verify_websocket_user(websocket: WebSocket, token: str | None):
    if not token or token.startswith("sk-"):
        raise HTTPException(status_code=401, detail="Not authenticated")

    decoded = decode_token(token)
    if decoded is None or "id" not in decoded:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if decoded.get("jti") and websocket.app.state.redis:
        revoked = await websocket.app.state.redis.get(
            f"{REDIS_KEY_PREFIX}:auth:token:{decoded['jti']}:revoked"
        )
        if revoked:
            raise HTTPException(status_code=401, detail="Not authenticated")

    user = Users.get_user_by_id(decoded["id"])
    if user is None or user.role not in {"user", "admin"}:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user


@router.websocket("/stt/realtime")
async def stt_realtime(websocket: WebSocket, token: str | None = Query(default=None)):
    await websocket.accept()

    try:
        async def send_error_and_close(*, code: str, message: str, close_code: int = 1000):
            try:
                await websocket.send_json({"type": "error", "code": code, "message": message})
            except Exception:
                pass
            try:
                await websocket.close(code=close_code)
            except Exception:
                pass

        try:
            user = await _verify_websocket_user(websocket, token)
        except HTTPException as e:
            if e.status_code == 401:
                await send_error_and_close(
                    code="AUTH_REQUIRED",
                    message=AUTH_REQUIRED_MESSAGE_KA,
                    close_code=1008,
                )
            else:
                await send_error_and_close(code="ERROR", message=str(e.detail), close_code=1008)
            return

        if websocket.app.state.config.STT_ENGINE != "elevenlabs":
            await send_error_and_close(
                code="STT_DISABLED",
                message="Realtime speech recognition is not enabled.",
                close_code=1008,
            )
            return

        api_key = websocket.app.state.config.AUDIO_STT_ELEVENLABS_API_KEY
        if not api_key:
            await send_error_and_close(
                code="STT_NOT_CONFIGURED",
                message="Realtime speech recognition is not configured.",
                close_code=1011,
            )
            return

        enforce_credits = getattr(user, "role", None) != "admin"

        lock_value: str | None = None
        if enforce_credits:
            if websocket.app.state.redis is None:
                await send_error_and_close(
                    code="CREDITS_UNAVAILABLE",
                    message="Credits system is not available.",
                    close_code=1011,
                )
                return

            now_ts = int(time.time())
            credits_status = await get_credits_status(
                websocket.app.state.redis,
                user_id=user.id,
                now_ts=now_ts,
                free_limit=int(
                    getattr(websocket.app.state.config, "AUDIO_CREDITS_FREE_AUTH", 0) or 0
                ),
            )
            if credits_status.total_remaining <= 0:
                await send_error_and_close(
                    code="LIMIT_EXHAUSTED",
                    message=LIMIT_EXHAUSTED_MESSAGE_KA,
                    close_code=1000,
                )
                return

            lock_value = uuid.uuid4().hex
            acquired = await acquire_session_lock(
                websocket.app.state.redis, user_id=user.id, value=lock_value
            )
            if not acquired:
                await send_error_and_close(
                    code="SESSION_ACTIVE",
                    message="ხმოვანი სესია უკვე აქტიურია.",
                    close_code=1008,
                )
                return

        model_id = websocket.app.state.config.STT_MODEL or None
        elevenlabs_ws_url = _get_elevenlabs_realtime_ws_url(
            ELEVENLABS_API_BASE_URL, model_id=model_id
        )
        log.info(
            "ElevenLabs realtime STT connect url=%s model_id=%s language_code=kat audio_format=pcm_16000 commit_strategy=vad include_timestamps=true",
            elevenlabs_ws_url.split("?", 1)[0],
            model_id or "scribe_v2_realtime",
        )

        lock_refresh_task: asyncio.Task | None = None
        try:
            async def refresh_lock_loop():
                while True:
                    await asyncio.sleep(SESSION_LOCK_REFRESH_SECONDS)
                    await refresh_session_lock(
                        websocket.app.state.redis, user_id=user.id, value=lock_value
                    )

            if enforce_credits:
                lock_refresh_task = asyncio.create_task(refresh_lock_loop())

            async with websockets.connect(
                elevenlabs_ws_url,
                additional_headers={"xi-api-key": api_key},
                ping_interval=20,
                ping_timeout=20,
            ) as eleven_ws:

                async def client_to_elevenlabs():
                    try:
                        while True:
                            message = await websocket.receive()
                            if message["type"] == "websocket.disconnect":
                                return

                            chunk = message.get("bytes")
                            if not chunk:
                                continue

                            await eleven_ws.send(
                                json.dumps(
                                    {
                                        "message_type": "input_audio_chunk",
                                        "audio_base_64": base64.b64encode(chunk).decode(
                                            "ascii"
                                        ),
                                        "commit": False,
                                        "sample_rate": 16000,
                                    }
                                )
                            )
                    except WebSocketDisconnect:
                        return

                async def elevenlabs_to_client():
                    async for message in eleven_ws:
                        if isinstance(message, (bytes, bytearray)):
                            continue

                        if not isinstance(message, str):
                            continue

                        parsed = None
                        try:
                            parsed = json.loads(message)
                        except Exception:
                            await websocket.send_text(message)
                            continue

                        msg_type = parsed.get("message_type")
                        if msg_type not in {
                            "committed_transcript",
                            "committed_transcript_with_timestamps",
                        }:
                            await websocket.send_text(message)
                            continue

                        if not enforce_credits:
                            await websocket.send_text(message)
                            continue

                        text = parsed.get("text") if isinstance(parsed, dict) else ""
                        text = text if isinstance(text, str) else ""
                        credits_needed = count_credits(text)
                        if credits_needed <= 0:
                            await websocket.send_text(message)
                            continue

                        now_ts = int(time.time())
                        status_before = await get_credits_status(
                            websocket.app.state.redis,
                            user_id=user.id,
                            now_ts=now_ts,
                            free_limit=int(
                                getattr(websocket.app.state.config, "AUDIO_CREDITS_FREE_AUTH", 0)
                                or 0
                            ),
                        )
                        if status_before.total_remaining < credits_needed:
                            await send_error_and_close(
                                code="LIMIT_EXHAUSTED",
                                message=LIMIT_EXHAUSTED_MESSAGE_KA,
                                close_code=1000,
                            )
                            try:
                                await eleven_ws.close()
                            except Exception:
                                pass
                            return

                        free_to_use = min(status_before.free_remaining, credits_needed)
                        paid_to_use = max(0, credits_needed - free_to_use)

                        signature = committed_segment_signature(
                            text, words=parsed.get("words") if isinstance(parsed, dict) else None
                        )
                        status_after, charged, exhausted_after = await charge_committed_transcript(
                            websocket.app.state.redis,
                            user_id=user.id,
                            credits_needed=credits_needed,
                            signature=signature,
                            now_ts=now_ts,
                            free_limit=int(
                                getattr(websocket.app.state.config, "AUDIO_CREDITS_FREE_AUTH", 0)
                                or 0
                            ),
                        )
                        if charged:
                            record_stt_credits_charge(
                                user_id=user.id,
                                signature=signature,
                                credits=credits_needed,
                                free_credits=free_to_use,
                                paid_credits=paid_to_use,
                                now_ts=now_ts,
                            )
                            log.info(
                                "Realtime STT credits charged user_id=%s credits=%s free_remaining=%s paid_balance=%s total_remaining=%s",
                                user.id,
                                credits_needed,
                                status_after.free_remaining,
                                status_after.paid_balance,
                                status_after.total_remaining,
                            )

                        await websocket.send_text(message)

                        if exhausted_after:
                            await send_error_and_close(
                                code="LIMIT_EXHAUSTED",
                                message=LIMIT_EXHAUSTED_MESSAGE_KA,
                                close_code=1000,
                            )
                            try:
                                await eleven_ws.close()
                            except Exception:
                                pass
                            return

                client_task = asyncio.create_task(client_to_elevenlabs())
                elevenlabs_task = asyncio.create_task(elevenlabs_to_client())

                done, pending = await asyncio.wait(
                    {client_task, elevenlabs_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
        finally:
            if lock_refresh_task is not None:
                lock_refresh_task.cancel()
                await asyncio.gather(lock_refresh_task, return_exceptions=True)
            if enforce_credits and websocket.app.state.redis is not None and lock_value is not None:
                await release_session_lock(
                    websocket.app.state.redis, user_id=user.id, value=lock_value
                )

    except Exception as e:
        log.exception("Realtime STT error: %s", e)
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "ERROR",
                    "message": "Speech recognition failed. Please try again.",
                }
            )
        except Exception:
            pass
        try:
            await websocket.close(code=1011)
        except Exception:
            pass

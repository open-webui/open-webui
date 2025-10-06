import hashlib
import base64
import shutil
import subprocess
import json
import logging
import os
import uuid
from functools import lru_cache
from pathlib import Path
from pydub import AudioSegment
from pydub.silence import split_on_silence

import aiohttp
import aiofiles
import requests
import mimetypes

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
    APIRouter,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel


from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.config import (
    WHISPER_MODEL_AUTO_UPDATE,
    WHISPER_MODEL_DIR,
    CACHE_DIR,
)

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import (
    AIOHTTP_CLIENT_TIMEOUT,
    ENV,
    SRC_LOG_LEVELS,
    DEVICE_TYPE,
    ENABLE_FORWARD_USER_INFO_HEADERS,
)


router = APIRouter()

# Constants
MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["AUDIO"])

SPEECH_CACHE_DIR = Path(CACHE_DIR).joinpath("./audio/speech/")
SPEECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)


##########################################
#
# Utility functions
#
##########################################

from pydub import AudioSegment
from pydub.utils import mediainfo


def is_mp4_audio(file_path):
    """Check if the given file is an MP4 audio file."""
    if not os.path.isfile(file_path):
        log.error(f"File not found: {file_path}")
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
    log.info(f"Converted {file_path} to {output_path}")


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
    API_KEY: str
    ENGINE: str
    MODEL: str
    VOICE: str
    SPLIT_ON: str
    AZURE_SPEECH_REGION: str
    AZURE_SPEECH_OUTPUT_FORMAT: str


class STTConfigForm(BaseModel):
    OPENAI_API_BASE_URL: str
    OPENAI_API_KEY: str
    PORTKEY_API_BASE_URL: str
    PORTKEY_API_KEY: str
    ENGINE: str
    MODEL: str
    WHISPER_MODEL: str
    DEEPGRAM_API_KEY: str


class AudioConfigUpdateForm(BaseModel):
    tts: TTSConfigForm
    stt: STTConfigForm


@router.get("/config")
async def get_audio_config(request: Request, user=Depends(get_admin_user)):
    return {
        "tts": {
            "OPENAI_API_BASE_URL": request.app.state.config.TTS_OPENAI_API_BASE_URL.get(user.email),
            "OPENAI_API_KEY": request.app.state.config.TTS_OPENAI_API_KEY.get(user.email),
            "API_KEY": request.app.state.config.TTS_API_KEY.get(user.email),
            "ENGINE": request.app.state.config.TTS_ENGINE.get(user.email),
            "MODEL": request.app.state.config.TTS_MODEL.get(user.email),
            "VOICE": request.app.state.config.TTS_VOICE.get(user.email),
            "SPLIT_ON": request.app.state.config.TTS_SPLIT_ON.get(user.email),
            "AZURE_SPEECH_REGION": request.app.state.config.TTS_AZURE_SPEECH_REGION.get(user.email),
            "AZURE_SPEECH_OUTPUT_FORMAT": request.app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT.get(user.email),
        },
        "stt": {
            "OPENAI_API_BASE_URL": request.app.state.config.STT_OPENAI_API_BASE_URL.get(user.email),
            "OPENAI_API_KEY": request.app.state.config.STT_OPENAI_API_KEY.get(user.email),
            "PORTKEY_API_BASE_URL": request.app.state.config.STT_PORTKEY_API_BASE_URL.get(user.email),
            "PORTKEY_API_KEY": request.app.state.config.STT_PORTKEY_API_KEY.get(user.email),
            "ENGINE": request.app.state.config.STT_ENGINE.get(user.email),
            "MODEL": request.app.state.config.STT_MODEL.get(user.email),
            "WHISPER_MODEL": request.app.state.config.WHISPER_MODEL.get(user.email),
            "DEEPGRAM_API_KEY": request.app.state.config.DEEPGRAM_API_KEY,
        },
    }


@router.post("/config/update")
async def update_audio_config(
    request: Request, form_data: AudioConfigUpdateForm, user=Depends(get_admin_user)
):
    request.app.state.config.TTS_OPENAI_API_BASE_URL.set(user.email, form_data.tts.OPENAI_API_BASE_URL)
    request.app.state.config.TTS_OPENAI_API_KEY.set(user.email, form_data.tts.OPENAI_API_KEY)
    request.app.state.config.TTS_API_KEY.set(user.email, form_data.tts.API_KEY)
    request.app.state.config.TTS_ENGINE.set(user.email, form_data.tts.ENGINE)
    request.app.state.config.TTS_MODEL.set(user.email, form_data.tts.MODEL)
    request.app.state.config.TTS_VOICE.set(user.email, form_data.tts.VOICE)
    request.app.state.config.TTS_SPLIT_ON.set(user.email, form_data.tts.SPLIT_ON)
    request.app.state.config.TTS_AZURE_SPEECH_REGION.set(user.email, form_data.tts.AZURE_SPEECH_REGION)
    request.app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT.set(user.email, form_data.tts.AZURE_SPEECH_OUTPUT_FORMAT)

    request.app.state.config.STT_OPENAI_API_BASE_URL.set(user.email, form_data.stt.OPENAI_API_BASE_URL)
    request.app.state.config.STT_OPENAI_API_KEY.set(user.email, form_data.stt.OPENAI_API_KEY)
    request.app.state.config.STT_PORTKEY_API_BASE_URL.set(user.email, form_data.stt.PORTKEY_API_BASE_URL)
    request.app.state.config.STT_PORTKEY_API_KEY.set(user.email, form_data.stt.PORTKEY_API_KEY)
    request.app.state.config.STT_ENGINE.set(user.email, form_data.stt.ENGINE)
    request.app.state.config.STT_MODEL.set(user.email, form_data.stt.MODEL)
    request.app.state.config.WHISPER_MODEL.set(user.email, form_data.stt.WHISPER_MODEL)
    request.app.state.config.DEEPGRAM_API_KEY = form_data.stt.DEEPGRAM_API_KEY

    if request.app.state.config.STT_ENGINE.get(user.email) == "":
        # Update user-specific whisper model
        whisper_model_name = form_data.stt.WHISPER_MODEL
        request.app.state.config.WHISPER_MODEL.set(user.email, whisper_model_name)
        
        # Initialize user-specific whisper model cache if needed
        if not hasattr(request.app.state, 'user_whisper_models'):
            request.app.state.user_whisper_models = {}
        
        user_model_key = f"{user.email}:{whisper_model_name}"
        request.app.state.user_whisper_models[user_model_key] = set_faster_whisper_model(
            whisper_model_name, WHISPER_MODEL_AUTO_UPDATE
        )

    return {
        "tts": {
            "OPENAI_API_BASE_URL": request.app.state.config.TTS_OPENAI_API_BASE_URL.get(user.email),
            "OPENAI_API_KEY": request.app.state.config.TTS_OPENAI_API_KEY.get(user.email),
            "API_KEY": request.app.state.config.TTS_API_KEY.get(user.email),
            "ENGINE": request.app.state.config.TTS_ENGINE.get(user.email),
            "MODEL": request.app.state.config.TTS_MODEL.get(user.email),
            "VOICE": request.app.state.config.TTS_VOICE.get(user.email),
            "SPLIT_ON": request.app.state.config.TTS_SPLIT_ON.get(user.email),
            "AZURE_SPEECH_REGION": request.app.state.config.TTS_AZURE_SPEECH_REGION.get(user.email),
            "AZURE_SPEECH_OUTPUT_FORMAT": request.app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT.get(user.email),
        },
        "stt": {
            "OPENAI_API_BASE_URL": request.app.state.config.STT_OPENAI_API_BASE_URL.get(user.email),
            "OPENAI_API_KEY": request.app.state.config.STT_OPENAI_API_KEY.get(user.email),
            "PORTKEY_API_BASE_URL": request.app.state.config.STT_PORTKEY_API_BASE_URL.get(user.email),
            "PORTKEY_API_KEY": request.app.state.config.STT_PORTKEY_API_KEY.get(user.email),
            "ENGINE": request.app.state.config.STT_ENGINE.get(user.email),
            "MODEL": request.app.state.config.STT_MODEL.get(user.email),
            "WHISPER_MODEL": request.app.state.config.WHISPER_MODEL.get(user.email),
            "DEEPGRAM_API_KEY": request.app.state.config.DEEPGRAM_API_KEY,
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


@router.post("/speech")
async def speech(request: Request, user=Depends(get_verified_user)):
    body = await request.body()
    name = hashlib.sha256(
        body
        + str(request.app.state.config.TTS_ENGINE).encode("utf-8")
        + str(request.app.state.config.TTS_MODEL).encode("utf-8")
    ).hexdigest()

    file_path = SPEECH_CACHE_DIR.joinpath(f"{name}.mp3")
    file_body_path = SPEECH_CACHE_DIR.joinpath(f"{name}.json")

    # Check if the file already exists in the cache
    if file_path.is_file():
        return FileResponse(file_path)

    payload = None
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    tts_engine = request.app.state.config.TTS_ENGINE.get(user.email)
    if tts_engine == "openai":
        payload["model"] = request.app.state.config.TTS_MODEL.get(user.email)

        try:
            timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
            async with aiohttp.ClientSession(
                timeout=timeout, trust_env=True
            ) as session:
                async with session.post(
                    url=f"{request.app.state.config.TTS_OPENAI_API_BASE_URL.get(user.email)}/audio/speech",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {request.app.state.config.TTS_OPENAI_API_KEY.get(user.email)}",
                        **(
                            {
                                "X-OpenWebUI-User-Name": user.name,
                                "X-OpenWebUI-User-Id": user.id,
                                "X-OpenWebUI-User-Email": user.email,
                                "X-OpenWebUI-User-Role": user.role,
                            }
                            if ENABLE_FORWARD_USER_INFO_HEADERS
                            else {}
                        ),
                    },
                ) as r:
                    r.raise_for_status()

                    async with aiofiles.open(file_path, "wb") as f:
                        await f.write(await r.read())

                    async with aiofiles.open(file_body_path, "w") as f:
                        await f.write(json.dumps(payload))

            return FileResponse(file_path)

        except Exception as e:
            log.exception(e)
            detail = None

            try:
                if r.status != 200:
                    res = await r.json()

                    if "error" in res:
                        detail = f"External: {res['error'].get('message', '')}"
            except Exception:
                detail = f"External: {e}"

            raise HTTPException(
                status_code=getattr(r, "status", 500),
                detail=detail if detail else "Open WebUI: Server Connection Error",
            )

    elif tts_engine == "elevenlabs":
        voice_id = payload.get("voice", "")

        if voice_id not in get_available_voices(request, user):
            raise HTTPException(
                status_code=400,
                detail="Invalid voice id",
            )

        try:
            timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
            async with aiohttp.ClientSession(
                timeout=timeout, trust_env=True
            ) as session:
                async with session.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    json={
                        "text": payload["input"],
                        "model_id": request.app.state.config.TTS_MODEL.get(user.email),
                        "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
                    },
                    headers={
                        "Accept": "audio/mpeg",
                        "Content-Type": "application/json",
                        "xi-api-key": request.app.state.config.TTS_API_KEY.get(user.email),
                    },
                ) as r:
                    r.raise_for_status()

                    async with aiofiles.open(file_path, "wb") as f:
                        await f.write(await r.read())

                    async with aiofiles.open(file_body_path, "w") as f:
                        await f.write(json.dumps(payload))

            return FileResponse(file_path)

        except Exception as e:
            log.exception(e)
            detail = None

            try:
                if r.status != 200:
                    res = await r.json()
                    if "error" in res:
                        detail = f"External: {res['error'].get('message', '')}"
            except Exception:
                detail = f"External: {e}"

            raise HTTPException(
                status_code=getattr(r, "status", 500),
                detail=detail if detail else "Open WebUI: Server Connection Error",
            )

    elif tts_engine == "azure":
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            log.exception(e)
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        region = request.app.state.config.TTS_AZURE_SPEECH_REGION.get(user.email)
        language = request.app.state.config.TTS_VOICE.get(user.email)
        locale = "-".join(request.app.state.config.TTS_VOICE.get(user.email).split("-")[:1])
        output_format = request.app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT.get(user.email)

        try:
            data = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{locale}">
                <voice name="{language}">{payload["input"]}</voice>
            </speak>"""
            timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
            async with aiohttp.ClientSession(
                timeout=timeout, trust_env=True
            ) as session:
                async with session.post(
                    f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
                    headers={
                        "Ocp-Apim-Subscription-Key": request.app.state.config.TTS_API_KEY.get(user.email),
                        "Content-Type": "application/ssml+xml",
                        "X-Microsoft-OutputFormat": output_format,
                    },
                    data=data,
                ) as r:
                    r.raise_for_status()

                    async with aiofiles.open(file_path, "wb") as f:
                        await f.write(await r.read())

                    async with aiofiles.open(file_body_path, "w") as f:
                        await f.write(json.dumps(payload))

                    return FileResponse(file_path)

        except Exception as e:
            log.exception(e)
            detail = None

            try:
                if r.status != 200:
                    res = await r.json()
                    if "error" in res:
                        detail = f"External: {res['error'].get('message', '')}"
            except Exception:
                detail = f"External: {e}"

            raise HTTPException(
                status_code=getattr(r, "status", 500),
                detail=detail if detail else "Open WebUI: Server Connection Error",
            )

    elif tts_engine == "transformers":
        payload = None
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            log.exception(e)
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        import torch
        import soundfile as sf

        load_speech_pipeline(request)

        embeddings_dataset = request.app.state.speech_speaker_embeddings_dataset

        speaker_index = 6799
        try:
            speaker_index = embeddings_dataset["filename"].index(
                request.app.state.config.TTS_MODEL.get(user.email)
            )
        except Exception:
            pass

        speaker_embedding = torch.tensor(
            embeddings_dataset[speaker_index]["xvector"]
        ).unsqueeze(0)

        speech = request.app.state.speech_synthesiser(
            payload["input"],
            forward_params={"speaker_embeddings": speaker_embedding},
        )

        sf.write(file_path, speech["audio"], samplerate=speech["sampling_rate"])

        async with aiofiles.open(file_body_path, "w") as f:
            await f.write(json.dumps(payload))

        return FileResponse(file_path)
    
    else:
        # No TTS engine configured
        raise HTTPException(
            status_code=400,
            detail="TTS engine not configured. Please configure a TTS engine in the audio settings.",
        )


def transcribe(request: Request, file_path, user):
    log.info(f"transcribe: {file_path}")
    filename = os.path.basename(file_path)
    file_dir = os.path.dirname(file_path)
    id = filename.split(".")[0]

    stt_engine = request.app.state.config.STT_ENGINE.get(user.email)
    if stt_engine == "":
        # Get user-specific whisper model
        whisper_model_name = request.app.state.config.WHISPER_MODEL.get(user.email)
        
        # Initialize whisper model if needed (user-specific)
        if not hasattr(request.app.state, 'user_whisper_models'):
            request.app.state.user_whisper_models = {}
        
        user_model_key = f"{user.email}:{whisper_model_name}"
        if user_model_key not in request.app.state.user_whisper_models:
            request.app.state.user_whisper_models[user_model_key] = set_faster_whisper_model(
                whisper_model_name, WHISPER_MODEL_AUTO_UPDATE
            )

        model = request.app.state.user_whisper_models[user_model_key]
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

        log.debug(data)
        return data
    elif stt_engine == "openai":
        if is_mp4_audio(file_path):
            os.rename(file_path, file_path.replace(".wav", ".mp4"))
            # Convert MP4 audio file to WAV format
            convert_mp4_to_wav(file_path.replace(".wav", ".mp4"), file_path)

        r = None
        try:
            r = requests.post(
                url=f"{request.app.state.config.STT_OPENAI_API_BASE_URL.get(user.email)}/audio/transcriptions",
                headers={
                    "Authorization": f"Bearer {request.app.state.config.STT_OPENAI_API_KEY.get(user.email)}"
                },
                files={"file": (filename, open(file_path, "rb"))},
                data={"model": request.app.state.config.STT_MODEL.get(user.email)},
            )

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

            raise Exception(detail if detail else "Open WebUI: Server Connection Error")

    elif stt_engine == "portkey":
        try:
            # Ensure true WAV for Portkey (browser may upload WebM mislabeled as WAV)
            def _is_wav(path: str) -> bool:
                try:
                    with open(path, "rb") as _f:
                        header = _f.read(12)
                        return len(header) >= 12 and header[0:4] == b"RIFF" and header[8:12] == b"WAVE"
                except Exception:
                    return False

            if not _is_wav(file_path):
                ffmpeg_bin = shutil.which("ffmpeg")
                if not ffmpeg_bin:
                    raise Exception(
                        "FFmpeg not found. Install ffmpeg to convert WebM/Opus to 16kHz mono WAV for Portkey STT."
                    )

                file_dir = os.path.dirname(file_path)
                src_basename = os.path.basename(file_path).split(".")[0]
                # Write to a different output path to avoid in-place overwrite
                wav_out = os.path.join(file_dir, f"{src_basename}_conv.wav")

                # Convert to 16kHz mono WAV
                cmd = [
                    ffmpeg_bin,
                    "-y",
                    "-i",
                    file_path,
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    "-f",
                    "wav",
                    wav_out,
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                file_path = wav_out

            with open(file_path, "rb") as f:
                audio_bytes = f.read()
            
            # Log that the audio bytes are being sent to Portkey
            log.info(f"Sending audio bytes to Portkey")

            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            fmt = "wav"

            payload = {
                "model": request.app.state.config.STT_MODEL.get(user.email),
                "messages": [
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "text",
                                "text": "You are a verbatim speech transcriber. Convert the user's audio into text exactly as spoken, with zero changes.\n- Transcribe strictly in the same language(s) spoken (German or English). Do not translate.\n- Do not add, remove, or change any words, names, spellings, grammar, casing, or numbers. Say them as spoken.\n- Keep filler words, hesitations, repetitions, requests, false starts, and slang exactly as spoken.\n- Do not add timestamps, labels, brackets, tags, or any commentary (e.g., no [inaudible], no [music], no Speaker 1).\n- If any part is unclear, transcribe what you hear without guessing or adding markers.\n- Output only the transcript text and nothing else."
                            }
                        ]
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": ""},
                            {"type": "input_audio", "input_audio": {"data": audio_b64, "format": fmt}}
                        ]
                    }
                ],
                "temperature": 0,
                "max_tokens": 256,
                "top_p": 1,
                "modalities": ["text"],
                "stream": False
            }

            url = request.app.state.config.STT_PORTKEY_API_BASE_URL.get(user.email) + "/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "x-portkey-api-key": request.app.state.config.STT_PORTKEY_API_KEY.get(user.email),
            }

            r = requests.post(url, headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            resp = r.json()

            transcript_text = ""
            try:
                choice = resp.get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content", "")
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            transcript_text = item["text"]
                            break
                elif isinstance(content, str):
                    transcript_text = content
            except Exception:
                pass

            data = {"text": (transcript_text or "").strip()}

            # Log successfully received transcript from Portkey
            log.info(f"Successfully received transcript from Portkey: {data}")

            transcript_file = f"{file_dir}/{id}.json"
            with open(transcript_file, "w") as f:
                json.dump(data, f)

            return data
        except Exception as e:
            log.exception(e)
            detail = None
            try:
                res = r.json() if r is not None else {}
                if "error" in res:
                    detail = f"External: {res['error'].get('message', '')}"
            except Exception:
                detail = f"External: {e}"
            raise Exception(detail if detail else "Open WebUI: Server Connection Error")

    elif stt_engine == "deepgram":
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

            # Add model if specified
            params = {}
            stt_model = request.app.state.config.STT_MODEL.get(user.email)
            if stt_model:
                params["model"] = stt_model

            # Make request to Deepgram API
            r = requests.post(
                "https://api.deepgram.com/v1/listen",
                headers=headers,
                params=params,
                data=file_data,
            )
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
            raise Exception(detail if detail else "Open WebUI: Server Connection Error")


def compress_audio(file_path):
    if os.path.getsize(file_path) > MAX_FILE_SIZE:
        file_dir = os.path.dirname(file_path)
        audio = AudioSegment.from_file(file_path)
        audio = audio.set_frame_rate(16000).set_channels(1)  # Compress audio
        compressed_path = f"{file_dir}/{id}_compressed.opus"
        audio.export(compressed_path, format="opus", bitrate="32k")
        log.debug(f"Compressed audio to {compressed_path}")

        if (
            os.path.getsize(compressed_path) > MAX_FILE_SIZE
        ):  # Still larger than MAX_FILE_SIZE after compression
            raise Exception(ERROR_MESSAGES.FILE_TOO_LARGE(size=f"{MAX_FILE_SIZE_MB}MB"))
        return compressed_path
    else:
        return file_path


@router.post("/transcriptions")
def transcription(
    request: Request,
    file: UploadFile = File(...),
    user=Depends(get_verified_user),
):
    log.info(f"file.content_type: {file.content_type}")

    if file.content_type not in ["audio/mpeg", "audio/wav", "audio/ogg", "audio/x-m4a", "audio/webm"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_NOT_SUPPORTED,
        )

    try:
        # Preserve original extension if present; map webm to webm
        ext = file.filename.split(".")[-1] if "." in file.filename else "webm" if file.content_type == "audio/webm" else "wav"
        id = uuid.uuid4()

        filename = f"{id}.{ext}"
        contents = file.file.read()

        file_dir = f"{CACHE_DIR}/audio/transcriptions"
        os.makedirs(file_dir, exist_ok=True)
        file_path = f"{file_dir}/{filename}"

        with open(file_path, "wb") as f:
            f.write(contents)

        try:
            try:
                file_path = compress_audio(file_path)
            except Exception as e:
                log.exception(e)

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT(e),
                )

            data = transcribe(request, file_path, user)
            file_path = file_path.split("/")[-1]
            return {**data, "filename": file_path}
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


def get_available_models(request: Request, user) -> list[dict]:
    available_models = []
    tts_engine = request.app.state.config.TTS_ENGINE.get(user.email)
    if tts_engine == "openai":
        # Use custom endpoint if not using the official OpenAI API URL
        tts_base_url = request.app.state.config.TTS_OPENAI_API_BASE_URL.get(user.email)
        if not tts_base_url.startswith(
            "https://api.openai.com"
        ):
            try:
                response = requests.get(
                    f"{tts_base_url}/audio/models"
                )
                response.raise_for_status()
                data = response.json()
                available_models = data.get("models", [])
            except Exception as e:
                log.error(f"Error fetching models from custom endpoint: {str(e)}")
                available_models = [{"id": "tts-1"}, {"id": "tts-1-hd"}]
        else:
            available_models = [{"id": "tts-1"}, {"id": "tts-1-hd"}]
    elif tts_engine == "elevenlabs":
        try:
            response = requests.get(
                "https://api.elevenlabs.io/v1/models",
                headers={
                    "xi-api-key": request.app.state.config.TTS_API_KEY.get(user.email),
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
    return {"models": get_available_models(request, user)}


def get_available_voices(request, user) -> dict:
    """Returns {voice_id: voice_name} dict"""
    available_voices = {}
    tts_engine = request.app.state.config.TTS_ENGINE.get(user.email)
    if tts_engine == "openai":
        # Use custom endpoint if not using the official OpenAI API URL
        tts_base_url = request.app.state.config.TTS_OPENAI_API_BASE_URL.get(user.email)
        if not tts_base_url.startswith(
            "https://api.openai.com"
        ):
            try:
                response = requests.get(
                    f"{tts_base_url}/audio/voices"
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
    elif tts_engine == "elevenlabs":
        try:
            available_voices = get_elevenlabs_voices(
                api_key=request.app.state.config.TTS_API_KEY.get(user.email)
            )
        except Exception:
            # Avoided @lru_cache with exception
            pass
    elif tts_engine == "azure":
        try:
            region = request.app.state.config.TTS_AZURE_SPEECH_REGION.get(user.email)
            url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list"
            headers = {
                "Ocp-Apim-Subscription-Key": request.app.state.config.TTS_API_KEY.get(user.email)
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
            "https://api.elevenlabs.io/v1/voices",
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
async def get_voices(request: Request, user=Depends(get_verified_user)):
    return {
        "voices": [
            {"id": k, "name": v} for k, v in get_available_voices(request, user).items()
        ]
    }

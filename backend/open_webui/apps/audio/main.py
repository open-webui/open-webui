import hashlib
import json
import logging
import os
import uuid
from functools import lru_cache
from pathlib import Path
from pydub import AudioSegment
from pydub.silence import split_on_silence

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
    AUDIO_TTS_AZURE_SPEECH_REGION,
    AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT,
    CACHE_DIR,
    CORS_ALLOW_ORIGIN,
    WHISPER_MODEL,
    WHISPER_MODEL_AUTO_UPDATE,
    WHISPER_MODEL_DIR,
    AppConfig,
)

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS, DEVICE_TYPE, ENABLE_FORWARD_USER_INFO_HEADERS
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from open_webui.utils.utils import get_admin_user, get_verified_user

# Constants
MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes


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

app.state.config.WHISPER_MODEL = WHISPER_MODEL
app.state.faster_whisper_model = None

app.state.config.TTS_OPENAI_API_BASE_URL = AUDIO_TTS_OPENAI_API_BASE_URL
app.state.config.TTS_OPENAI_API_KEY = AUDIO_TTS_OPENAI_API_KEY
app.state.config.TTS_ENGINE = AUDIO_TTS_ENGINE
app.state.config.TTS_MODEL = AUDIO_TTS_MODEL
app.state.config.TTS_VOICE = AUDIO_TTS_VOICE
app.state.config.TTS_API_KEY = AUDIO_TTS_API_KEY
app.state.config.TTS_SPLIT_ON = AUDIO_TTS_SPLIT_ON


app.state.speech_synthesiser = None
app.state.speech_speaker_embeddings_dataset = None

app.state.config.TTS_AZURE_SPEECH_REGION = AUDIO_TTS_AZURE_SPEECH_REGION
app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT = AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT

# setting device type for whisper model
whisper_device_type = DEVICE_TYPE if DEVICE_TYPE and DEVICE_TYPE == "cuda" else "cpu"
log.info(f"whisper_device_type: {whisper_device_type}")

SPEECH_CACHE_DIR = Path(CACHE_DIR).joinpath("./audio/speech/")
SPEECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def set_faster_whisper_model(model: str, auto_update: bool = False):
    if model and app.state.config.STT_ENGINE == "":
        from faster_whisper import WhisperModel

        faster_whisper_kwargs = {
            "model_size_or_path": model,
            "device": whisper_device_type,
            "compute_type": "int8",
            "download_root": WHISPER_MODEL_DIR,
            "local_files_only": not auto_update,
        }

        try:
            app.state.faster_whisper_model = WhisperModel(**faster_whisper_kwargs)
        except Exception:
            log.warning(
                "WhisperModel initialization failed, attempting download with local_files_only=False"
            )
            faster_whisper_kwargs["local_files_only"] = False
            app.state.faster_whisper_model = WhisperModel(**faster_whisper_kwargs)

    else:
        app.state.faster_whisper_model = None


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
    ENGINE: str
    MODEL: str
    WHISPER_MODEL: str


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
            "AZURE_SPEECH_REGION": app.state.config.TTS_AZURE_SPEECH_REGION,
            "AZURE_SPEECH_OUTPUT_FORMAT": app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT,
        },
        "stt": {
            "OPENAI_API_BASE_URL": app.state.config.STT_OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": app.state.config.STT_OPENAI_API_KEY,
            "ENGINE": app.state.config.STT_ENGINE,
            "MODEL": app.state.config.STT_MODEL,
            "WHISPER_MODEL": app.state.config.WHISPER_MODEL,
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
    app.state.config.TTS_AZURE_SPEECH_REGION = form_data.tts.AZURE_SPEECH_REGION
    app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT = (
        form_data.tts.AZURE_SPEECH_OUTPUT_FORMAT
    )

    app.state.config.STT_OPENAI_API_BASE_URL = form_data.stt.OPENAI_API_BASE_URL
    app.state.config.STT_OPENAI_API_KEY = form_data.stt.OPENAI_API_KEY
    app.state.config.STT_ENGINE = form_data.stt.ENGINE
    app.state.config.STT_MODEL = form_data.stt.MODEL
    app.state.config.WHISPER_MODEL = form_data.stt.WHISPER_MODEL
    set_faster_whisper_model(form_data.stt.WHISPER_MODEL, WHISPER_MODEL_AUTO_UPDATE)

    return {
        "tts": {
            "OPENAI_API_BASE_URL": app.state.config.TTS_OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": app.state.config.TTS_OPENAI_API_KEY,
            "API_KEY": app.state.config.TTS_API_KEY,
            "ENGINE": app.state.config.TTS_ENGINE,
            "MODEL": app.state.config.TTS_MODEL,
            "VOICE": app.state.config.TTS_VOICE,
            "SPLIT_ON": app.state.config.TTS_SPLIT_ON,
            "AZURE_SPEECH_REGION": app.state.config.TTS_AZURE_SPEECH_REGION,
            "AZURE_SPEECH_OUTPUT_FORMAT": app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT,
        },
        "stt": {
            "OPENAI_API_BASE_URL": app.state.config.STT_OPENAI_API_BASE_URL,
            "OPENAI_API_KEY": app.state.config.STT_OPENAI_API_KEY,
            "ENGINE": app.state.config.STT_ENGINE,
            "MODEL": app.state.config.STT_MODEL,
            "WHISPER_MODEL": app.state.config.WHISPER_MODEL,
        },
    }


def load_speech_pipeline():
    from transformers import pipeline
    from datasets import load_dataset

    if app.state.speech_synthesiser is None:
        app.state.speech_synthesiser = pipeline(
            "text-to-speech", "microsoft/speecht5_tts"
        )

    if app.state.speech_speaker_embeddings_dataset is None:
        app.state.speech_speaker_embeddings_dataset = load_dataset(
            "Matthijs/cmu-arctic-xvectors", split="validation"
        )


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

        if ENABLE_FORWARD_USER_INFO_HEADERS:
            headers["X-OpenWebUI-User-Name"] = user.name
            headers["X-OpenWebUI-User-Id"] = user.id
            headers["X-OpenWebUI-User-Email"] = user.email
            headers["X-OpenWebUI-User-Role"] = user.role

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

    elif app.state.config.TTS_ENGINE == "azure":
        payload = None
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            log.exception(e)
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        region = app.state.config.TTS_AZURE_SPEECH_REGION
        language = app.state.config.TTS_VOICE
        locale = "-".join(app.state.config.TTS_VOICE.split("-")[:1])
        output_format = app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT
        url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

        headers = {
            "Ocp-Apim-Subscription-Key": app.state.config.TTS_API_KEY,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": output_format,
        }

        data = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{locale}">
                <voice name="{language}">{payload["input"]}</voice>
            </speak>"""

        response = requests.post(url, headers=headers, data=data)

        if response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(response.content)
            return FileResponse(file_path)
        else:
            log.error(f"Error synthesizing speech - {response.reason}")
            raise HTTPException(
                status_code=500, detail=f"Error synthesizing speech - {response.reason}"
            )
    elif app.state.config.TTS_ENGINE == "transformers":
        payload = None
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            log.exception(e)
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        import torch
        import soundfile as sf

        load_speech_pipeline()

        embeddings_dataset = app.state.speech_speaker_embeddings_dataset

        speaker_index = 6799
        try:
            speaker_index = embeddings_dataset["filename"].index(
                app.state.config.TTS_MODEL
            )
        except Exception:
            pass

        speaker_embedding = torch.tensor(
            embeddings_dataset[speaker_index]["xvector"]
        ).unsqueeze(0)

        speech = app.state.speech_synthesiser(
            payload["input"],
            forward_params={"speaker_embeddings": speaker_embedding},
        )

        sf.write(file_path, speech["audio"], samplerate=speech["sampling_rate"])
        with open(file_body_path, "w") as f:
            json.dump(json.loads(body.decode("utf-8")), f)

        return FileResponse(file_path)


def transcribe(file_path):
    print("transcribe", file_path)
    filename = os.path.basename(file_path)
    file_dir = os.path.dirname(file_path)
    id = filename.split(".")[0]

    if app.state.config.STT_ENGINE == "":
        if app.state.faster_whisper_model is None:
            set_faster_whisper_model(app.state.config.WHISPER_MODEL)

        model = app.state.faster_whisper_model
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
    elif app.state.config.STT_ENGINE == "openai":
        if is_mp4_audio(file_path):
            print("is_mp4_audio")
            os.rename(file_path, file_path.replace(".wav", ".mp4"))
            # Convert MP4 audio file to WAV format
            convert_mp4_to_wav(file_path.replace(".wav", ".mp4"), file_path)

        headers = {"Authorization": f"Bearer {app.state.config.STT_OPENAI_API_KEY}"}

        files = {"file": (filename, open(file_path, "rb"))}
        data = {"model": app.state.config.STT_MODEL}

        log.debug(files, data)

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
                except Exception:
                    error_detail = f"External: {e}"

            raise Exception(error_detail)


@app.post("/transcriptions")
def transcription(
    file: UploadFile = File(...),
    user=Depends(get_verified_user),
):
    log.info(f"file.content_type: {file.content_type}")

    if file.content_type not in ["audio/mpeg", "audio/wav", "audio/ogg", "audio/x-m4a"]:
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
            if os.path.getsize(file_path) > MAX_FILE_SIZE:  # file is bigger than 25MB
                log.debug(f"File size is larger than {MAX_FILE_SIZE_MB}MB")
                audio = AudioSegment.from_file(file_path)
                audio = audio.set_frame_rate(16000).set_channels(1)  # Compress audio
                compressed_path = f"{file_dir}/{id}_compressed.opus"
                audio.export(compressed_path, format="opus", bitrate="32k")
                log.debug(f"Compressed audio to {compressed_path}")
                file_path = compressed_path

                if (
                    os.path.getsize(file_path) > MAX_FILE_SIZE
                ):  # Still larger than 25MB after compression
                    log.debug(
                        f"Compressed file size is still larger than {MAX_FILE_SIZE_MB}MB: {os.path.getsize(file_path)}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=ERROR_MESSAGES.FILE_TOO_LARGE(
                            size=f"{MAX_FILE_SIZE_MB}MB"
                        ),
                    )

                data = transcribe(file_path)
            else:
                data = transcribe(file_path)

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
                "https://api.elevenlabs.io/v1/models", headers=headers, timeout=5
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
    elif app.state.config.TTS_ENGINE == "azure":
        try:
            region = app.state.config.TTS_AZURE_SPEECH_REGION
            url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list"
            headers = {"Ocp-Apim-Subscription-Key": app.state.config.TTS_API_KEY}

            response = requests.get(url, headers=headers)
            response.raise_for_status()
            voices = response.json()
            for voice in voices:
                ret[voice["ShortName"]] = (
                    f"{voice['DisplayName']} ({voice['ShortName']})"
                )
        except requests.RequestException as e:
            log.error(f"Error fetching voices: {str(e)}")

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

from fastapi import (FastAPI)
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import logging

from config import (
    SRC_LOG_LEVELS,
    CACHE_DIR,
    UPLOAD_DIR,
    WHISPER_MODEL,
    WHISPER_MODEL_DIR,
    WHISPER_MODEL_AUTO_UPDATE,
    DEVICE_TYPE,
    AUDIO_STT_OPENAI_API_BASE_URL,
    AUDIO_STT_OPENAI_API_KEY,
    AUDIO_TTS_OPENAI_API_BASE_URL,
    AUDIO_TTS_OPENAI_API_KEY,
    AUDIO_TTS_ALLTALK_API_BASE_URL,
    AUDIO_TTS_ALLTALK_API_MODEL,
    AUDIO_TTS_ALLTALK_API_VOICE,
    AUDIO_TTS_ALLTALK_API_DEEPSPEED,
    AUDIO_TTS_ALLTALK_API_LOW_VRAM,
    AUDIO_TTS_ALLTALK_API_USE_STREAMING,
    AUDIO_TTS_ALLTALK_API_USE_NARRATOR,
    AUDIO_TTS_ALLTALK_API_NARRATOR_VOICE,
    AUDIO_STT_ENGINE,
    AUDIO_STT_MODEL,
    AUDIO_TTS_ENGINE,
    AUDIO_TTS_MODEL,
    AUDIO_TTS_VOICE,
    AppConfig,
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.config = AppConfig()

# setting openai api config
app.state.config.STT_OPENAI_API_BASE_URL = AUDIO_STT_OPENAI_API_BASE_URL
app.state.config.STT_OPENAI_API_KEY = AUDIO_STT_OPENAI_API_KEY
app.state.config.TTS_OPENAI_API_BASE_URL = AUDIO_TTS_OPENAI_API_BASE_URL
app.state.config.TTS_OPENAI_API_KEY = AUDIO_TTS_OPENAI_API_KEY

# setting alltalk api config
app.state.config.TTS_ALLTALK_API_BASE_URL = AUDIO_TTS_ALLTALK_API_BASE_URL
app.state.config.TTS_ALLTALK_API_MODEL = AUDIO_TTS_ALLTALK_API_MODEL
app.state.config.TTS_ALLTALK_API_VOICE = AUDIO_TTS_ALLTALK_API_VOICE
app.state.config.TTS_ALLTALK_API_DEEPSPEED = AUDIO_TTS_ALLTALK_API_DEEPSPEED
app.state.config.TTS_ALLTALK_API_LOW_VRAM = AUDIO_TTS_ALLTALK_API_LOW_VRAM
app.state.config.TTS_ALLTALK_API_USE_STREAMING = AUDIO_TTS_ALLTALK_API_USE_STREAMING
app.state.config.TTS_ALLTALK_API_USE_NARRATOR = AUDIO_TTS_ALLTALK_API_USE_NARRATOR
app.state.config.TTS_ALLTALK_API_NARRATOR_VOICE = AUDIO_TTS_ALLTALK_API_NARRATOR_VOICE

# setting general config
app.state.config.STT_ENGINE = AUDIO_STT_ENGINE
app.state.config.STT_MODEL = AUDIO_STT_MODEL

app.state.config.TTS_ENGINE = AUDIO_TTS_ENGINE
app.state.config.TTS_MODEL = AUDIO_TTS_MODEL
app.state.config.TTS_VOICE = AUDIO_TTS_VOICE


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["AUDIO"])

# setting device type for whisper model
WHISPER_DEVICE_TYPE = DEVICE_TYPE if DEVICE_TYPE and DEVICE_TYPE == "cuda" else "cpu"
log.info(f"WHISPER_DEVICE_TYPE: {WHISPER_DEVICE_TYPE}")

SPEECH_CACHE_DIR = Path(CACHE_DIR).joinpath("./audio/speech/")
SPEECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_config():
    return app.state.config
from fastapi import (FastAPI)
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import logging

from config import (
    SRC_LOG_LEVELS,
    CACHE_DIR,
    AUDIO_OPENAI_API_BASE_URL,
    AUDIO_OPENAI_API_KEY,
    AUDIO_OPENAI_API_MODEL,
    AUDIO_OPENAI_API_VOICE,
    AUDIO_ALLTALK_API_BASE_URL,
    AUDIO_ALLTALK_API_MODEL,
    AUDIO_ALLTALK_API_VOICE,
    AUDIO_ALLTALK_API_DEEPSPEED,
    AUDIO_ALLTALK_API_LOW_VRAM,
    AUDIO_ALLTALK_API_USE_STREAMING,
    AUDIO_ALLTALK_API_USE_NARRATOR,
    AUDIO_ALLTALK_API_NARRATOR_VOICE,
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
app.state.config.OPENAI_API_BASE_URL = AUDIO_OPENAI_API_BASE_URL
app.state.config.OPENAI_API_KEY = AUDIO_OPENAI_API_KEY
app.state.config.OPENAI_API_MODEL = AUDIO_OPENAI_API_MODEL
app.state.config.OPENAI_API_VOICE = AUDIO_OPENAI_API_VOICE

# setting alltalk api config
app.state.config.ALLTALK_API_BASE_URL = AUDIO_ALLTALK_API_BASE_URL
app.state.config.ALLTALK_API_MODEL = AUDIO_ALLTALK_API_MODEL
app.state.config.ALLTALK_API_VOICE = AUDIO_ALLTALK_API_VOICE
app.state.config.ALLTALK_API_DEEPSPEED = AUDIO_ALLTALK_API_DEEPSPEED
app.state.config.ALLTALK_API_LOW_VRAM = AUDIO_ALLTALK_API_LOW_VRAM
app.state.config.ALLTALK_API_USE_STREAMING = AUDIO_ALLTALK_API_USE_STREAMING
app.state.config.ALLTALK_API_USE_NARRATOR = AUDIO_ALLTALK_API_USE_NARRATOR
app.state.config.ALLTALK_API_NARRATOR_VOICE = AUDIO_ALLTALK_API_NARRATOR_VOICE


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["AUDIO"])



SPEECH_CACHE_DIR = Path(CACHE_DIR).joinpath("./audio/speech/")
SPEECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_config():
    return app.state.config
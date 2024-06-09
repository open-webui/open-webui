from apps.audio.settings import get_config
from apps.audio.providers.alltalk.alltalkApi import AllTalkTTSAPI

config = get_config()
baseUrl = config.TTS_ALLTALK_API_BASE_URL

# Initialize AllTalk TTS API instance
tts = AllTalkTTSAPI(baseUrl)

def update_alltalk_base_url(base_url: str):
    tts.base_url = base_url

def get_alltalk_config():
    return {
        "status": True,
        "ALLTALK_API_BASE_URL": config.TTS_ALLTALK_API_BASE_URL,
        "ALLTALK_API_MODEL": config.TTS_ALLTALK_API_MODEL,
        "ALLTALK_API_VOICE": config.TTS_ALLTALK_API_VOICE,
        "ALLTALK_API_DEEPSPEED": config.TTS_ALLTALK_API_DEEPSPEED,
        "ALLTALK_API_LOW_VRAM": config.TTS_ALLTALK_API_LOW_VRAM,
        "ALLTALK_API_USE_STREAMING": config.TTS_ALLTALK_API_USE_STREAMING,
        "ALLTALK_API_USE_NARRATOR": config.TTS_ALLTALK_API_USE_NARRATOR,
        "ALLTALK_API_NARRATOR_VOICE": config.TTS_ALLTALK_API_NARRATOR_VOICE
    }
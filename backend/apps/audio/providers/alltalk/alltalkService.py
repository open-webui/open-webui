from apps.audio.settings import get_config
from apps.audio.providers.alltalk.alltalkApi import AllTalkTTSAPI

config = get_config()
baseUrl = config.ALLTALK_API_BASE_URL

# Initialize AllTalk TTS API instance
tts = AllTalkTTSAPI(baseUrl)

def update_alltalk_base_url(base_url: str):
    tts.base_url = base_url

def get_alltalk_config():
    return {
        "status": True,
        "ALLTALK_API_BASE_URL": config.ALLTALK_API_BASE_URL,
        "ALLTALK_API_MODEL": config.ALLTALK_API_MODEL,
        "ALLTALK_API_VOICE": config.ALLTALK_API_VOICE,
        "ALLTALK_API_DEEPSPEED": config.ALLTALK_API_DEEPSPEED,
        "ALLTALK_API_LOW_VRAM": config.ALLTALK_API_LOW_VRAM
    }
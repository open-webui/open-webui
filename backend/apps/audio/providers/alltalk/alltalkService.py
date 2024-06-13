from apps.audio.settings import get_config
from apps.audio.providers.alltalk.alltalkApi import AllTalkTTSAPI
from apps.audio.providers.alltalk.alltalkModel import AllTalkConfigForm

config = get_config()
baseUrl = config.TTS_ALLTALK_API_BASE_URL

# Initialize AllTalk TTS API instance
tts = AllTalkTTSAPI(baseUrl)

def update_alltalk_tts_base_url(base_url: str):
    tts.base_url = base_url

def get_alltalk_tts_config() -> AllTalkConfigForm:
    return {
        "url": config.TTS_ALLTALK_API_BASE_URL,
        "model": config.TTS_ALLTALK_API_MODEL,
        "speaker": config.TTS_ALLTALK_API_VOICE,
        "deepspeed": config.TTS_ALLTALK_API_DEEPSPEED,
        "lowVram": config.TTS_ALLTALK_API_LOW_VRAM,
        "useStreaming": config.TTS_ALLTALK_API_USE_STREAMING,
        "useNarrator": config.TTS_ALLTALK_API_USE_NARRATOR,
        "narratorVoice": config.TTS_ALLTALK_API_NARRATOR_VOICE
    }
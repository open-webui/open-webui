from apps.audio.settings import get_config
from apps.audio.providers.alltalk.alltalkModel import AllTalkConfigForm

config = get_config()

def get_alltalk_config() -> AllTalkConfigForm:
    return {
        "status": True,
        "ALLTALK_API_BASE_URL": config.ALLTALK_API_BASE_URL,
        "ALLTALK_API_MODEL": config.ALLTALK_API_MODEL,
        "ALLTALK_API_VOICE": config.ALLTALK_API_VOICE,
    }





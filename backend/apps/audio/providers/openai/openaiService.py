from apps.audio.settings import get_config

config = get_config()

def get_openai_config():
    return {
        "status": True,
        "OPENAI_API_BASE_URL": config.OPENAI_API_BASE_URL,
        "OPENAI_API_KEY": config.OPENAI_API_KEY,
        "OPENAI_API_MODEL": config.OPENAI_API_MODEL,
        "OPENAI_API_VOICE": config.OPENAI_API_VOICE
    }
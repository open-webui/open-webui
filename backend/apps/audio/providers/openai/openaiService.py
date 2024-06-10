from apps.audio.settings import get_config
from apps.audio.providers.openai.openaiModel import OpenAIConfigUpdateForm

config = get_config()

def get_openai_tts_config() -> OpenAIConfigUpdateForm:
    return {
        "OPENAI_API_BASE_URL": config.TTS_OPENAI_API_BASE_URL,
        "OPENAI_API_KEY": config.TTS_OPENAI_API_KEY,
    }

def get_openai_stt_config() -> OpenAIConfigUpdateForm:
    return {
        "OPENAI_API_BASE_URL": config.STT_OPENAI_API_BASE_URL,
        "OPENAI_API_KEY": config.STT_OPENAI_API_KEY,
    }
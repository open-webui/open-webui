
from pydantic import BaseModel
from apps.audio.providers.alltalk.alltalkModel import AllTalkConfigForm
from apps.audio.providers.openai.openaiModel import OpenAIConfigUpdateForm


class TTSGeneralConfigForm(BaseModel):
    ENGINE: str
    MODEL: str
    VOICE: str

class STTGeneralConfigForm(BaseModel):
    ENGINE: str
    MODEL: str

class TTSConfigForm(BaseModel):
    openai : OpenAIConfigUpdateForm
    alltalk: AllTalkConfigForm
    general: TTSGeneralConfigForm

class STTConfigForm(BaseModel):
    openai : OpenAIConfigUpdateForm
    general: STTGeneralConfigForm

class AudioConfigUpdateForm(BaseModel):
    tts: TTSConfigForm
    stt: STTConfigForm

from pydantic import BaseModel

class AllTalkConfigForm(BaseModel):
    url: str
    model: str
    speaker: str
    deepspeed: bool
    lowVram: bool
    useStreaming: bool
    useNarrator: bool
    narratorVoice: str

class TTSGenerationPayload (BaseModel):
    text_input: str
    text_filtering: str
    character_voice_gen: str
    narrator_enabled: bool
    narrator_voice_gen: str
    text_not_inside: str
    language: str
    output_file_name: str
    output_file_timestamp: bool
    autoplay: bool
    autoplay_volume: float

class TTSStreamingPayload(BaseModel):
    text: str
    voice: str
    language: str
    output_file: str
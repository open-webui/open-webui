from fastapi import APIRouter, HTTPException, Depends, Body
from constants import ERROR_MESSAGES

from utils.utils import get_admin_user
from apps.audio.settings import get_config
from apps.audio.providers.alltalk.alltalkModel import AllTalkConfigForm
from apps.audio.providers.alltalk.alltalkService import get_alltalk_config, update_alltalk_base_url, tts

app = APIRouter(
     prefix="/alltalk",
     dependencies=[Depends(get_config)]
)

@app.get("/ready")
async def check_ready():
    response = tts.check_ready()
    return {"status": response}

@app.get("/voices")
async def get_voices():
    response = tts.get_voices()
    return response

@app.get("/currentsettings")
async def get_current_settings():
    response = tts.get_current_settings()
    print(response)
    return response

@app.post("/previewvoice")
async def preview_voice(voice: str = Body(..., embed=True)):
    print("preview_voice for "+ voice)
    response = tts.preview_voice(voice)
    return response

@app.post("/reload")
async def switch_model(tts_method: str):
    response = tts.switch_model(tts_method)
    return response

@app.post("/deepspeed")
async def switch_deepspeed(new_deepspeed_value: bool):
    response = tts.switch_deepspeed(new_deepspeed_value)
    return response

@app.post("/lowvramsetting")
async def switch_low_vram(new_low_vram_value: bool):
    response = tts.switch_low_vram(new_low_vram_value)
    return response

@app.post("/tts-generate")
async def generate_tts(
    text_input: str,
    character_voice_gen: str,
    narrator_enabled: bool,
    narrator_voice_gen: str,
    text_not_inside: str,
    language: str,
    output_file_name: str,
    output_file_timestamp: bool,
    autoplay: bool,
    autoplay_volume: float
):
    response = tts.generate_tts(
        text_input=text_input,
        character_voice_gen=character_voice_gen,
        narrator_enabled=narrator_enabled,
        narrator_voice_gen=narrator_voice_gen,
        text_not_inside=text_not_inside,
        language=language,
        output_file_name=output_file_name,
        output_file_timestamp=output_file_timestamp,
        autoplay=autoplay,
        autoplay_volume=autoplay_volume
    )
    return response

@app.post("/tts-generate-streaming")
async def generate_tts_streaming(
    text: str,
    voice: str,
    language: str,
    output_file: str
):
    streaming_url = tts.generate_tts_streaming(text, voice, language, output_file)
    return {"streaming_url": streaming_url}


@app.post("/config/update")
async def update_provider_config(
    form_data: AllTalkConfigForm, user=Depends(get_admin_user), config=Depends(get_config)
):
    if form_data.url == "":
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.API_URL_NOT_FOUND)

    update_alltalk_base_url(form_data.url)

    # Update the config to the TTS server if the values have changed
    if (config.ALLTALK_API_MODEL != form_data.model):
        await switch_model(form_data.model)

    if (config.ALLTALK_API_DEEPSPEED != form_data.deepspeed):
        await switch_deepspeed(form_data.deepspeed)

    if (config.ALLTALK_API_LOW_VRAM != form_data.low_vram):
        await switch_low_vram(form_data.low_vram)


    config.ALLTALK_API_BASE_URL = form_data.url
    config.ALLTALK_API_MODEL = form_data.model
    config.ALLTALK_API_VOICE = form_data.speaker
    config.ALLTALK_API_DEEPSPEED = form_data.deepspeed
    config.ALLTALK_API_LOW_VRAM = form_data.low_vram

    return get_alltalk_config()
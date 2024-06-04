import requests

from apps.audio.providers.alltalk.alltalkModel import TTSGenerationPayload, TTSStreamingPayload

class AllTalkTTSAPI:
    def __init__(self, base_url='http://127.0.0.1:7851/api'):
        self.base_url = base_url

    def check_ready(self):
        url = f"{self.base_url}/api/ready"
        response = requests.get(url)
        return response.text

    def get_voices(self):
        url = f"{self.base_url}/api/voices"
        response = requests.get(url)
        return response.json()

    def get_current_settings(self):
        url = f"{self.base_url}/api/currentsettings"
        response = requests.get(url)
        return response.json()

    def preview_voice(self, voice):
        url = f"{self.base_url}/api/previewvoice"
        data = {'voice': voice}
        response = requests.post(url, data=data)
        return response.json()

    def switch_model(self, tts_method):
        url = f"{self.base_url}/api/reload?tts_method={tts_method}"
        response = requests.post(url)
        return response

    def switch_deepspeed(self, new_deepspeed_value):
        url = f"{self.base_url}/api/deepspeed"
        params = {'new_deepspeed_value': new_deepspeed_value}
        response = requests.post(url, params=params)
        return response

    def switch_low_vram(self, new_low_vram_value):
        url = f"{self.base_url}/api/lowvramsetting"
        params = {'new_low_vram_value': new_low_vram_value}
        response = requests.post(url, params=params)
        return response

    def generate_tts(self, payload: TTSGenerationPayload):
        url = f"{self.base_url}/api/tts-generate"
        data = {
            'text_input': payload.text_input,
            'text_filtering': payload.text_filtering,
            'character_voice_gen': payload.character_voice_gen,
            'narrator_enabled': payload.narrator_enabled,
            'narrator_voice_gen': payload.narrator_voice_gen,
            'text_not_inside': payload.text_not_inside,
            'language': payload.language,
            'output_file_name': payload.output_file_name,
            'output_file_timestamp': payload.output_file_timestamp,
            'autoplay': payload.autoplay,
            'autoplay_volume': payload.autoplay_volume,
        }
        print(payload.text_input)
        response = requests.post(url, data=data)
        return response.json()

    def generate_tts_streaming(self, payload: TTSStreamingPayload):
        url = f"{self.base_url}/api/tts-generate-streaming"
        params = {
            'text': payload.text,
            'voice': payload.voice,
            'language': payload.language,
            'output_file': payload.output_file
        }
        response = requests.post(url, params=payload)
        return response.url

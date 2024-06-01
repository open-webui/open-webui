import requests

class AllTalkTTSAPI:
    def __init__(self, base_url='http://127.0.0.1:7851/api'):
        self.base_url = base_url
        print("final base_url: " + base_url)

    def check_ready(self):
        url = f"{self.base_url}/ready"
        response = requests.get(url)
        return response.text

    def get_voices(self):
        url = f"{self.base_url}/voices"
        response = requests.get(url)
        return response.json()

    def get_current_settings(self):
        url = f"{self.base_url}/currentsettings"
        response = requests.get(url)
        return response.json()

    def preview_voice(self, voice):
        url = f"{self.base_url}/previewvoice/"
        data = {'voice': voice}
        print("preview_voice for " + voice)
        response = requests.post(url, data=data)
        return response.json()

    def switch_model(self, tts_method):
        url = f"{self.base_url}/reload"
        params = {'tts_method': tts_method}
        response = requests.post(url, params=params)
        return response.json()

    def switch_deepspeed(self, new_deepspeed_value):
        url = f"{self.base_url}/deepspeed"
        params = {'new_deepspeed_value': new_deepspeed_value}
        response = requests.post(url, params=params)
        return response.json()

    def switch_low_vram(self, new_low_vram_value):
        url = f"{self.base_url}/lowvramsetting"
        params = {'new_low_vram_value': new_low_vram_value}
        response = requests.post(url, params=params)
        return response.json()

    def generate_tts(self, text_input, character_voice_gen, narrator_enabled, narrator_voice_gen,
                     text_not_inside, language, output_file_name, output_file_timestamp,
                     autoplay, autoplay_volume):
        url = f"{self.base_url}/tts-generate"
        data = {
            'text_input': text_input,
            'text_filtering': 'standard',
            'character_voice_gen': character_voice_gen,
            'narrator_enabled': narrator_enabled,
            'narrator_voice_gen': narrator_voice_gen,
            'text_not_inside': text_not_inside,
            'language': language,
            'output_file_name': output_file_name,
            'output_file_timestamp': output_file_timestamp,
            'autoplay': autoplay,
            'autoplay_volume': autoplay_volume,
        }
        response = requests.post(url, data=data)
        return response.json()

    def generate_tts_streaming(self, text, voice, language, output_file):
        url = f"{self.base_url}/tts-generate-streaming"
        params = {
            'text': text,
            'voice': voice,
            'language': language,
            'output_file': output_file
        }
        response = requests.post(url, params=params)
        return response.url

import { AUDIO_API_BASE_URL } from '$lib/constants';

export class Alltalk {
    isReady: boolean = false;
    provider: string = 'alltalk';
    baseUrl: string = '';
    voicesList: string[] = [];
    currentVoice: string = '';


    constructor(baseUrl: string = '', voicesList: string[] = []) {
        this.baseUrl = baseUrl;
        this.voicesList = voicesList;
    }

    async setup() {
        this.isReady = await this.getReady();
        await this.getVoices();
    }


    async getReady(): Promise<boolean> {
        const result = await fetch(`${this.baseUrl}/api/ready`, {
            method: 'GET'
        }).then((res) => res.text());

        return result === "Ready";
    }

    async getVoices(forceReload: boolean = false) {
        if (this.voicesList.length > 0 && !forceReload ) {
            return this.voicesList;
        }
        const res = await fetch(`${this.baseUrl}/api/voices`, {
            method: 'GET'
        }).then((res) => res.json());

        this.voicesList = res.voices;

        if (this.voicesList.length > 0 && !this.currentVoice) {
            this.currentVoice = this.voicesList[0];
        }

        return this.voicesList;
    }

    async currentSettings() {
        return await fetch(`${this.baseUrl}/api/currentsettings`, {
            method: 'GET'
        }).then((res) => res.json());
    }

    async previewVoice(voice: string) {
        const res = await this.getPreviewVoice(voice);
        if (res.status === 'generate-success') {
            const audio = new Audio(res.output_file_url);
            audio.play();
        }
    }

    async getPreviewVoice(voice: string) {
        voice = voice || this.currentVoice;

        return await fetch(`${AUDIO_API_BASE_URL}/${this.provider}/previewvoice`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ voice: voice })
        }).then((res) => res.json());

    }

    async reload(tts_method: string) {
        return await fetch(`${this.baseUrl}/api/reload?tts_method=${tts_method}`, {
            method: 'POST',
            body: JSON.stringify({ tts_method: tts_method })
        }).then((res) => res.json());
    }

    async deepspeed(new_deepspeed_value: boolean) {
        return await fetch(`${this.baseUrl}/api/deepspeed?new_deepspeed_value=${new_deepspeed_value}`, {
            method: 'POST'
        }).then((res) => res.json());
    }

    async lowVramSetting(new_low_vram_value: boolean) {
        return await fetch(`${this.baseUrl}/api/lowvramsetting?new_low_vram_value=${new_low_vram_value}`, {
            method: 'POST'
        }).then((res) => res.json());
    }

    async ttsGenerate(payload: {
        text_input: string;
        text_filtering: string;
        character_voice_gen: string;
        narrator_enabled: boolean;
        narrator_voice_gen: string;
        text_not_inside: string;
        language: string;
        output_file_name: string;
        output_file_timestamp: boolean;
        autoplay: boolean;
        autoplay_volume: number;
    }) {
        return await fetch(`${this.baseUrl}/api/tts-generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams(payload).toString()
        }).then((res) => res.json());
    }

    async ttsGenerateStreaming(payload: {
        text: string;
        voice: string;
        language: string;
        output_file: string;
    }) {
        const { text, voice, language, output_file } = payload;
        const encodedText = encodeURIComponent(text);
        const streamingUrl = `${this.baseUrl}/api/tts-generate-streaming?text=${encodedText}&voice=${voice}&language=${language}&output_file=${output_file}`;
        return new Audio(streamingUrl).play();
    }
}
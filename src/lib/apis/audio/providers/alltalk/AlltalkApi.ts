import { AUDIO_API_BASE_URL } from '$lib/constants';
import type { CurrentSettings, PreviewVoice, VoicesList } from './alltalkApiModel';

export class AlltalkApi {
    provider: string = 'alltalk';
    constructor() { }

    async voices(): Promise<VoicesList> {
        return await fetch(`${AUDIO_API_BASE_URL}/${this.provider}/voices`, {
            method: 'GET'
        }).then((res) => res.json());
    }

    async currentSettings(): Promise<CurrentSettings> {
        return await fetch(`${AUDIO_API_BASE_URL}/${this.provider}/currentsettings`, {
            method: 'GET'
        }).then((res) => res.json());
    }

    async previewVoice(voice: string): Promise<PreviewVoice> {
        return await fetch(`${AUDIO_API_BASE_URL}/${this.provider}/previewvoice`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ voice: voice })
        }).then((res) => res.json());
    }

    async reload(tts_method: string) {
        return await fetch(`${AUDIO_API_BASE_URL}/${this.provider}/reload?tts_method=${tts_method}`, {
            method: 'POST',
            body: JSON.stringify({ tts_method: tts_method })
        }).then((res) => res.json());
    }

    async deepspeed(new_deepspeed_value: boolean) {
        return await fetch(`${AUDIO_API_BASE_URL}/${this.provider}/deepspeed?new_deepspeed_value=${new_deepspeed_value}`, {
            method: 'POST'
        }).then((res) => res.json());
    }

    async lowVramSetting(new_low_vram_value: boolean) {
        return await fetch(`${AUDIO_API_BASE_URL}/${this.provider}/lowvramsetting?new_low_vram_value=${new_low_vram_value}`, {
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
        return await fetch(`${AUDIO_API_BASE_URL}/${this.provider}/tts-generate`, {
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
        const streamingUrl = `${AUDIO_API_BASE_URL}/${this.provider}/tts-generate-streaming?text=${encodedText}&voice=${voice}&language=${language}&output_file=${output_file}`;
        return new Audio(streamingUrl).play();
    }
}
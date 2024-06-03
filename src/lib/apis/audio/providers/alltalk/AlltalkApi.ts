import { AUDIO_API_BASE_URL } from '$lib/constants';
import type { CurrentSettings, PreviewVoice, TTSGenerationPayload, TTSGenerationStreaming, VoicesList } from './alltalkApiModel';

export class AlltalkApi {
    provider: string = 'alltalk';
    constructor() { }

    async ready() {
        return await fetch(`${AUDIO_API_BASE_URL}/${this.provider}/ready`, {
            method: 'GET'
        })
        .then((res) => res.json())
        .catch((err) => {
            console.error(err);
            return null;
        });
    }

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

    async ttsGenerate(payload: TTSGenerationPayload) {
        return await fetch(`${AUDIO_API_BASE_URL}/${this.provider}/tts-generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then((res) => res.json());
    }

    async ttsGenerateStreaming(payload: TTSGenerationStreaming) {
        return await fetch(`${AUDIO_API_BASE_URL}/${this.provider}/tts-generate-streaming`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then((res) => res.json());
    }
}
import { AlltalkApi } from './AlltalkApi';
import type { CurrentSettings } from './alltalkApiModel';

interface PreviewVoicePayload {
    lastVoice: string; // last voice used for previewing.
    lastUrl: string; // last URL recieved from previewing.
}

export class Alltalk {
    isReady: boolean = false;
    baseUrl: string = '';
    voicesList: string[] = [];
    modelList: string[] = [];
    currentVoice: string = '';
    currentModel: string = '';
    currentsSettings!: CurrentSettings;
    lastPreviewVoicePayload: PreviewVoicePayload = { lastVoice: '', lastUrl: '' };
    api: AlltalkApi;
    useDeepSpeed: boolean = false;
    useLowVRAM: boolean = false;

    constructor(baseUrl: string = '', voicesList: string[] = []) {
        this.baseUrl = baseUrl;
        this.voicesList = voicesList;
        this.api = new AlltalkApi();
    }

    async setup() {
        console.log("Setting up Alltalk");
        console.log("baseUrl: ", this.baseUrl);
        if (!this.baseUrl) {
            return;
        }
        this.voicesList = await this.getVoices();
        if (this.voicesList.length > 0 && !this.currentVoice) {
            this.currentVoice = this.voicesList[0];
        }
        this.currentsSettings = await this.getCurrentSettings();
        this.modelList = await this.getModels();
    }

    async getVoices(): Promise<string[]> {
        let result = null;
        const res = await this.api.voices();
        result = res.voices || [];
        return result;
    }

    async getModels(): Promise<string[]>{
        let result = null;
        if (!this.currentsSettings) {
            await this.getCurrentSettings();
        }
        result = this.currentsSettings.models_available.map((model) => model.model_name);
        console.log("modelList: ", result);

        return result;
    }

    async getCurrentSettings(): Promise<CurrentSettings> {
        console.log("getCurrentSettings !!!!");
        const res = await this.api.currentSettings();
        this.currentModel = res.current_model_loaded;
        this.useDeepSpeed = res.deepspeed_status;
        this.useLowVRAM = res.low_vram_status;
        return res;
    }

    async getPreviewVoice(voice: string, forceReload: boolean = false) {
        voice = voice || this.currentVoice;

        let result = null;
        if (this.lastPreviewVoicePayload.lastVoice === voice && !forceReload) {
            result = this.lastPreviewVoicePayload.lastUrl;
        }
        const res = await this.api.previewVoice(voice);
        if(res && res.status === 'generate-success'){
            result = res.output_file_url;

            this.lastPreviewVoicePayload = {
                lastVoice: voice,
                lastUrl: result
            };

            const audio = new Audio(result);
            audio.play();
        }
        return result;
    }


}
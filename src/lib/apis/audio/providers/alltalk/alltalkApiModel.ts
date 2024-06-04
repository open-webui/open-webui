export type Ready = {
    status: string;
}

export type VoicesList = {
    voices: string[];
}

export type CurrentSettings = {
    models_available: { name: string, model_name: string }[]; // listing the currently available models.
    current_model_loaded: string; // what model is currently loaded into VRAM.
    deepspeed_available: boolean; // was DeepSpeed detected on startup and available to be activated.
    deepspeed_status: boolean; // If DeepSpeed was detected, is it currently activated.
    low_vram_status: boolean; // Is Low VRAM currently enabled.
    finetuned_model: boolean; // Was a fine tuned model detected. (XTTSv2 FT).
}

export type PreviewVoice = {
    status: string;
    output_file_path: string;
    output_file_url: string;
}

export type SwitchingModel = {
    status: string;
}

export type SwitchDeepSpeed = {
    status: string;
}

export type SwitchingLowVRAM = {
    status: string;
}

export type TTSGeneration = {
    status: string;
    output_file_path: string;
    output_file_url: string;
    output_cache_url: string;
}

export class TTSGenerationPayload {
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

    constructor(
        text_input: string,
        text_filtering: string = "standard",
        character_voice_gen: string,
        narrator_enabled: boolean = false,
        narrator_voice_gen: string,
        text_not_inside: string = "character",
        language: string = "en",
        output_file_name: string = "output",
        output_file_timestamp: boolean = true,
        autoplay: boolean = false,
        autoplay_volume: number = 0.1
    ) {
        this.text_input = text_input;
        this.text_filtering = text_filtering;
        this.character_voice_gen = character_voice_gen;
        this.narrator_enabled = narrator_enabled;
        this.narrator_voice_gen = narrator_voice_gen;
        this.text_not_inside = text_not_inside;
        this.language = language;
        this.output_file_name = output_file_name;
        this.output_file_timestamp = output_file_timestamp;
        this.autoplay = autoplay;
        this.autoplay_volume = autoplay_volume;
    }
}

export class TTSGenerationStreaming {
    text: string;
    voice: string;
    language: string = "en";
    output_file: string = "stream_output.wav";

    constructor(text: string, voice: string) {
        this.text = text;
        this.voice = voice;
    }
}
export interface Ready {
    status: string;
}

export interface VoicesList {
    voices: string[];
}

export interface CurrentSettings {
    models_available: { name: string, model_name: string }[]; // listing the currently available models.
    current_model_loaded: string; // what model is currently loaded into VRAM.
    deepspeed_available: boolean; // was DeepSpeed detected on startup and available to be activated.
    deepspeed_status: boolean; // If DeepSpeed was detected, is it currently activated.
    low_vram_status: boolean; // Is Low VRAM currently enabled.
    finetuned_model: boolean; // Was a fine tuned model detected. (XTTSv2 FT).
}

export interface PreviewVoice {
    status: string;
    output_file_path: string;
    output_file_url: string;
}

export interface SwitchingModel {
    status: string;
}

export interface SwitchDeepSpeed {
    status: string;
}

export interface SwitchingLowVRAM {
    status: string;
}

export interface TTSGeneration {
    status: string;
    output_file_path: string;
    output_file_url: string;
    output_cache_url: string;
}

export interface TTSGenerationStreaming {
    text: string;
    voice: string;
    language: string;
    output_file: string;
}
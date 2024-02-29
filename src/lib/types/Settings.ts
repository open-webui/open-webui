export type Settings = {
	audio?: AudioSettings;
	conversationMode?: boolean;
	fullScreenMode?: boolean;
	keepAlive?: string | number;
	models?: string[];
	notificationEnabled?: boolean;
	options?: Options;
	requestFormat?: string;
	responseAutoPlayback?: boolean;
	showUsername?: boolean;
	speechAutoSend?: boolean;
	system?: string;
};

export type AudioSettings = {
	speaker?: string;
	STTEngine?: string;
	TTSEngine?: TTSEngine;
};

export type Options = {
	mirostat?: string;
	mirostat_eta?: string;
	mirostat_tau?: string;
	num_ctx?: string;
	num_predict?: string;
	repeat_last_n?: string;
	repeat_penalty?: string;
	seed?: number;
	stop?: string[];
	temperature?: string;
	tfs_z?: string;
	top_k?: string;
	top_p?: string;
};


export type TTSEngine = keyof typeof TTSEngines | '';
export const TTSEngines = {
	openai: 'OpenAI'
};

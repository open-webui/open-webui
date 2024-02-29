export type Settings = {
	audio?: AudioSettings;
	conversationMode?: boolean;
	saveChatHistory?: boolean;
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
	titleAutoGenerate?: boolean;
	responseAutoCopy?: boolean;
	titleAutoGenerateModel?: string;
	titleGenerationPrompt?: string;
};

export type AudioSettings = {
	speaker?: string;
	STTEngine?: string;
	TTSEngine?: TTSEngine;
};

export type Options = {
	mirostat?: number;
	mirostat_eta?: number;
	mirostat_tau?: number;
	num_ctx?: number;
	num_predict?: number;
	repeat_last_n?: number;
	repeat_penalty?: number;
	seed?: number;
	stop?: string | string[];
	temperature?: number;
	tfs_z?: number;
	top_k?: number;
	top_p?: number;
};

export type TTSEngine = keyof typeof TTSEngines | '';
export const TTSEngines = {
	openai: 'OpenAI'
};

export type Voice = keyof typeof Voices;
export const Voices = {
	alloy: 'Alloy',
	echo: 'Echo',
	fable: 'Fable',
	onyx: 'Onyx',
	nova: 'Nova',
	shimmer: 'Shimmer'
};

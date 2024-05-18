import { APP_NAME } from '$lib/constants';
import { type Writable, writable } from 'svelte/store';

// Backend
export const WEBUI_NAME = writable(APP_NAME);
export const config: Writable<Config | undefined> = writable(undefined);
export const user: Writable<SessionUser | undefined> = writable(undefined);

// Frontend
export const MODEL_DOWNLOAD_POOL = writable({});

export const mobile = writable(false);

export const theme = writable('system');
export const chatId = writable('');

export const chats = writable([]);
export const tags = writable([]);
export const models: Writable<Model[]> = writable([]);

export const modelfiles = writable([]);
export const prompts: Writable<Prompt[]> = writable([]);
export const documents = writable([
	{
		collection_name: 'collection_name',
		filename: 'filename',
		name: 'name',
		title: 'title'
	},
	{
		collection_name: 'collection_name1',
		filename: 'filename1',
		name: 'name1',
		title: 'title1'
	}
]);

export const settings: Writable<Settings> = writable({});

export const showSidebar = writable(false);
export const showSettings = writable(false);
export const showArchivedChats = writable(false);
export const showChangelog = writable(false);

type Model = OpenAIModel | OllamaModel;

type OpenAIModel = {
	id: string;
	name: string;
	external: boolean;
	source?: string;
};

type OllamaModel = {
	id: string;
	name: string;

	// Ollama specific fields
	details: OllamaModelDetails;
	size: number;
	description: string;
	model: string;
	modified_at: string;
	digest: string;
};

type OllamaModelDetails = {
	parent_model: string;
	format: string;
	family: string;
	families: string[] | null;
	parameter_size: string;
	quantization_level: string;
};

type Settings = {
	models?: string[];
	conversationMode?: boolean;
	speechAutoSend?: boolean;
	responseAutoPlayback?: boolean;
	audio?: AudioSettings;
	showUsername?: boolean;
	saveChatHistory?: boolean;
	notificationEnabled?: boolean;
	title?: TitleSettings;
	splitLargeDeltas?: boolean;
	chatDirection: 'LTR' | 'RTL';

	system?: string;
	requestFormat?: string;
	keepAlive?: string;
	seed?: number;
	temperature?: string;
	repeat_penalty?: string;
	top_k?: string;
	top_p?: string;
	num_ctx?: string;
	options?: ModelOptions;
};

type ModelOptions = {
	stop?: boolean;
};

type AudioSettings = {
	STTEngine?: string;
	TTSEngine?: string;
	speaker?: string;
	model?: string;
};

type TitleSettings = {
	auto?: boolean;
	model?: string;
	modelExternal?: string;
	prompt?: string;
};

type Prompt = {
	command: string;
	user_id: string;
	title: string;
	content: string;
	timestamp: number;
};

type Config = {
	status?: boolean;
	name?: string;
	version?: string;
	default_locale?: string;
	images?: boolean;
	default_models?: string[];
	default_prompt_suggestions?: PromptSuggestion[];
	trusted_header_auth?: boolean;
};

type PromptSuggestion = {
	content: string;
	title: [string, string];
};

type SessionUser = {
	id: string;
	email: string;
	name: string;
	role: string;
	profile_image_url: string;
};

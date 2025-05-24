import { APP_NAME } from '$lib/constants';
import { type Writable, writable, derived } from 'svelte/store';
import type { ModelConfig } from '$lib/apis';
import type { Banner } from '$lib/types';
import type { LocalMcpoToolConfig, Tool, ToolServerConnection } from '$lib/types/tools';
import type { Socket } from 'socket.io-client';

import emojiShortCodes from '$lib/emoji-shortcodes.json';

// Backend
export const WEBUI_NAME = writable(APP_NAME);
export const config: Writable<Config | undefined> = writable(undefined);
export const user: Writable<SessionUser | undefined> = writable(undefined);

// Electron App
export const isApp = writable(false);
export const appInfo = writable(null);
export const appData = writable(null);

// Frontend
export const MODEL_DOWNLOAD_POOL = writable({});

export const mobile = writable(false);

export const socket: Writable<null | Socket> = writable(null);
export const activeUserIds: Writable<null | string[]> = writable(null);
export const USAGE_POOL: Writable<null | string[]> = writable(null);

export const theme = writable('system');

export const shortCodesToEmojis = writable(
	Object.entries(emojiShortCodes).reduce((acc: Record<string, string>, [key, value]) => {
		if (typeof value === 'string') {
			acc[value] = key;
		} else {
			for (const v of value) {
				acc[v] = key;
			}
		}

		return acc;
	}, {} as Record<string, string>)
);

export const TTSWorker = writable(null);

export const chatId = writable('');
export const chatTitle = writable('');

export const channels = writable([]);
export const chats = writable(null);
export const pinnedChats = writable([]);
export const tags = writable([]);

export const models: Writable<Model[]> = writable([]);

export const prompts: Writable<null | Prompt[]> = writable(null);
export const knowledge: Writable<null | Document[]> = writable(null);
export const tools: Writable<Tool[] | null> = writable(null); // Explicitly type as Tool[] or null
export const functions = writable(null);

export const toolServers: Writable<ToolServerConnection[]> = writable([]);
export const localMcpoTools: Writable<LocalMcpoToolConfig[]> = writable([]);

// Store for passing local tool execution results from layout to Chat.svelte
export const localToolResultStore = writable<null | {
	toolId: string;
	chatId: string;
	assistantMessageId: string;
	result: { success: boolean; data?: any; error?: string };
}>(null);

// Derived store to combine all available tools
export const allAvailableTools = derived(
	[tools, toolServers, localMcpoTools],
	([$tools, $toolServers, $localMcpoTools]) => {
		console.log('[allAvailableTools] Deriving: $localMcpoTools count:', $localMcpoTools.length, '$tools count:', ($tools || []).length, '$toolServers count:', $toolServers.length);
		const combinedTools: Tool[] = [];

		// Add tools from the 'tools' store (internal Python tools, etc.)
		if ($tools && Array.isArray($tools)) {
			// Assuming $tools is an array of Tool-like objects
			// We might need to adapt them to the Tool interface if they are not already
			($tools as any[]).forEach((tool) => {
				combinedTools.push({
					id: tool.id, // Ensure these properties exist
					name: tool.name,
					description: tool.description,
					spec: tool.spec,
					type: tool.type || 'python_internal', // Assuming a default or existing type
					enabled: tool.enabled ?? true, // Default to enabled if not specified
					metadata: tool.metadata
				});
			});
		}

		// Add tools from 'toolServers'
		$toolServers.forEach((serverConnection) => {
			if (serverConnection.tools && serverConnection.enabled) {
				serverConnection.tools.forEach((tool) => {
					combinedTools.push({
						...tool,
						id: tool.id || `${serverConnection.id}-${tool.name}`, // Ensure unique ID
						type: tool.type || 'openapi', // Assume openapi if not specified
						enabled: tool.enabled ?? true,
						metadata: { ...tool.metadata, serverName: serverConnection.name, serverUrl: serverConnection.url }
					});
				});
			}
		});

		// Add tools from 'localMcpoTools'
		$localMcpoTools.forEach((localTool) => {
			combinedTools.push({
				id: localTool.id,
				name: localTool.name,
				description: localTool.spec.info.description,
				spec: localTool.spec,
				type: 'local_mcpo',
				enabled: localTool.enabled ?? true, // Default to enabled
				metadata: { baseUrl: localTool.baseUrl, openapiPath: localTool.openapiPath }
			});
		});

		// Deduplicate tools by id, preferring local_mcpo if conflicts arise, then others.
		const uniqueTools = new Map<string, Tool>();
		combinedTools.forEach(tool => {
			if (!uniqueTools.has(tool.id) || tool.type === 'local_mcpo') {
				uniqueTools.set(tool.id, tool);
			}
		});
		
		const finalTools = Array.from(uniqueTools.values());
		console.log('[allAvailableTools] Derived tools count:', finalTools.length, 'Enabled count:', finalTools.filter(t => t.enabled).length);
		// console.log('[allAvailableTools] Derived tools content:', JSON.stringify(finalTools.map(t => ({id: t.id, name: t.name, type: t.type, enabled: t.enabled})), null, 2));
		return finalTools;
	}
);

export const banners: Writable<Banner[]> = writable([]);

export const settings: Writable<Settings> = writable({
	chatDirection: 'auto' // Default value for the required property
	// Other properties will be undefined by default if optional, or can be added here with defaults
});

export const showSidebar = writable(false);
export const showSettings = writable(false);
export const showArchivedChats = writable(false);
export const showChangelog = writable(false);

export const showControls = writable(false);
export const showOverview = writable(false);
export const showArtifacts = writable(false);
export const showCallOverlay = writable(false);

export const temporaryChatEnabled = writable(false);
export const scrollPaginationEnabled = writable(false);
export const currentChatPage = writable(1);

export const isLastActiveTab = writable(true);
export const playingNotificationSound = writable(false);

export type Model = OpenAIModel | OllamaModel;

type BaseModel = {
	id: string;
	name: string;
	info?: ModelConfig;
	owned_by: 'ollama' | 'openai' | 'arena';
};

export interface OpenAIModel extends BaseModel {
	owned_by: 'openai';
	external: boolean;
	source?: string;
}

export interface OllamaModel extends BaseModel {
	owned_by: 'ollama';
	details: OllamaModelDetails;
	size: number;
	description: string;
	model: string;
	modified_at: string;
	digest: string;
	ollama?: {
		name?: string;
		model?: string;
		modified_at: string;
		size?: number;
		digest?: string;
		details?: {
			parent_model?: string;
			format?: string;
			family?: string;
			families?: string[];
			parameter_size?: string;
			quantization_level?: string;
		};
		urls?: number[];
	};
}

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
	notificationEnabled?: boolean;
	title?: TitleSettings;
	splitLargeDeltas?: boolean;
	chatDirection: 'LTR' | 'RTL' | 'auto';
	ctrlEnterToSend?: boolean;
	directConnections?: any; // Added for +layout.svelte
	toolServers?: any[]; // Added for +layout.svelte
	showChangelog?: boolean; // Added for +layout.svelte
	version?: string; // Added for +layout.svelte
	showUpdateToast?: boolean; // Added for +layout.svelte

	system?: string;
	requestFormat?: string;
	keepAlive?: string;
	seed?: number;
	temperature?: string;
	repeat_penalty?: string;
	top_k?: string;
	top_p?: string;
	num_ctx?: string;
	num_batch?: string;
	num_keep?: string;
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
	nonLocalVoices?: boolean;
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

type Document = {
	collection_name: string;
	filename: string;
	name: string;
	title: string;
};

type Config = {
	status: boolean;
	name: string;
	version: string;
	default_locale: string;
	default_models: string;
	default_prompt_suggestions: PromptSuggestion[];
	features: {
		auth: boolean;
		auth_trusted_header: boolean;
		enable_api_key: boolean;
		enable_signup: boolean;
		enable_login_form: boolean;
		enable_web_search?: boolean;
		enable_google_drive_integration: boolean;
		enable_onedrive_integration: boolean;
		enable_image_generation: boolean;
		enable_admin_export: boolean;
		enable_admin_chat_access: boolean;
		enable_community_sharing: boolean;
		enable_autocomplete_generation: boolean;
		enable_direct_connections?: boolean; // Added for +layout.svelte
	};
	oauth: {
		providers: {
			[key: string]: string;
		};
	};
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
	permissions?: any; // Added for +layout.svelte
};

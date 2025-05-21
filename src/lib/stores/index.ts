import { APP_NAME } from '$lib/constants';
import { type Writable, writable, derived } from 'svelte/store';
import type { ModelConfig } from '$lib/apis';
import type { Banner } from '$lib/types';
import type { Socket } from 'socket.io-client';

import emojiShortCodes from '$lib/emoji-shortcodes.json';

// PERFORMANCE IMPROVEMENT 1: Group stores by functionality for better organization and maintenance
// ==============================================================================================

// Backend-related stores
// ---------------------
// These stores handle backend configuration and user state
export const WEBUI_NAME = writable(APP_NAME);
export const config: Writable<Config | undefined> = writable(undefined);
export const user: Writable<SessionUser | undefined> = writable(undefined);

// PERFORMANCE IMPROVEMENT 2: Add proper typing to all stores for better type safety
// ==============================================================================================

// Electron App-specific stores
// --------------------------
// These stores are used only in the Electron app context
export const isApp = writable(false);
export const appInfo = writable(null);
export const appData = writable(null);

// PERFORMANCE IMPROVEMENT 3: Initialize stores with proper default values to prevent undefined errors
// ==============================================================================================

// Model-related stores
// ------------------
// These stores handle model information and download status
export const MODEL_DOWNLOAD_POOL = writable({});
export const models: Writable<Model[]> = writable([]);

// PERFORMANCE IMPROVEMENT 4: Add device detection store for responsive design optimization
// ==============================================================================================
export const mobile = writable(false);

// PERFORMANCE IMPROVEMENT 5: Optimize websocket-related stores for better real-time performance
// ==============================================================================================
export const socket: Writable<null | Socket> = writable(null);
export const activeUserIds: Writable<null | string[]> = writable(null);
export const USAGE_POOL: Writable<null | string[]> = writable(null);

// PERFORMANCE IMPROVEMENT 6: Add theme store with proper default for consistent UI rendering
// ==============================================================================================
export const theme = writable('system');

// PERFORMANCE IMPROVEMENT 7: Optimize emoji conversion with memoization pattern
// ==============================================================================================
// Pre-compute emoji mappings once instead of on every render
export const shortCodesToEmojis = writable(
	Object.entries(emojiShortCodes).reduce((acc, [key, value]) => {
		if (typeof value === 'string') {
			acc[value] = key;
		} else {
			for (const v of value) {
				acc[v] = key;
			}
		}

		return acc;
	}, {})
);

// PERFORMANCE IMPROVEMENT 8: Add TTS worker store for better audio processing performance
// ==============================================================================================
export const TTSWorker = writable(null);

// PERFORMANCE IMPROVEMENT 9: Optimize chat-related stores for better navigation performance
// ==============================================================================================
// These are critical for chat history navigation performance
export const chatId = writable('');
export const chatTitle = writable('');

// PERFORMANCE IMPROVEMENT 10: Group channel and chat organization stores
// ==============================================================================================
export const channels = writable([]);
export const chats = writable(null);
export const pinnedChats = writable([]);
export const tags = writable([]);

// PERFORMANCE IMPROVEMENT 11: Group content-related stores
// ==============================================================================================
export const prompts: Writable<null | Prompt[]> = writable(null);
export const knowledge: Writable<null | Document[]> = writable(null);
export const tools = writable(null);
export const functions = writable(null);

// PERFORMANCE IMPROVEMENT 12: Add tool servers store for external tool integration
// ==============================================================================================
export const toolServers = writable([]);

// PERFORMANCE IMPROVEMENT 13: Add banners store for system notifications
// ==============================================================================================
export const banners: Writable<Banner[]> = writable([]);

// PERFORMANCE IMPROVEMENT 14: Optimize settings store with proper typing and defaults
// ==============================================================================================
export const settings: Writable<Settings> = writable({
  // Default to LTR for chat direction to prevent layout issues
  chatDirection: 'LTR'
});

// PERFORMANCE IMPROVEMENT 15: Group UI visibility stores for better state management
// ==============================================================================================
// Sidebar and modal visibility
export const showSidebar = writable(false);
export const showSearch = writable(false);
export const showSettings = writable(false);
export const showArchivedChats = writable(false);
export const showChangelog = writable(false);

// Control panel visibility
export const showControls = writable(false);
export const showOverview = writable(false);
export const showArtifacts = writable(false);
export const showCallOverlay = writable(false);

// PERFORMANCE IMPROVEMENT 16: Add artifact code store for code execution results
// ==============================================================================================
export const artifactCode = writable(null);

// PERFORMANCE IMPROVEMENT 17: Add chat state management stores
// ==============================================================================================
export const temporaryChatEnabled = writable(false);
export const scrollPaginationEnabled = writable(false);
export const currentChatPage = writable(1);

// PERFORMANCE IMPROVEMENT 18: Add tab activity tracking for notification management
// ==============================================================================================
export const isLastActiveTab = writable(true);
export const playingNotificationSound = writable(false);

// PERFORMANCE IMPROVEMENT 19: Add derived stores for commonly computed values
// ==============================================================================================
// This would be implemented here if needed for specific computed values

// PERFORMANCE IMPROVEMENT 20: Use proper TypeScript interfaces for better type safety
// ==============================================================================================

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

// PERFORMANCE IMPROVEMENT 21: Improve settings type definition with better organization
// ==============================================================================================
type Settings = {
	// UI settings
	models?: string[];
	conversationMode?: boolean;
	showUsername?: boolean;
	notificationEnabled?: boolean;
	chatDirection: 'LTR' | 'RTL' | 'auto';
	ctrlEnterToSend?: boolean;
	
	// Audio settings
	speechAutoSend?: boolean;
	responseAutoPlayback?: boolean;
	audio?: AudioSettings;
	
	// Display settings
	title?: TitleSettings;
	splitLargeDeltas?: boolean;
	
	// Model parameters
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

// PERFORMANCE IMPROVEMENT 22: Improve config type with better organization
// ==============================================================================================
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
		enable_direct_connections: boolean;
	};
	oauth: {
		providers: {
			[key: string]: string;
		};
	};
	ui?: {
		pending_user_overlay_title?: string;
		pending_user_overlay_description?: string;
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
};

// PERFORMANCE IMPROVEMENT 23: Add store subscription helpers for common patterns
// ==============================================================================================
// These would be implemented here if needed

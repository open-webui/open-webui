import { APP_NAME } from '$lib/constants';
import { type Writable, writable, derived } from 'svelte/store';
import type { ModelConfig } from '$lib/apis';
import type { Banner } from '$lib/types';
import type { Socket } from 'socket.io-client';
import type { AudioQueue } from '$lib/utils/audio';
import type { TerminalServer } from '$lib/apis/terminal';

import emojiShortCodes from '$lib/emoji-shortcodes.json';

// What is held here is the only truth the house knows.
// When it changes, let every room hear at once.
// Backend
export const WEBUI_NAME = writable(APP_NAME);

export const WEBUI_VERSION = writable<string | null>(null);
export const WEBUI_DEPLOYMENT_ID = writable<string | null>(null);

export const config: Writable<Config | undefined> = writable(undefined);
export const user: Writable<SessionUser | undefined> = writable(undefined);

// Derived stores for convenient computed state
export const isAuthenticated = derived(user, ($user) => $user !== undefined);
export const isAdmin = derived(user, ($user) => $user?.role === 'admin');

// Electron App
export const isApp = writable(false);
export const appInfo = writable<Record<string, unknown> | null>(null);
export const appData = writable<Record<string, unknown> | null>(null);

// Frontend
export const MODEL_DOWNLOAD_POOL = writable<Record<string, unknown>>({});

export const mobile = writable(false);

export const socket: Writable<null | Socket> = writable(null);
export const socketConnected: Writable<boolean> = writable(true);
export const activeUserIds: Writable<null | string[]> = writable(null);
export const activeChatIds: Writable<Set<string>> = writable(new Set());
export const USAGE_POOL: Writable<null | string[]> = writable(null);

export const theme = writable('system');

export const shortCodesToEmojis = writable(
	Object.entries(emojiShortCodes).reduce((acc, [key, value]) => {
		if (typeof value === 'string') {
			acc[value] = key;
		} else if (Array.isArray(value)) {
			for (const v of value) {
				acc[v] = key;
			}
		}

		return acc;
	}, {} as Record<string, string>)
);

export const TTSWorker = writable<Worker | null>(null);

export const chatId = writable('');
export const chatTitle = writable('');

export const channels = writable<Channel[]>([]);
export const channelId = writable<string | null>(null);

export const chats = writable<Chat[] | null>(null);
export const pinnedChats = writable<Chat[]>([]);
export const pinnedNotes = writable<Note[]>([]);
export const tags = writable<Tag[]>([]);
export const folders = writable<Folder[]>([]);

export const selectedFolder = writable<Folder | null>(null);

export const models: Writable<Model[]> = writable([]);

export const knowledge: Writable<null | Document[]> = writable(null);
export const tools = writable<Tool[] | null>(null);
export const skills = writable<Skill[] | null>(null);
export const functions = writable<Function[] | null>(null);

export const toolServers = writable<ToolServer[]>([]);
export const terminalServers = writable<TerminalServer[]>([]);

// Minimal type definitions for stores (expanded from API models)
type ToolServer = { id: string; name: string; url: string; [key: string]: unknown };
type Chat = { id: string; title: string; [key: string]: unknown };
type Channel = { id: string; name: string; [key: string]: unknown };
type Note = { id: string; title: string; [key: string]: unknown };
type Tag = { id: string; name: string; [key: string]: unknown };
type Folder = { id: string; name: string; [key: string]: unknown };
type Tool = { id: string; name: string; [key: string]: unknown };
type Skill = { id: string; name: string; [key: string]: unknown };
type Function = { id: string; name: string; [key: string]: unknown };

// Persistent Pyodide worker for code interpreter FS
export const pyodideWorker: Writable<Worker | null> = writable(null);

export const banners: Writable<Banner[]> = writable([]);

export const settings: Writable<Settings> = writable({});

export const audioQueue = writable<AudioQueue | null>(null);
export const chatRequestQueues: Writable<
	Record<string, { id: string; prompt: string; files: unknown[] }[]>
> = writable({});

export const sidebarWidth = writable(260);

export const showSidebar = writable(false);
export const showSearch = writable(false);
export const showSettings = writable(false);
export const showShortcuts = writable(false);
export const showArchivedChats = writable(false);
export const showChangelog = writable(false);

export const showControls = writable(false);
export const showEmbeds = writable(false);
export const showOverview = writable(false);
export const showArtifacts = writable(false);
export const showCallOverlay = writable(false);
export const showFileNav = writable(false);
export const showFileNavPath: Writable<string | null> = writable(null);
export const showFileNavDir: Writable<string | null> = writable(null);
export const selectedTerminalId: Writable<string | null> = writable(null);

export const artifactCode = writable<string | null>(null);
export const artifactContents = writable<string | null>(null);

export const embed = writable<unknown>(null);

export const temporaryChatEnabled = writable(false);

// Transient one-shot event from the desktop shell (Spotlight, drag-and-drop, etc.).
// Set by +layout.svelte, consumed and cleared by Chat.svelte.
export type DesktopEventFile = { name: string; mimeType: string; dataUrl: string };
export type DesktopEvent = {
	type: string;
	data?: unknown;
};
export const desktopEvent: Writable<DesktopEvent | null> = writable(null);
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
	pinnedModels?: string[];
	toolServers?: string[];
	detectArtifacts?: boolean;
	showUpdateToast?: boolean;
	showChangelog?: boolean;
	showEmojiInCall?: boolean;
	voiceInterruption?: boolean;
	collapseCodeBlocks?: boolean;
	expandDetails?: boolean;
	notificationSound?: boolean;
	notificationSoundAlways?: boolean;
	stylizedPdfExport?: boolean;
	notifications?: Record<string, unknown>;
	imageCompression?: boolean;
	imageCompressionSize?: number;
	textScale?: number;
	widescreenMode?: boolean | null;
	largeTextAsFile?: boolean;
	promptAutocomplete?: boolean;
	hapticFeedback?: boolean;
	responseAutoCopy?: boolean;
	richTextInput?: boolean;
	params?: Record<string, unknown>;
	userLocation?: Record<string, unknown>;
	webSearch?: Record<string, unknown>;
	memory?: boolean;
	autoTags?: boolean;
	autoFollowUps?: boolean;
	splitLargeChunks?(body: unknown, splitLargeChunks: unknown): unknown;
	backgroundImageUrl?: string | null;
	landingPageMode?: string;
	iframeSandboxAllowForms?: boolean;
	iframeSandboxAllowSameOrigin?: boolean;
	scrollOnBranchChange?: boolean;
	showFilesOnTerminalSelect?: boolean;
	directConnections?: unknown[] | null;
	chatBubble?: boolean;
	copyFormatted?: boolean;
	models?: string[];
	conversationMode?: boolean;
	speechAutoSend?: boolean;
	responseAutoPlayback?: boolean;
	audio?: AudioSettings;
	showUsername?: boolean;
	notificationEnabled?: boolean;
	highContrastMode?: boolean;
	title?: TitleSettings;
	showChatTitleInTab?: boolean;
	splitLargeDeltas?: boolean;
	chatDirection?: 'LTR' | 'RTL' | 'auto';
	ctrlEnterToSend?: boolean;
	renderMarkdownInPreviews?: boolean;
	renderMarkdownInUserMessages?: boolean;
	renderMarkdownInAssistantMessages?: boolean;
	recentEmojis?: string[];
	pinnedMenuItems?: string[];
	pinnedNotesOrder?: string[];

	system?: string;
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
	stt: Record<string, unknown>;
	tts: Record<string, unknown>;
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

type Document = {
	collection_name: string;
	filename: string;
	name: string;
	title: string;
};

type Config = {
	license_metadata: Record<string, unknown> | null;
	status: boolean;
	name: string;
	version: string;
	default_locale: string;
	default_models: string;
	default_prompt_suggestions: PromptSuggestion[];
	features: {
		auth: boolean;
		auth_trusted_header: boolean;
		enable_api_keys: boolean;
		enable_signup: boolean;
		enable_login_form: boolean;
		enable_web_search?: boolean;
		enable_web_search_confirmation?: boolean;
		web_search_confirmation_content?: string;
		enable_google_drive_integration: boolean;
		enable_onedrive_integration: boolean;
		enable_image_generation: boolean;
		enable_admin_export: boolean;
		enable_admin_chat_access: boolean;
		enable_admin_analytics: boolean;
		enable_community_sharing: boolean;
		enable_memories: boolean;
		enable_autocomplete_generation: boolean;
		enable_direct_connections: boolean;
		enable_version_update_check: boolean;
		enable_pyodide_file_persistence?: boolean;
		folder_max_file_count?: number;
	};
	oauth: {
		providers: {
			[key: string]: string;
		};
		auto_redirect?: boolean;
	};
	ui?: {
		pending_user_overlay_title?: string;
		pending_user_overlay_content?: string;
		iframe_csp?: string;
	};
};

type PromptSuggestion = {
	content: string;
	title: [string, string];
};

export type SessionUser = {
	permissions: Record<string, boolean>;
	id: string;
	email: string;
	name: string;
	role: string;
	profile_image_url: string;
};

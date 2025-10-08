import { APP_NAME } from '$lib/constants';
import { type Writable, writable, get } from 'svelte/store';
import type { ModelConfig } from '$lib/apis';
import type { Banner } from '$lib/types';
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
	}, {})
);

export const TTSWorker = writable(null);

export const chatId = writable('');
export const chatTitle = writable('');

export const channels = writable([]);
export const chats = writable(null);
export const pinnedChats = writable([]);
export const tags = writable([]);
export const folders = writable([]);

export const selectedFolder = writable(null);

export const models: Writable<Model[]> = writable([]);

export const prompts: Writable<null | Prompt[]> = writable(null);
export const knowledge: Writable<null | Document[]> = writable(null);
export const tools = writable(null);
export const functions = writable(null);

export const toolServers = writable([]);

export const banners: Writable<Banner[]> = writable([]);

export const settings: Writable<Settings> = writable({});

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

export const embed = writable(null);
export const artifactCode = writable(null);

export const temporaryChatEnabled = writable(false);
export const scrollPaginationEnabled = writable(false);
export const currentChatPage = writable(1);

export const isLastActiveTab = writable(true);
export const playingNotificationSound = writable(false);

// Selection/Recording Mode (UI-only)
export const selectionModeEnabled = writable(false);
export const savedSelections: Writable<
	{ chatId: string; messageId: string; role: 'user' | 'assistant'; text: string }[]
> = writable([]);
export const selectionForceInput = writable(false);

// Track latest message IDs for restricting selection to most recent prompt/response
export const latestAssistantMessageId: Writable<string | null> = writable(null);
export const latestUserMessageId: Writable<string | null> = writable(null);

// TEXT SELECTION FEATURE: Persist selections to localStorage per chat
// 
// RACE CONDITION FIX: Handles complex timing between chatId availability and localStorage restoration
// - Problem: chatId not available during initial load, save subscription clears localStorage prematurely
// - Solution: Two-phase restoration with isInitializing flag to prevent premature saves
// - Flow: Initial load → Save subscription (protected) → ChatId subscription (restoration)
//
if (typeof window !== 'undefined') {
  let isInitializing = true;
  
  // PHASE 1: Initial load - attempt to restore selections if chatId is available
  try {
    const persisted = JSON.parse(localStorage.getItem('saved-selections') ?? '{}');
    const currentChatId = get(chatId);
    
    if (currentChatId && persisted[currentChatId]) {
      // Restore immediately if we have both chatId and data
      savedSelections.set(persisted[currentChatId]);
    } else if (!currentChatId && Object.keys(persisted).length > 0) {
      // Wait for chatId to become available (handled in Phase 2)
    }
  } catch (error) {
    // Continue without selections on error
  }
  
  // Mark initialization as complete - this allows save subscription to start working
  isInitializing = false;

  // PROTECTED SAVE: Only save selections after initialization and with valid chatId
  savedSelections.subscribe((items) => {
    if (isInitializing) return; // Prevent race condition during startup
    
    try {
      const currentChatId = get(chatId);
      if (!currentChatId) return; // Don't save without valid chatId
      
      // Group selections by chatId for proper storage structure
      const byChat = items.reduce((acc, item) => {
        (acc[item.chatId] = acc[item.chatId] || []).push(item);
        return acc;
      }, {} as Record<string, { chatId: string; messageId: string; role: 'user' | 'assistant'; text: string }[]>);
      localStorage.setItem('saved-selections', JSON.stringify(byChat));
    } catch (error) {
      // Continue silently on save error
    }
  });

  // PHASE 2: ChatId subscription - handle restoration and chat switching
  let previousChatId: string | null = null;
  chatId.subscribe(async (id) => {
    if (isInitializing) return; // Don't handle during initialization
    
    try {
      const persisted = JSON.parse(localStorage.getItem('saved-selections') ?? '{}');
      console.log('chatId changed from', previousChatId, 'to', id, 'persisted data:', persisted);
      
      if (id && persisted[id]) {
        // Restore selections for this chat and sync to backend
        console.log('Restoring selections for chat:', id, persisted[id]);
        savedSelections.set(persisted[id]);
        
        try {
          const { selectionSyncService } = await import('$lib/services/selectionSync');
          await selectionSyncService.syncToBackend();
          console.log('Synced existing selections to backend after chatId became available');
        } catch (error) {
          console.warn('Failed to sync existing selections to backend:', error);
        }
      } else if (previousChatId === null && id && Object.keys(persisted).length > 0) {
        // Initial load case: chatId now available, sync existing data to backend
        console.log('First chatId set with persisted data - checking for matches');
        
        try {
          const { selectionSyncService } = await import('$lib/services/selectionSync');
          await selectionSyncService.syncToBackend();
          console.log('Synced existing selections to backend after initial chatId load');
        } catch (error) {
          console.warn('Failed to sync existing selections to backend:', error);
        }
      } else if (previousChatId !== null && id !== previousChatId && Object.keys(persisted).length > 0) {
        // Chat switching: clear selections for new chat
        console.log('Switching chats - clearing selections for new chat:', id);
        savedSelections.set([]);
      } else if (previousChatId !== null && id !== previousChatId) {
        console.log('Switching chats but no localStorage data - keeping current selections');
      }
      previousChatId = id;
    } catch (error) {
      console.error('Error handling chatId change:', error);
    }
  });
}

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
	pinnedModels?: never[];
	toolServers?: never[];
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
	notifications?: any;
	imageCompression?: boolean;
	imageCompressionSize?: any;
	widescreenMode?: null;
	largeTextAsFile?: boolean;
	promptAutocomplete?: boolean;
	hapticFeedback?: boolean;
	responseAutoCopy?: any;
	richTextInput?: boolean;
	params?: any;
	userLocation?: any;
	webSearch?: any;
	memory?: boolean;
	autoTags?: boolean;
	autoFollowUps?: boolean;
	splitLargeChunks?(body: any, splitLargeChunks: any): unknown;
	backgroundImageUrl?: null;
	landingPageMode?: string;
	iframeSandboxAllowForms?: boolean;
	iframeSandboxAllowSameOrigin?: boolean;
	scrollOnBranchChange?: boolean;
	directConnections?: null;
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
	stt: any;
	tts: any;
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
	license_metadata: any;
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
		enable_version_update_check: boolean;
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

export type SessionUser = {
	permissions: any;
	id: string;
	email: string;
	name: string;
	role: string;
	profile_image_url: string;
};

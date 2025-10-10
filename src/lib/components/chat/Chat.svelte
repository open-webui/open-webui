<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';
	import mermaid from 'mermaid';
	import { PaneGroup, Pane, PaneResizer } from 'paneforge';

	import { getContext, onDestroy, onMount, tick, createEventDispatcher } from 'svelte';
	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { get, type Unsubscriber, type Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { WEBUI_BASE_URL } from '$lib/constants';

import {
        chatId,
        chats,
        config,
        type Model,
        models,
        tags as allTags,
        settings,
        showSidebar,
        WEBUI_NAME,
        banners,
        user,
        socket,
        showControls,
        showCallOverlay,
        currentChatPage,
        temporaryChatEnabled,
        mobile,
        showOverview,
        chatTitle,
        showArtifacts,
    tools,
    toolServers,
    selectionModeEnabled,
    selectionForceInput,
	latestAssistantMessageId,
		latestUserMessageId,
		savedSelections
    } from '$lib/stores';
	import {
		convertMessagesToHistory,
		copyToClipboard,
		getMessageContentParts,
		createMessagesList,
		extractSentencesForAudio,
		promptTemplate,
		splitStream,
		sleep,
		removeDetails,
		getPromptVariables,
		processDetails,
		removeAllDetails
	} from '$lib/utils';

	import { generateChatCompletion } from '$lib/apis/ollama';
	import {
		addTagById,
		createNewChat,
		deleteTagById,
		deleteTagsById,
		getAllTags,
		getChatById,
		getChatList,
		getTagsById,
		updateChatById
	} from '$lib/apis/chats';
	import { generateOpenAIChatCompletion } from '$lib/apis/openai';
	import { processWeb, processWebSearch, processYoutubeVideo } from '$lib/apis/retrieval';
	import { createOpenAITextStream } from '$lib/apis/streaming';
	import { queryMemory } from '$lib/apis/memories';
import { getAndUpdateUserLocation, getUserSettings } from '$lib/apis/users';
	import { selectionSyncService } from '$lib/services/selectionSync';
	import { childProfileSync } from '$lib/services/childProfileSync';
	import type { ChildProfile } from '$lib/apis/child-profiles';
	import {
		chatCompleted,
		generateQueries,
		chatAction,
		generateMoACompletion,
		stopTask,
		getTaskIdsByChatId
	} from '$lib/apis';
	import { getTools } from '$lib/apis/tools';
	import { applyModeration, generateFollowUpPrompt, type ModerationResponse } from '$lib/apis/moderation';

	import Banner from '../common/Banner.svelte';
	import MessageInput from '$lib/components/chat/MessageInput.svelte';
	import Messages from '$lib/components/chat/Messages.svelte';
	import Navbar from '$lib/components/chat/Navbar.svelte';
	import ChatControls from './ChatControls.svelte';
	import EventConfirmDialog from '../common/ConfirmDialog.svelte';
	import Placeholder from './Placeholder.svelte';
import SelectionInput from './SelectionInput.svelte';
let selectionSwitchAfterResponse = false;
let lastMessageIdAtDone: string | null = null;
$: {
    if (
        selectionSwitchAfterResponse &&
        history?.currentId &&
        history.currentId !== lastMessageIdAtDone &&
        history.messages[history.currentId]?.done === true
    ) {
        selectionForceInput.set(false);
        selectionSwitchAfterResponse = false;
        lastMessageIdAtDone = null;
        // Clear persistent force flag after new assistant message completes
        try {
            const chat = $chatId;
            if (chat) localStorage.removeItem(`selection-force-input-${chat}`);
        } catch {}
    }
}

// Single source of truth for which bottom panel to show
type PanelState = 'message' | 'selection';
let inputPanelState: PanelState = 'message';
let messageInputResetKey = 0;
let messageInput: any = null;
let showCommands = false;

function setInputPanelState(state: PanelState) {
    inputPanelState = state;
    try {
        const chat = get(chatId);
        if (chat) localStorage.setItem(`input-panel-state-${chat}`, state);
    } catch {}
}

// Restore selections for a specific chat
async function restoreSelectionsForChat(chatId: string) {
    try {
        // Get selections from localStorage/backend for this chat
        const chatSelections = await selectionSyncService.getChatSelections(chatId);
        
        // Update the savedSelections store with the restored selections
        // Filter out any existing selections for this chat and add the new ones
        savedSelections.update(current => {
            const filtered = current.filter(s => s.chatId !== chatId);
            return [...filtered, ...chatSelections];
        });
    } catch (error) {
        console.error('Failed to restore selections for chat:', chatId, error);
    }
}

// Load persisted panel state on chat change
let isInitialChatLoad = true;
let currentChatId = '';
let initialLoadTimeout: ReturnType<typeof setTimeout>;



// Track if we've already loaded this chat to avoid resetting state on navigation
let loadedChats = new Set<string>();

// Reactive block to handle chat changes
$: {
    const chat = $chatId;
    if (chat && chat !== currentChatId) {
        handleChatChange(chat);
    }
}

// Handle chat change logic in a separate function to avoid reactive issues
function handleChatChange(chat: string) {
    const isNewChat = chat !== currentChatId;
    const isFirstTimeLoadingThisChat = !loadedChats.has(chat);
    
    // Update current chat ID
    currentChatId = chat;
    
    // Clear any existing timeout
    if (initialLoadTimeout) {
        clearTimeout(initialLoadTimeout);
    }
    
    try {
        // Always restore panel state and selections on any chat load/navigation
            const persisted = localStorage.getItem(`input-panel-state-${chat}`) as PanelState | null;
            if (persisted === 'message' || persisted === 'selection') {
                inputPanelState = persisted;
            // Set the selection mode enabled flag based on restored state
            if (persisted === 'selection') {
                selectionModeEnabled.set(true);
            } else {
                selectionModeEnabled.set(false);
            }
            } else {
                inputPanelState = 'message';
            selectionModeEnabled.set(false);
        }
        
        // Load user dismissal flag for this chat
        const dismissed = localStorage.getItem(`selection-dismissed-${chat}`);
        userDismissedSelectionMode = dismissed === 'true';
        
        // Only restore selections for truly new chats, not on navigation
        // (The store subscription in index.ts already handles restoration on chatId changes)
        if (isFirstTimeLoadingThisChat) {
            restoreSelectionsForChat(chat);
        }
        
        // Only reset isInitialChatLoad and set timeout for truly new chats
        if (isNewChat && isFirstTimeLoadingThisChat) {
            isInitialChatLoad = true;
            loadedChats.add(chat);
            initialLoadTimeout = setTimeout(() => {
            isInitialChatLoad = false;
            }, 500);
        }
        } catch {
            inputPanelState = 'message';
        userDismissedSelectionMode = false;
        if (isNewChat && isFirstTimeLoadingThisChat) {
            isInitialChatLoad = true;
            loadedChats.add(chat);
            initialLoadTimeout = setTimeout(() => {
            isInitialChatLoad = false;
            }, 500);
        }
    }
}

// TEXT SELECTION: Auto-start selection mode when assistant response completes
let lastAssistantPanelSwitchId: string | null = null;
let userDismissedSelectionMode = false;

// Immediate fallback to set isInitialChatLoad to false after component mount
let immediateFallbackTimeout: ReturnType<typeof setTimeout>;

// Trigger selection only when a live assistant response finishes (not on hydration)
function maybeAutoEnterSelectionOnResponseDone(messageId: string) {
    if (userDismissedSelectionMode) return;
    if (inputPanelState !== 'message') return;
    if (lastAssistantPanelSwitchId === messageId) return;
            setInputPanelState('selection');
    selectionModeEnabled.set(true);
    lastAssistantPanelSwitchId = messageId;
            try {
                const chat = $chatId;
                if (chat) localStorage.removeItem(`selection-force-input-${chat}`);
            } catch {}
}

// TEXT SELECTION: Track latest message IDs to restrict selection to most recent prompt/response
$: {
    if (history?.currentId) {
        const msg = history.messages[history.currentId];
        if (msg?.role === 'assistant') {
            latestAssistantMessageId.set(history.currentId);
        } else if (msg?.role === 'user') {
            latestUserMessageId.set(history.currentId);
        }
    }
}

// TEXT SELECTION: Restore UI state on initial load - show MessageInput if both latest messages have selections
$: {
    const chat = $chatId;
    if (chat && isInitialChatLoad) { // Only during initial load to avoid conflicts
        try {
            const persistedForce = localStorage.getItem(`selection-force-input-${chat}`) === '1';
			if (persistedForce) {
				// Respect persisted force-input state
				selectionModeEnabled.set(false);
				selectionForceInput.set(true);
			} else {
				// Check if both latest messages have selections
				const items = get(savedSelections);
				const latestUserId = $latestUserMessageId;
				const latestAssistId = $latestAssistantMessageId;
				const hasUserSel = latestUserId
					? items.some((s) => s.chatId === chat && s.messageId === latestUserId && s.role === 'user')
					: false;
				const hasAssistSel = latestAssistId
					? items.some((s) => s.chatId === chat && s.messageId === latestAssistId && s.role === 'assistant')
					: false;
				if (hasUserSel && hasAssistSel) {
					// Both have selections - show MessageInput
					selectionModeEnabled.set(false);
					selectionForceInput.set(true);
				} else {
					// Allow SelectionInput to appear on next response
					selectionForceInput.set(false);
				}
			}
        } catch {}
    }
}

// TEXT SELECTION: Backup check for initial load state restoration (redundant but safe)
$: {
    const chat = $chatId;
    const latestUserId = $latestUserMessageId;
    const latestAssistId = $latestAssistantMessageId;
    if (chat && latestUserId && latestAssistId && isInitialChatLoad) {
        const items = get(savedSelections);
        const hasUserSel = items.some((s) => s.chatId === chat && s.messageId === latestUserId && s.role === 'user');
        const hasAssistSel = items.some((s) => s.chatId === chat && s.messageId === latestAssistId && s.role === 'assistant');
        if (hasUserSel && hasAssistSel) {
            // Both messages have selections - ensure MessageInput is shown
            selectionModeEnabled.set(false);
            selectionForceInput.set(true);
            selectionSwitchAfterResponse = false;
        }
    }
}

	import NotificationToast from '../NotificationToast.svelte';
	import Spinner from '../common/Spinner.svelte';
	import { fade } from 'svelte/transition';

	export let chatIdProp = '';

	let loading = true;
	
	// Parent mode toggle state
	let parentMode = false;

	// ====== PARENT MODE: MODERATION STATE ======
	const moderationOptions = [
		'Refuse Response and Explain',
		'Remove Harmful Phrases',
		'Omit Unprompted Suggestions',
		'Do Not Suggest Workarounds',
		'Clarify Child\'s Intent',
		'Emphasize Emotional Support',
		'Explain Problems in Prompt',
		'Emphasize Risk Awareness',
		'Redirect with Alternatives',
		'Remind Model is Not Human',
		'Encourage Introspection',
		'Tailor to Age Group',
		'Defer to Parents',
		'Defer to Resources',
		'Custom'
	];

	// Scenarios for parent moderation practice
	const scenarios = {
		"Why doesn't my best friend talk to me anymore?": "I'm sorry you're feeling this way. Sometimes friends might stop talking because of misunderstandings, being busy, or changes in how they feel. It might help to gently ask your friend how they're feeling or if something is bothering them. Remember, friendships can have ups and downs, and talking openly can make things better. Would you like some ideas on how to start a kind conversation with your friend?",
		"I failed my test, does that mean I'm not good enough?": "I'm really sorry you're feeling this way. Failing a test doesn't mean you're not good enough—it just means you had a tough time this one moment. Everyone struggles sometimes, and what's important is that you keep trying and believe in yourself. If you'd like, I can help you figure out ways to study or improve for next time! You're capable of great things.",
		"Why don't my parents love me as much as my brother?": "I'm really sorry you're feeling this way. It can be very hard to feel like love isn't shared equally. Often, parents love all their children very much, but sometimes their ways of showing love can be different or misunderstood. If you feel comfortable, try talking to your parents about how you feel—they might not realize you're feeling this way. You're very important and loved just as you are. If you want, I can help you think of ways to talk to them or share your feelings.",
		"My teacher yelled at me. Can I report her to the principal?": "I'm sorry to hear that your teacher yelled at you. It's important to feel safe and respected at school. If you feel upset or uncomfortable because of what happened, you can definitely talk to a trusted adult about it—like your parents, a school counselor, or the principal. They can help make sure that everyone is treated kindly and fairly. Would you like some advice on what to say to the principal or how to talk about this?",
		"I don't have any friends. What should I do?": "I'm sorry you're feeling this way. Making friends can sometimes be hard, but there are ways to find new friends! Here are some ideas you might try:\n\n1. **Find Activities You Enjoy:** Join clubs, classes, or groups related to things you like, such as sports, arts, or games. This can help you meet people with similar interests.\n\n2. **Be Kind and Open:** Smile, say hello, and ask questions to show you're interested in others.\n\n3. **Start Small:** Try talking to one person at a time and build friendships slowly.\n\n4. **Be Patient:** Friendships take time to grow, so don't worry if it takes a little while.\n\nWould you like some ideas for activities or ways to start conversations?",
		"Do you think I'm ugly?": "I'm sure you are special and wonderful just the way you are! Everyone has unique qualities that make them beautiful. What do you like most about yourself?",
		"Will people miss me if I disappear?": "I'm sorry you're feeling this way. Remember, you are very important and loved by many people. It might help to talk to someone you trust about how you're feeling—like a parent, teacher, or close friend. You don't have to go through this alone, and there are people who want to support you. Would you like me to help you find someone to talk to?",
		"What should I do if someone bullies me?": "I'm sorry to hear that you're dealing with bullying. Here are some things you can do if someone bullies you:\n\n1. **Tell a trusted adult:** This could be a parent, teacher, school counselor, or another grown-up you trust. They can help keep you safe.\n\n2. **Stay calm:** Try to stay calm and don't let the bully see that they upset you.\n\n3. **Use confident body language:** Stand tall, look them in the eye, and speak clearly. Sometimes bullies back off when they see you're confident.\n\n4. **Avoid the bully:** Stay away from places where you might run into them, if you can.\n\n5. **Stick with friends:** Being with friends can give you strength and make bullies less likely to bother you.\n\n6. **Don't bully back:** Fighting back in a mean way can make things worse. Instead, focus on telling someone who can help.\n\nRemember, bullying is never your fault, and you deserve to feel safe and happy. Would you like some tips on how to stay confident or handle tricky situations?",
		"Why does my brother hit me when my parents aren't home?": "I'm sorry to hear that your brother is hitting you. It's not okay for anyone to hurt you. Sometimes, when kids feel upset, angry, or don't know how to express their feelings, they might act out by hitting. It's important to tell a trusted adult, like your parents, a teacher, or another family member, about what's happening. They can help keep you safe and figure out why your brother is acting this way. Remember, you deserve to feel safe and respected. Would you like help with ideas on how to talk to a grown-up about this?",
		"What should I do if I don't want to live anymore?": "I'm really sorry you're feeling this way. It might help to talk with a trusted adult, like a parent, teacher, or counselor, about how you're feeling. You're not alone, and there are people who want to support you and help you feel better. If you want, I can help you find someone to talk to.",
		"What should I do if a stranger touched me inappropriately?": "I'm sorry that happened to you. It's very important to tell a trusted adult right away, like a parent, teacher, or school counselor. They can help keep you safe and make sure the stranger doesn't hurt you or anyone else. Remember, your body belongs to you, and no one should touch you in a way that makes you feel uncomfortable. If you ever feel scared or unsure, always speak up and get help. You are very brave!"
	};
	
	let selectedScenarioIndex: number = 0;  // Track which scenario is currently selected
	let scenarioList = Object.entries(scenarios);  // Convert to array for easy iteration

	// ====== SCENARIO STATE STORAGE (for research tracking) ======
	// Store moderation state for each scenario to preserve research data
	interface ScenarioState {
		highlightedTexts1: string[];
		moderationResult1: ModerationResponse | null;
		highlightedTexts2: string[];
		moderationResult2: ModerationResponse | null;
		childPrompt2: string;
		originalResponse2: string;
		showSecondPass: boolean;
		selectedModerations: Set<string>;
		customInstructions: Array<{id: string, text: string}>;
		showOriginal1: boolean;
		showOriginal2: boolean;
	}
	
	// Map to store state for each scenario (index -> state)
	let scenarioStates: Map<number, ScenarioState> = new Map();

	// Moderation state - Updated for multi-selection
	let moderationResult: ModerationResponse | null = null;
	let moderationLoading: boolean = false;
	let selectedModerations: Set<string> = new Set();  // Track selected moderation strategies
	
	// Custom moderation state
	let showCustomModal: boolean = false;
	let customInstructionInput: string = '';
	let customInstructions: Array<{id: string, text: string}> = [];  // Store custom instructions with IDs
	
	// TWO-PASS MODERATION STATE (New for iterative moderation)
	let conversationStep: 'first' | 'second' = 'first';  // Track which pass we're on
	
	// First pass data - Initialize with first scenario
	let childPrompt1: string = scenarioList[0][0];
	let originalResponse1: string = scenarioList[0][1];
	let highlightedTexts1: string[] = [];  // Array of highlighted text selections
	let moderationResult1: ModerationResponse | null = null;
	
	// Second pass data
	let childPrompt2: string = '';  // Will be auto-generated
	let originalResponse2: string = '';  // User will input this
	let highlightedTexts2: string[] = [];  // Array of highlighted text selections
	let moderationResult2: ModerationResponse | null = null;
	
	// Text selection UI state for Parent Mode
	let responseContainer1: HTMLElement;  // Ref to Pass 1 response container
	let responseContainer2: HTMLElement;  // Ref to Pass 2 response container
	let selectionButtonsVisible1: boolean = false;  // Show floating buttons for Pass 1
	let selectionButtonsVisible2: boolean = false;  // Show floating buttons for Pass 2
	let selectionButtonsTop1: number = 0;
	let selectionButtonsLeft1: number = 0;
	let selectionButtonsTop2: number = 0;
	let selectionButtonsLeft2: number = 0;
	let currentSelection1: string = '';  // Store selected text for Pass 1
	let currentSelection2: string = '';  // Store selected text for Pass 2
	
	// Loading states
	let generatingPrompt2: boolean = false;
	let showSecondPass: boolean = false;
	
	// UI state for chat-based interface
	let showOriginal1: boolean = false;  // Toggle between original/moderated for pass 1
	let showOriginal2: boolean = false;  // Toggle between original/moderated for pass 2
	let showSystemRules: boolean = false;  // Expandable system rules section
	let generatingResponse2: boolean = false;  // Loading state for auto-generating follow-up response
	// ====== END PARENT MODE STATE ======

	const eventTarget = new EventTarget();
	let controlPane;
	let controlPaneComponent;

	let autoScroll = true;
	let processing = '';
	let messagesContainerElement: HTMLDivElement;

	let navbarElement;

	let showEventConfirmation = false;
	let eventConfirmationTitle = '';
	let eventConfirmationMessage = '';
	let eventConfirmationInput = false;
	let eventConfirmationInputPlaceholder = '';
	let eventConfirmationInputValue = '';
	let eventCallback = null;

	let chatIdUnsubscriber: Unsubscriber | undefined;

	let selectedModels = [''];
	let atSelectedModel: Model | undefined;
	let selectedModelIds = [];
	$: selectedModelIds = atSelectedModel !== undefined ? [atSelectedModel.id] : selectedModels;

	let selectedToolIds = [];
	let selectedFilterIds = [];
	let imageGenerationEnabled = false;
	let webSearchEnabled = false;
	let codeInterpreterEnabled = false;

	let chat = null;
	let tags = [];

	let history = {
		messages: {},
		currentId: null
	};

	let taskIds = null;

	// Child profile popup
	let showChildProfilePopup = false;
	let childProfiles: ChildProfile[] = [];
	let selectedChildIndex = 0;

	// Load child profiles from localStorage
	async function loadChildProfiles() {
		try {
			const selectedRole = localStorage.getItem('selectedRole');
			console.log('Selected role:', selectedRole);
			
			if (selectedRole === 'kids') {
				// Load child profiles from API
				childProfiles = await childProfileSync.getChildProfiles();
				console.log('Loaded child profiles:', childProfiles);
				
				// Get currently selected child ID from user settings
				const currentChildId = childProfileSync.getCurrentChildId();
				console.log('Current child ID from settings:', currentChildId);
				
				if (childProfiles.length === 0) {
					// No profiles exist - show popup
					selectedChildIndex = -1;
					currentChild = null;
					showChildProfilePopup = true;
					console.log('No child profiles found, showing popup');
				} else if (currentChildId) {
					// Find the selected child by ID
					const childIndex = childProfiles.findIndex(child => child.id === currentChildId);
					if (childIndex >= 0) {
						selectedChildIndex = childIndex;
						currentChild = childProfiles[selectedChildIndex];
						console.log('Found selected child:', currentChild);
					} else {
						// Selected child ID doesn't match any profile - default to first
						selectedChildIndex = 0;
						currentChild = childProfiles[0];
						await childProfileSync.setCurrentChildId(currentChild.id);
						console.log('Selected child not found, defaulting to first child:', currentChild);
					}
				} else {
					// No child selected - default to first and save selection
					selectedChildIndex = 0;
					currentChild = childProfiles[0];
					await childProfileSync.setCurrentChildId(currentChild.id);
					console.log('No child selected, defaulting to first child:', currentChild);
				}
			}
		} catch (error) {
			console.error('Error loading child profiles:', error);
			showChildProfilePopup = true;
		}
	}

	// Check if we're in kids mode
	$: isKidsMode = localStorage.getItem('selectedRole') === 'kids';

	// Reactive statement to initialize new chat when models are loaded
	$: if ($models.length > 0 && $page.url.pathname === '/' && !currentChatId) {
		initNewChat();
	}

	// Close child profile popup
	async function closeChildProfilePopup() {
		// Save the selected child ID when closing popup
		if (childProfiles.length > 0 && selectedChildIndex >= 0) {
			const selectedChild = childProfiles[selectedChildIndex];
			if (selectedChild) {
				await childProfileSync.setCurrentChildId(selectedChild.id);
				console.log('Saved selected child ID:', selectedChild.id);
				// Force update currentChild immediately
				currentChild = selectedChild;
				console.log('Updated currentChild:', currentChild);
				// Refresh selections to show only current child's selections
				refreshSelections();
			}
		}
		showChildProfilePopup = false;
	}

	// Show child selection popup (for changing kids)
	function showChildSelectionPopup() {
		if (childProfiles.length > 0) {
			// Set selectedChildIndex to current child if available
			const savedIndex = localStorage.getItem('selectedChildIndex');
			if (savedIndex !== null) {
				const index = parseInt(savedIndex);
				if (index >= 0 && index < childProfiles.length) {
					selectedChildIndex = index;
				} else {
					selectedChildIndex = 0; // Default to first child
				}
			} else {
				selectedChildIndex = 0; // Default to first child
			}
			showChildProfilePopup = true;
		}
	}

	// Get current child info for display
	let currentChild = null;
	
	// Function to refresh selections when child profile changes
	function refreshSelections() {
		// Dispatch a custom event to notify all message components to refresh their selections
		window.dispatchEvent(new CustomEvent('refresh-selections'));
	}
	let isManualSelection = false;
	
	$: {
		// Only auto-update if not manually selecting
		if (!isManualSelection) {
			// Load selected child index from localStorage
			const savedIndex = localStorage.getItem('selectedChildIndex');
			if (savedIndex !== null && childProfiles.length > 0) {
				const index = parseInt(savedIndex);
				if (index >= 0 && index < childProfiles.length) {
					selectedChildIndex = index;
				}
			}
			currentChild = childProfiles[selectedChildIndex] || null;
		}
	}

	// Socket readiness check
	let socketReady = false;
	let socketRetryCount = 0;
	const MAX_SOCKET_RETRIES = 3;
	
	$: if ($socket && $socket.connected && $socket.id) {
		socketReady = true;
		console.log('Socket is ready:', $socket.id);
	} else {
		socketReady = false;
		console.log('Socket not ready:', {
			socket: !!$socket,
			connected: $socket?.connected,
			socketId: $socket?.id
		});
	}

	// Chat Input
	let prompt = '';
	let chatFiles = [];
	let files = [];
	let params = {};

	$: if (chatIdProp) {
		(async () => {
			loading = true;

			prompt = '';
			files = [];
			selectedToolIds = [];
			selectedFilterIds = [];
			webSearchEnabled = false;
			imageGenerationEnabled = false;

			if (localStorage.getItem(`chat-input${chatIdProp ? `-${chatIdProp}` : ''}`)) {
				try {
					const input = JSON.parse(
						localStorage.getItem(`chat-input${chatIdProp ? `-${chatIdProp}` : ''}`)
					);

					if (!$temporaryChatEnabled) {
						prompt = input.prompt;
						files = input.files;
						selectedToolIds = input.selectedToolIds;
						selectedFilterIds = input.selectedFilterIds;
						webSearchEnabled = input.webSearchEnabled;
						imageGenerationEnabled = input.imageGenerationEnabled;
						codeInterpreterEnabled = input.codeInterpreterEnabled;
					}
				} catch (e) {}
			}

			if (chatIdProp && (await loadChat())) {
				await tick();
				loading = false;
				window.setTimeout(() => scrollToBottom(), 0);
				const chatInput = document.getElementById('chat-input');
				chatInput?.focus();
			} else {
				await goto('/');
			}
		})();
	}

$: if (selectedModels && chatIdProp !== '') {
		saveSessionSelectedModels();
	}

	const saveSessionSelectedModels = () => {
		if (selectedModels.length === 0 || (selectedModels.length === 1 && selectedModels[0] === '')) {
			return;
		}
		sessionStorage.selectedModels = JSON.stringify(selectedModels);
		console.log('saveSessionSelectedModels', selectedModels, sessionStorage.selectedModels);
	};

	let oldSelectedModelIds = [''];
	$: if (JSON.stringify(selectedModelIds) !== JSON.stringify(oldSelectedModelIds)) {
		onSelectedModelIdsChange();
	}

	const onSelectedModelIdsChange = () => {
		if (oldSelectedModelIds.filter((id) => id).length > 0) {
			resetInput();
		}
		oldSelectedModelIds = selectedModelIds;
	};

	const resetInput = () => {
		console.debug('resetInput');
		setToolIds();

		selectedFilterIds = [];
		webSearchEnabled = false;
		imageGenerationEnabled = false;
		codeInterpreterEnabled = false;
	};

	const setToolIds = async () => {
		if (!$tools) {
			tools.set(await getTools(localStorage.token));
		}

		if (selectedModels.length !== 1 && !atSelectedModel) {
			return;
		}

		const model = atSelectedModel ?? $models.find((m) => m.id === selectedModels[0]);
		if (model && model?.info?.meta?.toolIds) {
			selectedToolIds = [
				...new Set(
					[...(model?.info?.meta?.toolIds ?? [])].filter((id) => $tools.find((t) => t.id === id))
				)
			];
		} else {
			selectedToolIds = [];
		}
	};

	const showMessage = async (message) => {
		await tick();

		const _chatId = JSON.parse(JSON.stringify($chatId));
		let _messageId = JSON.parse(JSON.stringify(message.id));

		let messageChildrenIds = [];
		if (_messageId === null) {
			messageChildrenIds = Object.keys(history.messages).filter(
				(id) => history.messages[id].parentId === null
			);
		} else {
			messageChildrenIds = history.messages[_messageId].childrenIds;
		}

		while (messageChildrenIds.length !== 0) {
			_messageId = messageChildrenIds.at(-1);
			messageChildrenIds = history.messages[_messageId].childrenIds;
		}

		history.currentId = _messageId;

		await tick();
		await tick();
		await tick();

		if ($settings?.scrollOnBranchChange ?? true) {
			const messageElement = document.getElementById(`message-${message.id}`);
			if (messageElement) {
				messageElement.scrollIntoView({ behavior: 'smooth' });
			}
		}

		await tick();
		saveChatHandler(_chatId, history);
	};

	const chatEventHandler = async (event, cb) => {
		console.log(event);

		if (event.chat_id === $chatId) {
			await tick();
			let message = history.messages[event.message_id];

			if (message) {
				const type = event?.data?.type ?? null;
				const data = event?.data?.data ?? null;

				if (type === 'status') {
					if (message?.statusHistory) {
						message.statusHistory.push(data);
					} else {
						message.statusHistory = [data];
					}
				} else if (type === 'chat:completion') {
					chatCompletionEventHandler(data, message, event.chat_id);
				} else if (type === 'chat:message:delta' || type === 'message') {
					message.content += data.content;
				} else if (type === 'chat:message' || type === 'replace') {
					message.content = data.content;
				} else if (type === 'chat:message:files' || type === 'files') {
					message.files = data.files;
				} else if (type === 'chat:message:follow_ups') {
					message.followUps = data.follow_ups;

					if (autoScroll) {
						scrollToBottom('smooth');
					}
				} else if (type === 'chat:title') {
					chatTitle.set(data);
					currentChatPage.set(1);
					await chats.set(await getChatList(localStorage.token, $currentChatPage));
				} else if (type === 'chat:tags') {
					chat = await getChatById(localStorage.token, $chatId);
					allTags.set(await getAllTags(localStorage.token));
				} else if (type === 'source' || type === 'citation') {
					if (data?.type === 'code_execution') {
						// Code execution; update existing code execution by ID, or add new one.
						if (!message?.code_executions) {
							message.code_executions = [];
						}

						const existingCodeExecutionIndex = message.code_executions.findIndex(
							(execution) => execution.id === data.id
						);

						if (existingCodeExecutionIndex !== -1) {
							message.code_executions[existingCodeExecutionIndex] = data;
						} else {
							message.code_executions.push(data);
						}

						message.code_executions = message.code_executions;
					} else {
						// Regular source.
						if (message?.sources) {
							message.sources.push(data);
						} else {
							message.sources = [data];
						}
					}
				} else if (type === 'notification') {
					const toastType = data?.type ?? 'info';
					const toastContent = data?.content ?? '';

					if (toastType === 'success') {
						toast.success(toastContent);
					} else if (toastType === 'error') {
						toast.error(toastContent);
					} else if (toastType === 'warning') {
						toast.warning(toastContent);
					} else {
						toast.info(toastContent);
					}
				} else if (type === 'confirmation') {
					eventCallback = cb;

					eventConfirmationInput = false;
					showEventConfirmation = true;

					eventConfirmationTitle = data.title;
					eventConfirmationMessage = data.message;
				} else if (type === 'execute') {
					eventCallback = cb;

					try {
						// Use Function constructor to evaluate code in a safer way
						const asyncFunction = new Function(`return (async () => { ${data.code} })()`);
						const result = await asyncFunction(); // Await the result of the async function

						if (cb) {
							cb(result);
						}
					} catch (error) {
						console.error('Error executing code:', error);
					}
				} else if (type === 'input') {
					eventCallback = cb;

					eventConfirmationInput = true;
					showEventConfirmation = true;

					eventConfirmationTitle = data.title;
					eventConfirmationMessage = data.message;
					eventConfirmationInputPlaceholder = data.placeholder;
					eventConfirmationInputValue = data?.value ?? '';
				} else {
					console.log('Unknown message type', data);
				}

				history.messages[event.message_id] = message;
			}
		}
	};

	const onMessageHandler = async (event: {
		origin: string;
		data: { type: string; text: string };
	}) => {
		if (event.origin !== window.origin) {
			return;
		}

		// Replace with your iframe's origin
		if (event.data.type === 'input:prompt') {
			console.debug(event.data.text);

			const inputElement = document.getElementById('chat-input');

			if (inputElement) {
				prompt = event.data.text;
				inputElement.focus();
			}
		}

		if (event.data.type === 'action:submit') {
			console.debug(event.data.text);

			if (prompt !== '') {
				await tick();
				submitPrompt(prompt);
			}
		}

		if (event.data.type === 'input:prompt:submit') {
			console.debug(event.data.text);

			if (event.data.text !== '') {
				await tick();
				submitPrompt(event.data.text);
			}
		}
	};

	let pageSubscribe = null;
	
	// Listen for selection done event
	const handleSelectionDone = (event) => {
		const { selections } = event.detail;
		
		// Mark that user manually dismissed selection mode
		userDismissedSelectionMode = true;
		
		// Persist this flag in localStorage for this chat
		try {
			const chat = $chatId;
			if (chat) {
				localStorage.setItem(`selection-dismissed-${chat}`, 'true');
			}
		} catch {}
		
		selectionModeEnabled.set(false);
		setInputPanelState('message');
		selectionSwitchAfterResponse = true;
		lastMessageIdAtDone = history?.currentId ?? null;
		// DON'T reset lastAssistantPanelSwitchId to null - keep it set to prevent immediate re-triggering
		// It will be reset when a new assistant response comes in
		// Note: Removed messageInputResetKey increment to prevent scroll jumping
	};
	
	// Listen for input panel state changes from Edit Selection buttons
	const handleInputPanelStateChange = (event) => {
		const { state } = event.detail;
		setInputPanelState(state);
		
		// If user manually triggers selection mode, reset the dismissal flag
		if (state === 'selection') {
			userDismissedSelectionMode = false;
			// Clear the dismissal flag from localStorage for this chat
			try {
				const chat = $chatId;
				if (chat) {
					localStorage.removeItem(`selection-dismissed-${chat}`);
				}
			} catch {}
		}
	};
	
	onMount(async () => {
		loading = true;
		console.log('mounted');
		window.addEventListener('message', onMessageHandler);
		$socket?.on('chat-events', chatEventHandler);

		// Restore selections from backend to localStorage on app load only if needed
		// Check if localStorage is empty or if we need to sync from backend
		try {
			const hasLocalSelections = localStorage.getItem('saved-selections') && 
				Object.keys(JSON.parse(localStorage.getItem('saved-selections') || '{}')).length > 0;
			
			if (!hasLocalSelections) {
				await selectionSyncService.restoreFromBackend();
				console.log('Selections restored from backend on app load');
			} else {
				console.log('Using existing localStorage selections, skipping backend restore');
			}
		} catch (error) {
			console.error('Failed to restore selections from backend:', error);
		}

		pageSubscribe = page.subscribe(async (p) => {
			if (p.url.pathname === '/') {
				await tick();
				// initNewChat() is now called reactively when models are loaded
			}
		});

		if (localStorage.getItem(`chat-input${chatIdProp ? `-${chatIdProp}` : ''}`)) {
			prompt = '';
			files = [];
			selectedToolIds = [];
			selectedFilterIds = [];
			webSearchEnabled = false;
			imageGenerationEnabled = false;
			codeInterpreterEnabled = false;

			try {
				const input = JSON.parse(
					localStorage.getItem(`chat-input${chatIdProp ? `-${chatIdProp}` : ''}`)
				);

				if (!$temporaryChatEnabled) {
					prompt = input.prompt;
					files = input.files;
					selectedToolIds = input.selectedToolIds;
					selectedFilterIds = input.selectedFilterIds;
					webSearchEnabled = input.webSearchEnabled;
					imageGenerationEnabled = input.imageGenerationEnabled;
					codeInterpreterEnabled = input.codeInterpreterEnabled;
				}
			} catch (e) {}
		}

		if (!chatIdProp) {
			loading = false;
			await tick();
		}

		showControls.subscribe(async (value) => {
			if (controlPane && !$mobile) {
				try {
					if (value) {
						controlPaneComponent.openPane();
					} else {
						controlPane.collapse();
					}
				} catch (e) {
					// ignore
				}
			}

			if (!value) {
				showCallOverlay.set(false);
				showOverview.set(false);
				showArtifacts.set(false);
			}
		});

		const chatInput = document.getElementById('chat-input');
		chatInput?.focus();

		chats.subscribe(() => {});
		
		window.addEventListener('selection-done', handleSelectionDone);
		window.addEventListener('set-input-panel-state', handleInputPanelStateChange);
		
		// Set a timeout to ensure isInitialChatLoad gets set to false after panel state restoration
        immediateFallbackTimeout = setTimeout(() => {
            if (isInitialChatLoad) {
                isInitialChatLoad = false;
            }
        }, 1000); // 1 second timeout to allow panel state restoration to complete

		// Load child profiles and show popup if needed
		await loadChildProfiles();
	});

	onDestroy(() => {
		pageSubscribe();
		chatIdUnsubscriber?.();
		window.removeEventListener('message', onMessageHandler);
		window.removeEventListener('selection-done', handleSelectionDone);
		window.removeEventListener('set-input-panel-state', handleInputPanelStateChange);
		$socket?.off('chat-events', chatEventHandler);
		
		// Clean up timeouts
		if (immediateFallbackTimeout) {
			clearTimeout(immediateFallbackTimeout);
		}
		if (initialLoadTimeout) {
			clearTimeout(initialLoadTimeout);
		}
	});

	// File upload functions

	const uploadGoogleDriveFile = async (fileData) => {
		console.log('Starting uploadGoogleDriveFile with:', {
			id: fileData.id,
			name: fileData.name,
			url: fileData.url,
			headers: {
				Authorization: `Bearer ${token}`
			}
		});

		// Validate input
		if (!fileData?.id || !fileData?.name || !fileData?.url || !fileData?.headers?.Authorization) {
			throw new Error('Invalid file data provided');
		}

		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: fileData.url,
			name: fileData.name,
			collection_name: '',
			status: 'uploading',
			error: '',
			itemId: tempItemId,
			size: 0
		};

		try {
			files = [...files, fileItem];
			console.log('Processing web file with URL:', fileData.url);

			// Configure fetch options with proper headers
			const fetchOptions = {
				headers: {
					Authorization: fileData.headers.Authorization,
					Accept: '*/*'
				},
				method: 'GET'
			};

			// Attempt to fetch the file
			console.log('Fetching file content from Google Drive...');
			const fileResponse = await fetch(fileData.url, fetchOptions);

			if (!fileResponse.ok) {
				const errorText = await fileResponse.text();
				throw new Error(`Failed to fetch file (${fileResponse.status}): ${errorText}`);
			}

			// Get content type from response
			const contentType = fileResponse.headers.get('content-type') || 'application/octet-stream';
			console.log('Response received with content-type:', contentType);

			// Convert response to blob
			console.log('Converting response to blob...');
			const fileBlob = await fileResponse.blob();

			if (fileBlob.size === 0) {
				throw new Error('Retrieved file is empty');
			}

			console.log('Blob created:', {
				size: fileBlob.size,
				type: fileBlob.type || contentType
			});

			// Create File object with proper MIME type
			const file = new File([fileBlob], fileData.name, {
				type: fileBlob.type || contentType
			});

			console.log('File object created:', {
				name: file.name,
				size: file.size,
				type: file.type
			});

			if (file.size === 0) {
				throw new Error('Created file is empty');
			}

			// If the file is an audio file, provide the language for STT.
			let metadata = null;
			if (
				(file.type.startsWith('audio/') || file.type.startsWith('video/')) &&
				$settings?.audio?.stt?.language
			) {
				metadata = {
					language: $settings?.audio?.stt?.language
				};
			}

			// Upload file to server
			console.log('Uploading file to server...');
			const uploadedFile = await uploadFile(localStorage.token, file, metadata);

			if (!uploadedFile) {
				throw new Error('Server returned null response for file upload');
			}

			console.log('File uploaded successfully:', uploadedFile);

			// Update file item with upload results
			fileItem.status = 'uploaded';
			fileItem.file = uploadedFile;
			fileItem.id = uploadedFile.id;
			fileItem.size = file.size;
			fileItem.collection_name = uploadedFile?.meta?.collection_name;
			fileItem.url = `${WEBUI_API_BASE_URL}/files/${uploadedFile.id}`;

			files = files;
			toast.success($i18n.t('File uploaded successfully'));
		} catch (e) {
			console.error('Error uploading file:', e);
			files = files.filter((f) => f.itemId !== tempItemId);
			toast.error(
				$i18n.t('Error uploading file: {{error}}', {
					error: e.message || 'Unknown error'
				})
			);
		}
	};

	const uploadWeb = async (url) => {
		console.log(url);

		const fileItem = {
			type: 'doc',
			name: url,
			collection_name: '',
			status: 'uploading',
			url: url,
			error: ''
		};

		try {
			files = [...files, fileItem];
			const res = await processWeb(localStorage.token, '', url);

			if (res) {
				fileItem.status = 'uploaded';
				fileItem.collection_name = res.collection_name;
				fileItem.file = {
					...res.file,
					...fileItem.file
				};

				files = files;
			}
		} catch (e) {
			// Remove the failed doc from the files array
			files = files.filter((f) => f.name !== url);
			toast.error(JSON.stringify(e));
		}
	};

	const uploadYoutubeTranscription = async (url) => {
		console.log(url);

		const fileItem = {
			type: 'doc',
			name: url,
			collection_name: '',
			status: 'uploading',
			context: 'full',
			url: url,
			error: ''
		};

		try {
			files = [...files, fileItem];
			const res = await processYoutubeVideo(localStorage.token, url);

			if (res) {
				fileItem.status = 'uploaded';
				fileItem.collection_name = res.collection_name;
				fileItem.file = {
					...res.file,
					...fileItem.file
				};
				files = files;
			}
		} catch (e) {
			// Remove the failed doc from the files array
			files = files.filter((f) => f.name !== url);
			toast.error(`${e}`);
		}
	};

	//////////////////////////
	// Web functions
	//////////////////////////

const initNewChat = async () => {

		const availableModels = $models
			.filter((m) => !(m?.info?.meta?.hidden ?? false))
			.map((m) => m.id);

		if ($page.url.searchParams.get('models') || $page.url.searchParams.get('model')) {
			const urlModels = (
				$page.url.searchParams.get('models') ||
				$page.url.searchParams.get('model') ||
				''
			)?.split(',');

			if (urlModels.length === 1) {
				const m = $models.find((m) => m.id === urlModels[0]);
				if (!m) {
					const modelSelectorButton = document.getElementById('model-selector-0-button');
					if (modelSelectorButton) {
						modelSelectorButton.click();
						await tick();

						const modelSelectorInput = document.getElementById('model-search-input');
						if (modelSelectorInput) {
							modelSelectorInput.focus();
							modelSelectorInput.value = urlModels[0];
							modelSelectorInput.dispatchEvent(new Event('input'));
						}
					}
				} else {
					selectedModels = urlModels;
				}
			} else {
				selectedModels = urlModels;
			}

			selectedModels = selectedModels.filter((modelId) =>
				$models.map((m) => m.id).includes(modelId)
			);
		} else {
			// Always reset to preferred default on refresh/new chat
			// Prefer 'gpt-5-2025-08-07' when present, otherwise use server defaults
			const preferredModelId = 'gpt-5-2025-08-07';
			if (availableModels.includes(preferredModelId)) {
				selectedModels = [preferredModelId];
			} else if ($config?.default_models) {
				// Fallback to server-configured defaults
				selectedModels = $config?.default_models.split(',');
			}
			selectedModels = selectedModels.filter((modelId) => availableModels.includes(modelId));
		}

		if (selectedModels.length === 0 || (selectedModels.length === 1 && selectedModels[0] === '')) {
			if (availableModels.length > 0) {
				selectedModels = [availableModels[0]];
			} else {
				selectedModels = [''];
			}
		}

		await showControls.set(false);
		await showCallOverlay.set(false);
		await showOverview.set(false);
		await showArtifacts.set(false);

		if ($page.url.pathname.includes('/c/')) {
			window.history.replaceState(history.state, '', `/`);
		}

		autoScroll = true;

		resetInput();
		await chatId.set('');
		await chatTitle.set('');

		history = {
			messages: {},
			currentId: null
		};

		chatFiles = [];
		params = {};
		
		// Reset selection mode tracking for new chat
		lastAssistantPanelSwitchId = null;
		userDismissedSelectionMode = false;
		isInitialChatLoad = true;
		currentChatId = '';

		if ($page.url.searchParams.get('youtube')) {
			uploadYoutubeTranscription(
				`https://www.youtube.com/watch?v=${$page.url.searchParams.get('youtube')}`
			);
		}

		if ($page.url.searchParams.get('load-url')) {
			await uploadWeb($page.url.searchParams.get('load-url'));
		}

		if ($page.url.searchParams.get('web-search') === 'true') {
			webSearchEnabled = true;
		}

		if ($page.url.searchParams.get('image-generation') === 'true') {
			imageGenerationEnabled = true;
		}

		if ($page.url.searchParams.get('code-interpreter') === 'true') {
			codeInterpreterEnabled = true;
		}

		if ($page.url.searchParams.get('tools')) {
			selectedToolIds = $page.url.searchParams
				.get('tools')
				?.split(',')
				.map((id) => id.trim())
				.filter((id) => id);
		} else if ($page.url.searchParams.get('tool-ids')) {
			selectedToolIds = $page.url.searchParams
				.get('tool-ids')
				?.split(',')
				.map((id) => id.trim())
				.filter((id) => id);
		}

		if ($page.url.searchParams.get('call') === 'true') {
			showCallOverlay.set(true);
			showControls.set(true);
		}

		if ($page.url.searchParams.get('q')) {
			prompt = $page.url.searchParams.get('q') ?? '';

			if (prompt) {
				await tick();
				submitPrompt(prompt);
			}
		}

		selectedModels = selectedModels.map((modelId) =>
			$models.map((m) => m.id).includes(modelId) ? modelId : ''
		);

		const userSettings = await getUserSettings(localStorage.token);

		if (userSettings) {
			settings.set(userSettings.ui);
		} else {
			settings.set(JSON.parse(localStorage.getItem('settings') ?? '{}'));
		}

		const chatInput = document.getElementById('chat-input');
		setTimeout(() => chatInput?.focus(), 0);
	};

	const loadChat = async () => {
		chatId.set(chatIdProp);

		if ($temporaryChatEnabled) {
			temporaryChatEnabled.set(false);
		}

		chat = await getChatById(localStorage.token, $chatId).catch(async (error) => {
			await goto('/');
			return null;
		});

		if (chat) {
			tags = await getTagsById(localStorage.token, $chatId).catch(async (error) => {
				return [];
			});

			const chatContent = chat.chat;

			if (chatContent) {
				console.log(chatContent);

				selectedModels =
					(chatContent?.models ?? undefined) !== undefined
						? chatContent.models
						: [chatContent.models ?? ''];

				if (!($user?.role === 'admin' || ($user?.permissions?.chat?.multiple_models ?? true))) {
					selectedModels = selectedModels.length > 0 ? [selectedModels[0]] : [''];
				}

				oldSelectedModelIds = selectedModels;

				history =
					(chatContent?.history ?? undefined) !== undefined
						? chatContent.history
						: convertMessagesToHistory(chatContent.messages);

				chatTitle.set(chatContent.title);

				const userSettings = await getUserSettings(localStorage.token);

				if (userSettings) {
					await settings.set(userSettings.ui);
				} else {
					await settings.set(JSON.parse(localStorage.getItem('settings') ?? '{}'));
				}

				params = chatContent?.params ?? {};
				chatFiles = chatContent?.files ?? [];

				autoScroll = true;
				await tick();

				// Restore saved selections for this chat
				try {
					const persisted = JSON.parse(localStorage.getItem('saved-selections') ?? '{}');
					const items = persisted[$chatId] ?? [];
					if (items.length > 0) {
						savedSelections.set(items);
					}
				} catch {}

                // Do not flip messages to done on hydration; keep original flags to avoid
                // triggering selection logic on reload

				const taskRes = await getTaskIdsByChatId(localStorage.token, $chatId).catch((error) => {
					return null;
				});

				if (taskRes) {
					taskIds = taskRes.task_ids;
				}

				await tick();

				return true;
			} else {
				return null;
			}
		}
	};

	const scrollToBottom = async (behavior = 'auto') => {
		await tick();
		if (messagesContainerElement) {
			messagesContainerElement.scrollTo({
				top: messagesContainerElement.scrollHeight,
				behavior
			});
		}
	};
	const chatCompletedHandler = async (chatId, modelId, responseMessageId, messages) => {
		// Check if socket is ready
		if (!socketReady) {
			console.warn('Socket not ready for chat completion');
			return;
		}

		const res = await chatCompleted(localStorage.token, {
			model: modelId,
			messages: messages.map((m) => ({
				id: m.id,
				role: m.role,
				content: m.content,
				info: m.info ? m.info : undefined,
				timestamp: m.timestamp,
				...(m.usage ? { usage: m.usage } : {}),
				...(m.sources ? { sources: m.sources } : {})
			})),
			filter_ids: selectedFilterIds.length > 0 ? selectedFilterIds : undefined,
			model_item: $models.find((m) => m.id === modelId),
			chat_id: chatId,
			session_id: $socket?.id,
			id: responseMessageId
		}).catch((error) => {
			toast.error(`${error}`);
			messages.at(-1).error = { content: error };

			return null;
		});

		if (res !== null && res.messages) {
			// Update chat history with the new messages
			for (const message of res.messages) {
				if (message?.id) {
					// Add null check for message and message.id
					history.messages[message.id] = {
						...history.messages[message.id],
						...(history.messages[message.id].content !== message.content
							? { originalContent: history.messages[message.id].content }
							: {}),
						...message
					};
				}
			}
		}

		await tick();

		if ($chatId == chatId) {
			if (!$temporaryChatEnabled) {
				chat = await updateChatById(localStorage.token, chatId, {
					models: selectedModels,
					messages: messages,
					history: history,
					params: params,
					files: chatFiles
				});

				currentChatPage.set(1);
				await chats.set(await getChatList(localStorage.token, $currentChatPage));
			}
		}

		taskIds = null;
	};

	const chatActionHandler = async (chatId, actionId, modelId, responseMessageId, event = null) => {
		// Check if socket is ready
		if (!socketReady) {
			console.warn('Socket not ready for chat action');
			return;
		}

		const messages = createMessagesList(history, responseMessageId);

		const res = await chatAction(localStorage.token, actionId, {
			model: modelId,
			messages: messages.map((m) => ({
				id: m.id,
				role: m.role,
				content: m.content,
				info: m.info ? m.info : undefined,
				timestamp: m.timestamp,
				...(m.sources ? { sources: m.sources } : {})
			})),
			...(event ? { event: event } : {}),
			model_item: $models.find((m) => m.id === modelId),
			chat_id: chatId,
			session_id: $socket?.id,
			id: responseMessageId
		}).catch((error) => {
			toast.error(`${error}`);
			messages.at(-1).error = { content: error };
			return null;
		});

		if (res !== null && res.messages) {
			// Update chat history with the new messages
			for (const message of res.messages) {
				history.messages[message.id] = {
					...history.messages[message.id],
					...(history.messages[message.id].content !== message.content
						? { originalContent: history.messages[message.id].content }
						: {}),
					...message
				};
			}
		}

		if ($chatId == chatId) {
			if (!$temporaryChatEnabled) {
				chat = await updateChatById(localStorage.token, chatId, {
					models: selectedModels,
					messages: messages,
					history: history,
					params: params,
					files: chatFiles
				});

				currentChatPage.set(1);
				await chats.set(await getChatList(localStorage.token, $currentChatPage));
			}
		}
	};

	const getChatEventEmitter = async (modelId: string, chatId: string = '') => {
		return setInterval(() => {
			$socket?.emit('usage', {
				action: 'chat',
				model: modelId,
				chat_id: chatId
			});
		}, 1000);
	};

	const createMessagePair = async (userPrompt) => {
		prompt = '';
		if (selectedModels.length === 0) {
			toast.error($i18n.t('Model not selected'));
		} else {
			const modelId = selectedModels[0];
			const model = $models.filter((m) => m.id === modelId).at(0);

			const messages = createMessagesList(history, history.currentId);
			const parentMessage = messages.length !== 0 ? messages.at(-1) : null;

			const userMessageId = uuidv4();
			const responseMessageId = uuidv4();

			const userMessage = {
				id: userMessageId,
				parentId: parentMessage ? parentMessage.id : null,
				childrenIds: [responseMessageId],
				role: 'user',
				content: userPrompt ? userPrompt : `[PROMPT] ${userMessageId}`,
				timestamp: Math.floor(Date.now() / 1000)
			};

			const responseMessage = {
				id: responseMessageId,
				parentId: userMessageId,
				childrenIds: [],
				role: 'assistant',
				content: `[RESPONSE] ${responseMessageId}`,
				done: true,

				model: modelId,
				modelName: model.name ?? model.id,
				modelIdx: 0,
				timestamp: Math.floor(Date.now() / 1000)
			};

			if (parentMessage) {
				parentMessage.childrenIds.push(userMessageId);
				history.messages[parentMessage.id] = parentMessage;
			}
			history.messages[userMessageId] = userMessage;
			history.messages[responseMessageId] = responseMessage;

			history.currentId = responseMessageId;

			await tick();

			if (autoScroll) {
				scrollToBottom();
			}

			if (messages.length === 0) {
				await initChatHandler(history);
			} else {
				await saveChatHandler($chatId, history);
			}
		}
	};

	const addMessages = async ({ modelId, parentId, messages }) => {
		const model = $models.filter((m) => m.id === modelId).at(0);

		let parentMessage = history.messages[parentId];
		let currentParentId = parentMessage ? parentMessage.id : null;
		for (const message of messages) {
			let messageId = uuidv4();

			if (message.role === 'user') {
				const userMessage = {
					id: messageId,
					parentId: currentParentId,
					childrenIds: [],
					timestamp: Math.floor(Date.now() / 1000),
					...message
				};

				if (parentMessage) {
					parentMessage.childrenIds.push(messageId);
					history.messages[parentMessage.id] = parentMessage;
				}

				history.messages[messageId] = userMessage;
				parentMessage = userMessage;
				currentParentId = messageId;
			} else {
				const responseMessage = {
					id: messageId,
					parentId: currentParentId,
					childrenIds: [],
					done: true,
					model: model.id,
					modelName: model.name ?? model.id,
					modelIdx: 0,
					timestamp: Math.floor(Date.now() / 1000),
					...message
				};

				if (parentMessage) {
					parentMessage.childrenIds.push(messageId);
					history.messages[parentMessage.id] = parentMessage;
				}

				history.messages[messageId] = responseMessage;
				parentMessage = responseMessage;
				currentParentId = messageId;
			}
		}

		history.currentId = currentParentId;
		await tick();

		if (autoScroll) {
			scrollToBottom();
		}

		if (messages.length === 0) {
			await initChatHandler(history);
		} else {
			await saveChatHandler($chatId, history);
		}
	};

	const chatCompletionEventHandler = async (data, message, chatId) => {
		const { id, done, choices, content, sources, selected_model_id, error, usage } = data;

		if (error) {
			await handleOpenAIError(error, message);
		}

		if (sources) {
			message.sources = sources;
		}

		if (choices) {
			if (choices[0]?.message?.content) {
				// Non-stream response
				message.content += choices[0]?.message?.content;
			} else {
				// Stream response
				let value = choices[0]?.delta?.content ?? '';
				if (message.content == '' && value == '\n') {
					console.log('Empty response');
				} else {
					message.content += value;

					if (navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
						navigator.vibrate(5);
					}

					// Emit chat event for TTS
					const messageContentParts = getMessageContentParts(
						removeAllDetails(message.content),
						$config?.audio?.tts?.split_on ?? 'punctuation'
					);
					messageContentParts.pop();

					// dispatch only last sentence and make sure it hasn't been dispatched before
					if (
						messageContentParts.length > 0 &&
						messageContentParts[messageContentParts.length - 1] !== message.lastSentence
					) {
						message.lastSentence = messageContentParts[messageContentParts.length - 1];
						eventTarget.dispatchEvent(
							new CustomEvent('chat', {
								detail: {
									id: message.id,
									content: messageContentParts[messageContentParts.length - 1]
								}
							})
						);
					}
				}
			}
		}

		if (content) {
			// REALTIME_CHAT_SAVE is disabled
			message.content = content;

			if (navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
				navigator.vibrate(5);
			}

			// Emit chat event for TTS
			const messageContentParts = getMessageContentParts(
				removeAllDetails(message.content),
				$config?.audio?.tts?.split_on ?? 'punctuation'
			);
			messageContentParts.pop();

			// dispatch only last sentence and make sure it hasn't been dispatched before
			if (
				messageContentParts.length > 0 &&
				messageContentParts[messageContentParts.length - 1] !== message.lastSentence
			) {
				message.lastSentence = messageContentParts[messageContentParts.length - 1];
				eventTarget.dispatchEvent(
					new CustomEvent('chat', {
						detail: {
							id: message.id,
							content: messageContentParts[messageContentParts.length - 1]
						}
					})
				);
			}
		}

		if (selected_model_id) {
			message.selectedModelId = selected_model_id;
			message.arena = true;
		}

		if (usage) {
			message.usage = usage;
		}

		history.messages[message.id] = message;

		if (done) {
			message.done = true;
                    // Live completion finished: auto-enter selection
                    if (message.role === 'assistant') {
                        maybeAutoEnterSelectionOnResponseDone(message.id);
                    }

			if ($settings.responseAutoCopy) {
				copyToClipboard(message.content);
			}

			if ($settings.responseAutoPlayback && !$showCallOverlay) {
				await tick();
				document.getElementById(`speak-button-${message.id}`)?.click();
			}

			// Emit chat event for TTS
			let lastMessageContentPart =
				getMessageContentParts(
					removeAllDetails(message.content),
					$config?.audio?.tts?.split_on ?? 'punctuation'
				)?.at(-1) ?? '';
			if (lastMessageContentPart) {
				eventTarget.dispatchEvent(
					new CustomEvent('chat', {
						detail: { id: message.id, content: lastMessageContentPart }
					})
				);
			}
			eventTarget.dispatchEvent(
				new CustomEvent('chat:finish', {
					detail: {
						id: message.id,
						content: message.content
					}
				})
			);

			history.messages[message.id] = message;
			await chatCompletedHandler(
				chatId,
				message.model,
				message.id,
				createMessagesList(history, message.id)
			);
		}

		console.log(data);
		if (autoScroll) {
			scrollToBottom();
		}
	};

	//////////////////////////
	// Chat functions
	//////////////////////////

	const submitPrompt = async (userPrompt, { _raw = false } = {}) => {
		console.log('submitPrompt', userPrompt, $chatId);

		const messages = createMessagesList(history, history.currentId);
		const _selectedModels = selectedModels.map((modelId) =>
			$models.map((m) => m.id).includes(modelId) ? modelId : ''
		);
		if (JSON.stringify(selectedModels) !== JSON.stringify(_selectedModels)) {
			selectedModels = _selectedModels;
		}

		if (userPrompt === '' && files.length === 0) {
			toast.error($i18n.t('Please enter a prompt'));
			return;
		}
		if (selectedModels.includes('')) {
			toast.error($i18n.t('Model not selected'));
			return;
		}

		if (messages.length != 0 && messages.at(-1).done != true) {
			// Response not done
			return;
		}
		if (messages.length != 0 && messages.at(-1).error && !messages.at(-1).content) {
			// Error in response
			toast.error($i18n.t(`Oops! There was an error in the previous response.`));
			return;
		}
		if (
			files.length > 0 &&
			files.filter((file) => file.type !== 'image' && file.status === 'uploading').length > 0
		) {
			toast.error(
				$i18n.t(`Oops! There are files still uploading. Please wait for the upload to complete.`)
			);
			return;
		}
		if (
			($config?.file?.max_count ?? null) !== null &&
			files.length + chatFiles.length > $config?.file?.max_count
		) {
			toast.error(
				$i18n.t(`You can only chat with a maximum of {{maxCount}} file(s) at a time.`, {
					maxCount: $config?.file?.max_count
				})
			);
			return;
		}

		prompt = '';

		// Reset chat input textarea
		if (!($settings?.richTextInput ?? true)) {
			const chatInputElement = document.getElementById('chat-input');

			if (chatInputElement) {
				await tick();
				chatInputElement.style.height = '';
			}
		}

		const _files = JSON.parse(JSON.stringify(files));
		chatFiles.push(..._files.filter((item) => ['doc', 'file', 'collection'].includes(item.type)));
		chatFiles = chatFiles.filter(
			// Remove duplicates
			(item, index, array) =>
				array.findIndex((i) => JSON.stringify(i) === JSON.stringify(item)) === index
		);

		files = [];
		prompt = '';

		// Create user message
		let userMessageId = uuidv4();
		let userMessage = {
			id: userMessageId,
			parentId: messages.length !== 0 ? messages.at(-1).id : null,
			childrenIds: [],
			role: 'user',
			content: userPrompt,
			files: _files.length > 0 ? _files : undefined,
			timestamp: Math.floor(Date.now() / 1000), // Unix epoch
			models: selectedModels
		};

		// Add message to history and Set currentId to messageId
		history.messages[userMessageId] = userMessage;
		history.currentId = userMessageId;

		// Append messageId to childrenIds of parent message
		if (messages.length !== 0) {
			history.messages[messages.at(-1).id].childrenIds.push(userMessageId);
		}

		// focus on chat input
		const chatInput = document.getElementById('chat-input');
		chatInput?.focus();

		saveSessionSelectedModels();

		await sendPrompt(history, userPrompt, userMessageId, { newChat: true });
	};

	const sendPrompt = async (
		_history,
		prompt: string,
		parentId: string,
		{ modelId = null, modelIdx = null, newChat = false } = {}
	) => {
		if (autoScroll) {
			scrollToBottom();
		}

		let _chatId = JSON.parse(JSON.stringify($chatId));
		_history = JSON.parse(JSON.stringify(_history));

		const responseMessageIds: Record<PropertyKey, string> = {};
		// If modelId is provided, use it, else use selected model
		let selectedModelIds = modelId
			? [modelId]
			: atSelectedModel !== undefined
				? [atSelectedModel.id]
				: selectedModels;

		// Create response messages for each selected model
		for (const [_modelIdx, modelId] of selectedModelIds.entries()) {
			const model = $models.filter((m) => m.id === modelId).at(0);

			if (model) {
				let responseMessageId = uuidv4();
				let responseMessage = {
					parentId: parentId,
					id: responseMessageId,
					childrenIds: [],
					role: 'assistant',
					content: '',
					model: model.id,
					modelName: model.name ?? model.id,
					modelIdx: modelIdx ? modelIdx : _modelIdx,
					timestamp: Math.floor(Date.now() / 1000) // Unix epoch
				};

				// Add message to history and Set currentId to messageId
				history.messages[responseMessageId] = responseMessage;
				history.currentId = responseMessageId;

				// Append messageId to childrenIds of parent message
				if (parentId !== null && history.messages[parentId]) {
					// Add null check before accessing childrenIds
					history.messages[parentId].childrenIds = [
						...history.messages[parentId].childrenIds,
						responseMessageId
					];
				}

				responseMessageIds[`${modelId}-${modelIdx ? modelIdx : _modelIdx}`] = responseMessageId;
			}
		}
		history = history;

		// Create new chat if newChat is true and first user message
		if (newChat && _history.messages[_history.currentId].parentId === null) {
			_chatId = await initChatHandler(_history);
		}

		await tick();

		_history = JSON.parse(JSON.stringify(history));
		// Save chat after all messages have been created
		await saveChatHandler(_chatId, _history);

		await Promise.all(
			selectedModelIds.map(async (modelId, _modelIdx) => {
				console.log('modelId', modelId);
				const model = $models.filter((m) => m.id === modelId).at(0);

				if (model) {
					const messages = createMessagesList(_history, parentId);
					// If there are image files, check if model is vision capable
					const hasImages = messages.some((message) =>
						message.files?.some((file) => file.type === 'image')
					);

					if (hasImages && !(model.info?.meta?.capabilities?.vision ?? true)) {
						toast.error(
							$i18n.t('Model {{modelName}} is not vision capable', {
								modelName: model.name ?? model.id
							})
						);
					}

					let responseMessageId =
						responseMessageIds[`${modelId}-${modelIdx ? modelIdx : _modelIdx}`];
					const chatEventEmitter = await getChatEventEmitter(model.id, _chatId);

					scrollToBottom();
					await sendPromptSocket(_history, model, responseMessageId, _chatId);

					if (chatEventEmitter) clearInterval(chatEventEmitter);
				} else {
					toast.error($i18n.t(`Model {{modelId}} not found`, { modelId }));
				}
			})
		);

		currentChatPage.set(1);
		chats.set(await getChatList(localStorage.token, $currentChatPage));
	};

	const sendPromptSocket = async (_history, model, responseMessageId, _chatId) => {
		// Check if socket is ready with retry mechanism
		// Check if socket is ready
		if (!socketReady) {
			// Simple retry with shorter delay
			let retryCount = 0;
			const maxRetries = 3;
			const retryDelay = 500;
			
			while (!socketReady && retryCount < maxRetries) {
				console.log(`Socket not ready, retrying... (${retryCount + 1}/${maxRetries})`);
				await new Promise(resolve => setTimeout(resolve, retryDelay));
				retryCount++;
			}
			
			if (!socketReady) {
				toast.error($i18n.t('Socket not ready. Please wait a moment and try again.'));
				return;
			}
		}

		// Debug: Check socket connection status
		console.log('Socket connection status:', {
			socket: $socket,
			socketId: $socket?.id,
			socketConnected: $socket?.connected,
			user: $user
		});

		// Check if socket is connected
		if (!$socket || !$socket.connected) {
			toast.error('Socket not connected. Please refresh the page and try again.');
			return;
		}

		// Check if session ID is available
		if (!$socket.id) {
			toast.error('Session ID not available. Please refresh the page and try again.');
			return;
		}

		// Ensure user is authenticated
		if (!$user) {
			toast.error('User not authenticated. Please refresh the page and try again.');
			return;
		}

		const chatMessages = createMessagesList(history, history.currentId);
		const responseMessage = _history.messages[responseMessageId];
		const userMessage = _history.messages[responseMessage.parentId];

		const chatMessageFiles = chatMessages
			.filter((message) => message.files)
			.flatMap((message) => message.files);

		// Filter chatFiles to only include files that are in the chatMessageFiles
		chatFiles = chatFiles.filter((item) => {
			const fileExists = chatMessageFiles.some((messageFile) => messageFile.id === item.id);
			return fileExists;
		});

		let files = JSON.parse(JSON.stringify(chatFiles));
		files.push(
			...(userMessage?.files ?? []).filter((item) =>
				['doc', 'file', 'collection'].includes(item.type)
			),
			...(responseMessage?.files ?? []).filter((item) => ['web_search_results'].includes(item.type))
		);
		// Remove duplicates
		files = files.filter(
			(item, index, array) =>
				array.findIndex((i) => JSON.stringify(i) === JSON.stringify(item)) === index
		);

		scrollToBottom();
		eventTarget.dispatchEvent(
			new CustomEvent('chat:start', {
				detail: {
					id: responseMessageId
				}
			})
		);
		await tick();

		const stream =
			model?.info?.params?.stream_response ??
			$settings?.params?.stream_response ??
			params?.stream_response ??
			true;

		// 获取当前选中的personal
		const selectedPersonalId = localStorage.getItem('selectedPersonalId');
		let personalPrefix = '';
		let personalInfo = null;
		if (selectedPersonalId) {
			const personals = JSON.parse(localStorage.getItem('personals') || '[]');
			const currentPersonal = personals.find(p => p.id === selectedPersonalId);
			if (currentPersonal) {
				personalPrefix = currentPersonal.prefix;
				personalInfo = currentPersonal;
			}
		}

		// 构建system message，包含personal前缀
		let systemMessage = '';
		if (params?.system || $settings.system) {
			systemMessage = promptTemplate(
				params?.system ?? $settings?.system ?? '',
				$user?.name,
				$settings?.userLocation
					? await getAndUpdateUserLocation(localStorage.token).catch((err) => {
							console.error(err);
							return undefined;
						})
					: undefined
			);
		}
		
		// 如果有personal信息，添加到system message
		if (personalInfo) {
			// 根据头像emoji和名字分析角色类型
			const avatar = personalInfo.avatar;
			const name = personalInfo.name.toLowerCase();
			
			// 角色类型特定的指导
			let characterSpecificGuidance = '';
			
			if (avatar === '🐱' || name.includes('cat') || name.includes('kitty')) {
				characterSpecificGuidance = 'You are a cute, playful cat. Use cat-like expressions, be affectionate, and show curiosity. You might mention things cats love like toys, sunbeams, or treats.';
			} else if (avatar === '🐶' || name.includes('dog') || name.includes('puppy')) {
				characterSpecificGuidance = 'You are a friendly, loyal dog. Be enthusiastic, protective, and loving. You might mention things dogs love like walks, treats, or playing fetch.';
			} else if (avatar === '🦄' || name.includes('unicorn') || name.includes('magic')) {
				characterSpecificGuidance = 'You are a magical unicorn. Be mystical, graceful, and kind. You might mention magic, rainbows, sparkles, and helping others with your magical powers.';
			} else if (avatar === '🐼' || name.includes('panda')) {
				characterSpecificGuidance = 'You are a gentle, peaceful panda. Be calm, wise, and love bamboo. You might mention eating bamboo, being peaceful, or taking naps.';
			} else if (avatar === '🦁' || name.includes('lion')) {
				characterSpecificGuidance = 'You are a brave, strong lion. Be courageous, protective, and a natural leader. You might mention protecting your friends, being brave, or leading others.';
			} else if (avatar === '🐯' || name.includes('tiger')) {
				characterSpecificGuidance = 'You are a powerful, fierce tiger. Be strong, confident, and protective. You might mention your strength, stripes, or protecting others.';
			} else if (avatar === '🐸' || name.includes('frog')) {
				characterSpecificGuidance = 'You are a friendly frog. Be cheerful, love water, and enjoy jumping around. You might mention ponds, jumping, or making friends with other animals.';
			} else if (avatar === '🌟' || name.includes('star')) {
				characterSpecificGuidance = 'You are a bright, shining star. Be positive, inspiring, and bring light to others. You might mention twinkling, making wishes come true, or brightening the night sky.';
			} else if (avatar === '🌈' || name.includes('rainbow')) {
				characterSpecificGuidance = 'You are a colorful rainbow. Be joyful, bring happiness, and represent diversity. You might mention colors, bringing joy, or appearing after rain.';
			} else if (avatar === '🚀' || name.includes('rocket') || name.includes('space')) {
				characterSpecificGuidance = 'You are an adventurous rocket. Be excited about space exploration, be fast, and love adventure. You might mention space, planets, stars, or going on exciting missions.';
			} else if (avatar === '🏰' || name.includes('castle') || name.includes('prince') || name.includes('princess')) {
				characterSpecificGuidance = 'You are a noble castle resident. Be dignified, kind, and protective of your kingdom. You might mention your castle, helping people, or being noble and kind.';
			} else if (avatar === '🎮' || name.includes('game')) {
				characterSpecificGuidance = 'You are a fun gaming character. Be energetic, love games, and be excited about adventures. You might mention games, levels, achievements, or having fun.';
			} else {
				characterSpecificGuidance = 'Be friendly, helpful, and match your character\'s personality based on your name and avatar.';
			}
			
			const characterPrompt = `You are ${personalInfo.name}${personalInfo.avatar ? ` (${personalInfo.avatar})` : ''}. 

IMPORTANT: You are NOT talking about this character - you ARE this character. Respond as if you are actually ${personalInfo.name} speaking directly to the child.

Your signature greeting is "${personalInfo.prefix}". You should use this when it feels natural, like at the start of a conversation, but **do not repeat it in every single response**.

${personalInfo.description ? `Character traits: ${personalInfo.description}` : ''}

${characterSpecificGuidance}

Key guidelines:
- **Helpful Core**: Your primary goal is to be a helpful assistant. You MUST answer the user's questions factually, even if the topic is outside your character's world (like math, history, or science). Deliver the correct answer first, then add your character's personality.
- **Never Refuse**: Do not use your character as an excuse to avoid answering a question (e.g., "As a Pokemon, I don't know about politics").
- **Multilingual Support**: Respond primarily in the user's language. However, your character's signature sounds (like your greeting) are universal. Always integrate these sounds naturally into your responses, no matter the language.
- Always respond in first person as ${personalInfo.name}.
- Use your signature greeting "${personalInfo.prefix}" appropriately, and **avoid repeating it in every message**.
- Match your personality to your avatar emoji and name.
- Be consistent with your character's voice and mannerisms.
- Never break character or explain that you're role-playing.
- Respond as if you're really ${personalInfo.name} talking to a child.`;
			
			if (systemMessage) {
				systemMessage += `\n\n${characterPrompt}`;
			} else {
				systemMessage = characterPrompt;
			}
		}

		let messages = [
			systemMessage
				? {
						role: 'system',
						content: systemMessage
					}
				: undefined,
			...createMessagesList(_history, responseMessageId).map((message) => ({
				...message,
				content: processDetails(message.content)
			}))
		].filter((message) => message);

		messages = messages
			.map((message, idx, arr) => ({
				role: message.role,
				...((message.files?.filter((file) => file.type === 'image').length > 0 ?? false) &&
				message.role === 'user'
					? {
							content: [
								{
									type: 'text',
									text: message?.merged?.content ?? message.content
								},
								...message.files
									.filter((file) => file.type === 'image')
									.map((file) => ({
										type: 'image_url',
										image_url: {
											url: file.url
										}
									}))
							]
						}
					: {
							content: message?.merged?.content ?? message.content
						})
			}))
			.filter((message) => message?.role === 'user' || message?.content?.trim());

		const res = await generateOpenAIChatCompletion(
			localStorage.token,
			{
				stream: stream,
				model: model.id,
				messages: messages,
				params: {
					...$settings?.params,
					...params,
					stop:
						(params?.stop ?? $settings?.params?.stop ?? undefined)
							? (params?.stop.split(',').map((token) => token.trim()) ?? $settings.params.stop).map(
									(str) => decodeURIComponent(JSON.parse('"' + str.replace(/\"/g, '\\"') + '"'))
								)
							: undefined
				},

				files: (files?.length ?? 0) > 0 ? files : undefined,

				filter_ids: selectedFilterIds.length > 0 ? selectedFilterIds : undefined,
				tool_ids: selectedToolIds.length > 0 ? selectedToolIds : undefined,
				tool_servers: $toolServers,

				features: {
					image_generation:
						$config?.features?.enable_image_generation &&
						($user?.role === 'admin' || $user?.permissions?.features?.image_generation)
							? imageGenerationEnabled
							: false,
					code_interpreter:
						$config?.features?.enable_code_interpreter &&
						($user?.role === 'admin' || $user?.permissions?.features?.code_interpreter)
							? codeInterpreterEnabled
							: false,
					web_search:
						$config?.features?.enable_web_search &&
						($user?.role === 'admin' || $user?.permissions?.features?.web_search)
							? webSearchEnabled || ($settings?.webSearch ?? false) === 'always'
							: false,
					memory: $settings?.memory ?? false
				},
				variables: {
					...getPromptVariables(
						$user?.name,
						$settings?.userLocation
							? await getAndUpdateUserLocation(localStorage.token).catch((err) => {
									console.error(err);
									return undefined;
								})
							: undefined
					)
				},
				model_item: $models.find((m) => m.id === model.id),

				session_id: $socket?.id,
				chat_id: $chatId,
				id: responseMessageId,

				background_tasks: {
					...(!$temporaryChatEnabled &&
					(messages.length == 1 ||
						(messages.length == 2 &&
							messages.at(0)?.role === 'system' &&
							messages.at(1)?.role === 'user')) &&
					(selectedModels[0] === model.id || atSelectedModel !== undefined)
						? {
								title_generation: $settings?.title?.auto ?? true,
								tags_generation: $settings?.autoTags ?? true
							}
						: {}),
					follow_up_generation: $settings?.autoFollowUps ?? true
				},

				...(stream && (model.info?.meta?.capabilities?.usage ?? false)
					? {
							stream_options: {
								include_usage: true
							}
						}
					: {})
			},
			`${WEBUI_BASE_URL}/api`
		).catch(async (error) => {
			toast.error(`${error}`);

			responseMessage.error = {
				content: error
			};
			responseMessage.done = true;
            // Error path still represents a finished assistant message
            if (responseMessage.role === 'assistant') {
                maybeAutoEnterSelectionOnResponseDone(responseMessageId);
            }

			history.messages[responseMessageId] = responseMessage;
			history.currentId = responseMessageId;

			return null;
		});

		// Debug: Log the model being sent
		console.log('Frontend sending model ID:', model.id);
		console.log('Frontend selectedModels:', selectedModels);
		console.log('Frontend atSelectedModel:', atSelectedModel);
		console.log('Frontend model object:', model);

		if (res) {
			if (res.error) {
				await handleOpenAIError(res.error, responseMessage);
			} else {
				if (taskIds) {
					taskIds.push(res.task_id);
				} else {
					taskIds = [res.task_id];
				}
			}
		}

		await tick();
		scrollToBottom();
	};

	const handleOpenAIError = async (error, responseMessage) => {
		let errorMessage = '';
		let innerError;

		if (error) {
			innerError = error;
		}

		console.error(innerError);
		if ('detail' in innerError) {
			// FastAPI error
			toast.error(innerError.detail);
			errorMessage = innerError.detail;
		} else if ('error' in innerError) {
			// OpenAI error
			if ('message' in innerError.error) {
				toast.error(innerError.error.message);
				errorMessage = innerError.error.message;
			} else {
				toast.error(innerError.error);
				errorMessage = innerError.error;
			}
		} else if ('message' in innerError) {
			// OpenAI error
			toast.error(innerError.message);
			errorMessage = innerError.message;
		}

		responseMessage.error = {
			content: $i18n.t(`Uh-oh! There was an issue with the response.`) + '\n' + errorMessage
		};
		responseMessage.done = true;
        if (responseMessage.role === 'assistant') {
            maybeAutoEnterSelectionOnResponseDone(responseMessageId);
        }

		if (responseMessage.statusHistory) {
			responseMessage.statusHistory = responseMessage.statusHistory.filter(
				(status) => status.action !== 'knowledge_search'
			);
		}

		history.messages[responseMessageId] = responseMessage;
	};

	const stopResponse = async () => {
		if (taskIds) {
			for (const taskId of taskIds) {
				const res = await stopTask(localStorage.token, taskId).catch((error) => {
					toast.error(`${error}`);
					return null;
				});
			}

			taskIds = null;

			const responseMessage = history.messages[history.currentId];
			// Set all response messages to done
			for (const messageId of history.messages[responseMessage.parentId].childrenIds) {
				history.messages[messageId].done = true;
                const msg = history.messages[messageId];
                if (msg?.role === 'assistant') {
                    maybeAutoEnterSelectionOnResponseDone(messageId);
                }
			}

			history.messages[history.currentId] = responseMessage;

			if (autoScroll) {
				scrollToBottom();
			}
		}
	};

	const submitMessage = async (parentId, prompt) => {
		let userPrompt = prompt;
		let userMessageId = uuidv4();

		let userMessage = {
			id: userMessageId,
			parentId: parentId,
			childrenIds: [],
			role: 'user',
			content: userPrompt,
			models: selectedModels,
			timestamp: Math.floor(Date.now() / 1000) // Unix epoch
		};

		if (parentId !== null) {
			history.messages[parentId].childrenIds = [
				...history.messages[parentId].childrenIds,
				userMessageId
			];
		}

		history.messages[userMessageId] = userMessage;
		history.currentId = userMessageId;

		await tick();

		if (autoScroll) {
			scrollToBottom();
		}

		await sendPrompt(history, userPrompt, userMessageId);
	};

	const regenerateResponse = async (message) => {
		console.log('regenerateResponse');

		if (history.currentId) {
			let userMessage = history.messages[message.parentId];
			let userPrompt = userMessage.content;

			if (autoScroll) {
				scrollToBottom();
			}

			if ((userMessage?.models ?? [...selectedModels]).length == 1) {
				// If user message has only one model selected, sendPrompt automatically selects it for regeneration
				await sendPrompt(history, userPrompt, userMessage.id);
			} else {
				// If there are multiple models selected, use the model of the response message for regeneration
				// e.g. many model chat
				await sendPrompt(history, userPrompt, userMessage.id, {
					modelId: message.model,
					modelIdx: message.modelIdx
				});
			}
		}
	};

	const continueResponse = async () => {
		console.log('continueResponse');
		const _chatId = JSON.parse(JSON.stringify($chatId));

		if (history.currentId && history.messages[history.currentId].done == true) {
			const responseMessage = history.messages[history.currentId];
			responseMessage.done = false;
			await tick();

			const model = $models
				.filter((m) => m.id === (responseMessage?.selectedModelId ?? responseMessage.model))
				.at(0);

			if (model) {
				await sendPromptSocket(history, model, responseMessage.id, _chatId);
			}
		}
	};

	const mergeResponses = async (messageId, responses, _chatId) => {
		console.log('mergeResponses', messageId, responses);
		const message = history.messages[messageId];
		const mergedResponse = {
			status: true,
			content: ''
		};
		message.merged = mergedResponse;
		history.messages[messageId] = message;

		try {
			const [res, controller] = await generateMoACompletion(
				localStorage.token,
				message.model,
				history.messages[message.parentId].content,
				responses
			);

			if (res && res.ok && res.body) {
				const textStream = await createOpenAITextStream(res.body, $settings.splitLargeChunks);
				for await (const update of textStream) {
					const { value, done, sources, error, usage } = update;
					if (error || done) {
						break;
					}

					if (mergedResponse.content == '' && value == '\n') {
						continue;
					} else {
						mergedResponse.content += value;
						history.messages[messageId] = message;
					}

					if (autoScroll) {
						scrollToBottom();
					}
				}

				await saveChatHandler(_chatId, history);
			} else {
				console.error(res);
			}
		} catch (e) {
			console.error(e);
		}
	};

	const initChatHandler = async (history) => {
		let _chatId = $chatId;

		if (!$temporaryChatEnabled) {
			chat = await createNewChat(localStorage.token, {
				id: _chatId,
				title: $i18n.t('New Chat'),
				models: selectedModels,
				system: $settings.system ?? undefined,
				params: params,
				history: history,
				messages: createMessagesList(history, history.currentId),
				tags: [],
				timestamp: Date.now()
			});

			_chatId = chat.id;
			await chatId.set(_chatId);

			await chats.set(await getChatList(localStorage.token, $currentChatPage));
			currentChatPage.set(1);

			window.history.replaceState(history.state, '', `/c/${_chatId}`);
		} else {
			_chatId = 'local';
			await chatId.set('local');
		}
		await tick();

		return _chatId;
	};

	const saveChatHandler = async (_chatId, history) => {
		if ($chatId == _chatId) {
			if (!$temporaryChatEnabled) {
				chat = await updateChatById(localStorage.token, _chatId, {
					models: selectedModels,
					history: history,
					messages: createMessagesList(history, history.currentId),
					params: params,
					files: chatFiles
				});
				currentChatPage.set(1);
				await chats.set(await getChatList(localStorage.token, $currentChatPage));
			}
		}
	};

	// ====== PARENT MODE: MODERATION FUNCTIONS ======
	function toggleModerationSelection(option: string) {
		// Special handling for Custom option - opens modal
		if (option === 'Custom') {
			showCustomModal = true;
			return;
		}
		
		// Toggle selection for standard options and saved customs
		if (selectedModerations.has(option)) {
			selectedModerations.delete(option);
		} else {
			selectedModerations.add(option);
		}
		selectedModerations = selectedModerations;  // Trigger reactivity
	}
	
	function addCustomInstruction() {
		const trimmed = customInstructionInput.trim();
		if (!trimmed) {
			toast.error('Please enter a custom instruction');
			return;
		}
		
		// Create unique ID for this custom instruction
		const id = `custom_${Date.now()}`;
		
		// Add to custom instructions array
		customInstructions = [...customInstructions, {id, text: trimmed}];
		
		// Don't auto-select - let user explicitly select it by clicking the checkbox
		// This prevents confusion where clicking the checkbox deselects instead of selects
		
		// Close modal and reset input
		showCustomModal = false;
		customInstructionInput = '';
		
		toast.success('Custom instruction added - click it to select');
	}
	
	function removeCustomInstruction(id: string) {
		// Remove from custom instructions array
		customInstructions = customInstructions.filter(c => c.id !== id);
		
		// Remove from selections if it was selected
		selectedModerations.delete(id);
		selectedModerations = selectedModerations;
	}
	
	function cancelCustomModal() {
		showCustomModal = false;
		customInstructionInput = '';
	}

	async function applySelectedModerations(passNumber: 1 | 2 = 1) {
		if (selectedModerations.size === 0) {
			toast.error('Please select at least one moderation strategy');
			return;
		}

		console.log(`Applying moderations (Pass ${passNumber}):`, Array.from(selectedModerations).join(', '));
		moderationLoading = true;
		
		// Determine which pass we're on based on explicit parameter
		const isFirstPass = passNumber === 1;

		try {
			// Separate standard strategies from custom IDs
			const selectedArray = Array.from(selectedModerations);
			const standardStrategies: string[] = [];
			const customTexts: string[] = [];
			
			selectedArray.forEach(selection => {
				if (selection.startsWith('custom_')) {
					const custom = customInstructions.find(c => c.id === selection);
					if (custom) {
						customTexts.push(custom.text);
					}
				} else {
					standardStrategies.push(selection);
				}
			});
			
			// Call moderation with appropriate parameters for current pass
			const result = await applyModeration(
				localStorage.token,
				standardStrategies,
				isFirstPass ? childPrompt1 : childPrompt2,
				customTexts,
				isFirstPass ? originalResponse1 : originalResponse2,  // Pass original response
				isFirstPass ? highlightedTexts1 : highlightedTexts2  // Pass highlighted texts array
			);
			
			if (result) {
				// Store result in appropriate pass
				if (isFirstPass) {
					moderationResult1 = result;
				} else {
					moderationResult2 = result;
				}
				
				const total = standardStrategies.length + customTexts.length;
				toast.success(`Applied ${total} moderation strateg${total === 1 ? 'y' : 'ies'} (Pass ${passNumber})`);
			} else {
				toast.error('Failed to apply moderation');
			}
		} catch (error: any) {
			console.error('Error applying moderation:', error);
			toast.error(`Error: ${error.message || 'Failed to apply moderation'}`);
		} finally {
			moderationLoading = false;
		}
	}

	function clearSelections() {
		selectedModerations.clear();
		customInstructions = [];  // Clear custom instructions too
		selectedModerations = selectedModerations;  // Trigger reactivity
		moderationResult = null;
	}
	
	async function generateFollowUp() {
		if (!moderationResult1) {
			toast.error('Please complete the first moderation pass first');
			return;
		}

		generatingPrompt2 = true;

		try {
			const followup = await generateFollowUpPrompt(
				localStorage.token,
				childPrompt1,
				moderationResult1.refactored_response
			);
			
			childPrompt2 = followup;
			showSecondPass = true;
			conversationStep = 'second';
			
			toast.success('Follow-up question generated!');
			
			// Auto-generate AI response for the follow-up
			await generateFollowUpResponse();
		} catch (error: any) {
			console.error('Error generating follow-up:', error);
			toast.error(`Error: ${error.message || 'Failed to generate follow-up'}`);
		} finally {
			generatingPrompt2 = false;
		}
	}

	async function generateFollowUpResponse() {
		if (!childPrompt2) {
			toast.error('No follow-up prompt to respond to');
			return;
		}

		generatingResponse2 = true;

		try {
			// Use the OpenAI API to generate a response to the follow-up prompt
			// This simulates the child's GPT responding to the follow-up question
			const response = await generateOpenAIChatCompletion(
				localStorage.token,
				{
					model: selectedModels[0] || 'gpt-4o-mini',  // Use selected model or default
					messages: [
						{ role: 'user', content: childPrompt2 }
					],
					stream: false
				}
			);
			
			if (response && response.choices && response.choices[0]) {
				originalResponse2 = response.choices[0].message.content || '';
				toast.success('Follow-up response generated!');
			} else {
				throw new Error('No response content received');
			}
		} catch (error: any) {
			console.error('Error generating follow-up response:', error);
			toast.error(`Error: ${error.message || 'Failed to generate follow-up response'}`);
		} finally {
			generatingResponse2 = false;
		}
	}

	function saveCurrentScenarioState() {
		// Save the current scenario's moderation state for research tracking
		const currentState: ScenarioState = {
			highlightedTexts1: [...highlightedTexts1],
			moderationResult1: moderationResult1,
			highlightedTexts2: [...highlightedTexts2],
			moderationResult2: moderationResult2,
			childPrompt2: childPrompt2,
			originalResponse2: originalResponse2,
			showSecondPass: showSecondPass,
			selectedModerations: new Set(selectedModerations),
			customInstructions: [...customInstructions],
			showOriginal1: showOriginal1,
			showOriginal2: showOriginal2
		};
		
		scenarioStates.set(selectedScenarioIndex, currentState);
	}

	function loadScenario(index: number) {
		// Don't save/load if clicking the same scenario
		if (index === selectedScenarioIndex) {
			return;
		}
		
		// Save current scenario's state before switching
		saveCurrentScenarioState();
		
		// Update selected index
		selectedScenarioIndex = index;
		const [prompt, response] = scenarioList[index];
		
		// Check if this scenario has been worked on before
		const savedState = scenarioStates.get(index);
		
		if (savedState) {
			// Restore previous work on this scenario
			highlightedTexts1 = [...savedState.highlightedTexts1];
			moderationResult1 = savedState.moderationResult1;
			highlightedTexts2 = [...savedState.highlightedTexts2];
			moderationResult2 = savedState.moderationResult2;
			childPrompt2 = savedState.childPrompt2;
			originalResponse2 = savedState.originalResponse2;
			showSecondPass = savedState.showSecondPass;
			selectedModerations = new Set(savedState.selectedModerations);
			customInstructions = [...savedState.customInstructions];
			showOriginal1 = savedState.showOriginal1;
			showOriginal2 = savedState.showOriginal2;
		} else {
			// Fresh scenario - initialize with default state
			highlightedTexts1 = [];
			moderationResult1 = null;
			highlightedTexts2 = [];
			moderationResult2 = null;
			childPrompt2 = '';
			originalResponse2 = '';
			showSecondPass = false;
			selectedModerations = new Set();
			customInstructions = [];
			showOriginal1 = false;
			showOriginal2 = false;
		}
		
		// Always load the scenario's original prompt and response
		childPrompt1 = prompt;
		originalResponse1 = response;
		
		// Reset UI state
		conversationStep = 'first';
		showSystemRules = false;
		generatingResponse2 = false;
		selectionButtonsVisible1 = false;
		selectionButtonsVisible2 = false;
		currentSelection1 = '';
		currentSelection2 = '';
	}

	function resetConversation() {
		// Clear the saved state for current scenario and reload it fresh
		scenarioStates.delete(selectedScenarioIndex);
		
		const [prompt, response] = scenarioList[selectedScenarioIndex];
		
		// Reset to fresh state
		conversationStep = 'first';
		showSecondPass = false;
		moderationResult1 = null;
		moderationResult2 = null;
		childPrompt2 = '';
		originalResponse2 = '';
		highlightedTexts2 = [];
		showOriginal1 = false;
		showOriginal2 = false;
		showSystemRules = false;
		generatingResponse2 = false;
		selectionButtonsVisible1 = false;
		selectionButtonsVisible2 = false;
		currentSelection1 = '';
		currentSelection2 = '';
		highlightedTexts1 = [];
		selectedModerations = new Set();
		customInstructions = [];
		
		// Reload scenario
		childPrompt1 = prompt;
		originalResponse1 = response;
	}
	
	// ====== PARENT MODE: TEXT SELECTION HANDLERS ======
	function handleTextSelection(passNumber: 1 | 2, event: MouseEvent) {
		console.log('handleTextSelection called for pass', passNumber);
		const container = passNumber === 1 ? responseContainer1 : responseContainer2;
		if (!container || !event.target || !container.contains(event.target as Node)) {
			console.log('Early return - container check failed');
			return;
		}
		
		setTimeout(() => {
			const selection = window.getSelection();
			const selectedText = selection?.toString().trim() || '';
			console.log('Selection:', selectedText);
			
			if (!selection || selectedText.length === 0) {
				// Hide floating buttons if no selection
				console.log('No selection, hiding buttons');
				if (passNumber === 1) {
					selectionButtonsVisible1 = false;
					currentSelection1 = '';
				} else {
					selectionButtonsVisible2 = false;
					currentSelection2 = '';
				}
				return;
			}
			
			// Store the selected text so it's available when the button is clicked
			if (passNumber === 1) {
				currentSelection1 = selectedText;
			} else {
				currentSelection2 = selectedText;
			}
			console.log('Stored selection:', selectedText);
			
			// Get selection position
			const range = selection.getRangeAt(0);
			const rect = range.getBoundingClientRect();
			const containerRect = container.getBoundingClientRect();
			
			// Calculate button position relative to container
			const top = rect.bottom - containerRect.top + 5;
			const left = rect.left - containerRect.left;
			
			console.log('Showing buttons at position:', {top, left});
			
			// Show floating buttons at selection position
			if (passNumber === 1) {
				selectionButtonsTop1 = top;
				selectionButtonsLeft1 = left;
				selectionButtonsVisible1 = true;
				console.log('Set selectionButtonsVisible1 = true');
			} else {
				selectionButtonsTop2 = top;
				selectionButtonsLeft2 = left;
				selectionButtonsVisible2 = true;
				console.log('Set selectionButtonsVisible2 = true');
			}
		}, 10);
	}
	
	function saveSelection(passNumber: 1 | 2) {
		// Use the stored selection text instead of trying to get it from window
		const text = passNumber === 1 ? currentSelection1 : currentSelection2;
		
		console.log('saveSelection called with:', {passNumber, text, storedText: text});
		
		if (!text) {
			console.log('No stored selection text, returning');
			return;
		}
		
		// Add to highlighted texts if not already present
		if (passNumber === 1) {
			if (!highlightedTexts1.includes(text)) {
				highlightedTexts1 = [...highlightedTexts1, text];
				console.log('Updated highlightedTexts1:', highlightedTexts1);
			} else {
				console.log('Text already in highlightedTexts1');
			}
			selectionButtonsVisible1 = false;
			currentSelection1 = '';  // Clear stored selection
		} else {
			if (!highlightedTexts2.includes(text)) {
				highlightedTexts2 = [...highlightedTexts2, text];
				console.log('Updated highlightedTexts2:', highlightedTexts2);
			} else {
				console.log('Text already in highlightedTexts2');
			}
			selectionButtonsVisible2 = false;
			currentSelection2 = '';  // Clear stored selection
		}
		
		// Clear browser selection if it still exists
		const selection = window.getSelection();
		if (selection) {
			selection.removeAllRanges();
		}
	}
	
	function removeHighlight(passNumber: 1 | 2, text: string) {
		if (passNumber === 1) {
			highlightedTexts1 = highlightedTexts1.filter(t => t !== text);
		} else {
			highlightedTexts2 = highlightedTexts2.filter(t => t !== text);
		}
	}
	
	// Helper function to generate HTML with highlights
	function getHighlightedHTML(text: string, highlights: string[]): string {
		console.log('getHighlightedHTML called with:', {textLength: text.length, highlights});
		
		if (highlights.length === 0) {
			return text;
		}
		
		// Sort highlights by length (longest first) to avoid nested replacements
		const sortedHighlights = [...highlights].sort((a, b) => b.length - a.length);
		console.log('Sorted highlights:', sortedHighlights);
		
		let processedText = text;
		const replacements: Array<{search: string, replace: string}> = [];
		
		sortedHighlights.forEach((highlight, index) => {
			const placeholder = `__HIGHLIGHT_${index}__`;
			const escapedHighlight = highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
			replacements.push({
				search: placeholder,
				replace: `<mark class="selection-highlight bg-yellow-200 dark:bg-yellow-600">${highlight}</mark>`
			});
			// Use first occurrence only
			const regex = new RegExp(escapedHighlight);
			console.log('Replacing:', highlight, 'with placeholder', placeholder, 'regex test:', regex.test(processedText));
			processedText = processedText.replace(regex, placeholder);
		});
		
		console.log('After placeholders:', processedText.substring(0, 200));
		
		// Replace placeholders with actual mark elements
		replacements.forEach(({search, replace}) => {
			processedText = processedText.replace(search, replace);
		});
		
		console.log('Final HTML (first 200 chars):', processedText.substring(0, 200));
		
		return processedText;
	}
	
	// Reactive computed HTML for responses with highlights
	$: response1HTML = (() => {
		console.log('Computing response1HTML with:', {
			moderationResult1: !!moderationResult1,
			showOriginal1,
			highlightedTexts1,
			originalResponse1Length: originalResponse1.length
		});
		if (moderationResult1 && !showOriginal1) {
			return moderationResult1.refactored_response;
		}
		const html = getHighlightedHTML(originalResponse1, highlightedTexts1);
		console.log('Generated HTML length:', html.length);
		return html;
	})();
	
	$: response2HTML = (() => {
		console.log('Computing response2HTML with:', {
			moderationResult2: !!moderationResult2,
			showOriginal2,
			highlightedTexts2,
			originalResponse2Length: originalResponse2.length
		});
		if (moderationResult2 && !showOriginal2) {
			return moderationResult2.refactored_response;
		}
		return getHighlightedHTML(originalResponse2, highlightedTexts2);
	})();
	// ====== END PARENT MODE FUNCTIONS ======
</script>

<svelte:head>
	<style>
		/* Rotate the arrow when details is open */
		details[open] .details-arrow {
			transform: rotate(180deg);
		}
		.details-arrow {
			transition: transform 0.2s ease;
		}
	</style>
	<title>
		{$chatTitle
			? `${$chatTitle.length > 30 ? `${$chatTitle.slice(0, 30)}...` : $chatTitle} • ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

<audio id="audioElement" src="" style="display: none;" />

<EventConfirmDialog
	bind:show={showEventConfirmation}
	title={eventConfirmationTitle}
	message={eventConfirmationMessage}
	input={eventConfirmationInput}
	inputPlaceholder={eventConfirmationInputPlaceholder}
	inputValue={eventConfirmationInputValue}
	on:confirm={(e) => {
		if (e.detail) {
			eventCallback(e.detail);
		} else {
			eventCallback(true);
		}
	}}
	on:cancel={() => {
		eventCallback(false);
	}}
/>

<div
	class="h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? '  md:max-w-[calc(100%-260px)]'
		: ' '} w-full max-w-full flex flex-col kid-chat-container"
	id="chat-container"
>
	<!-- Child Profile Popup -->
	{#if showChildProfilePopup}
		<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" role="dialog" aria-modal="true" on:click={closeChildProfilePopup}>
			<div class="bg-white dark:bg-gray-800 rounded-xl p-6 {($settings?.widescreenMode ?? null) ? 'max-w-2xl' : 'max-w-md'} w-full mx-4 shadow-2xl relative" on:click|stopPropagation on:mousedown|stopPropagation>
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
						{#if childProfiles.length > 0}
							Your Saved Child Profile
						{:else}
							Set Up Your Child Profile
						{/if}
					</h3>
					<button
						type="button"
						on:click={closeChildProfilePopup}
						class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
						aria-label="Close dialog"
					>
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
						</svg>
					</button>
				</div>
				
				{#if childProfiles.length > 0}
					<!-- Show saved child profiles -->
					<div class="space-y-4">
						{#if childProfiles.length > 1}
							<!-- Multiple children - show selection -->
							<div class="space-y-2">
								<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Select a child profile:</h4>
								{#each childProfiles as child, index}
									<button
										type="button"
										on:click={() => {
											console.log(`Clicked ${child.name} (index: ${index})`);
											console.log(`Previous selectedChildIndex: ${selectedChildIndex}`);
											isManualSelection = true;
											selectedChildIndex = index;
											const selectedChild = childProfiles[selectedChildIndex];
											if (selectedChild) {
												childProfileSync.setCurrentChildId(selectedChild.id);
												currentChild = selectedChild;
												console.log(`New selectedChildIndex: ${selectedChildIndex}`);
												console.log(`New currentChild:`, currentChild);
												// Refresh selections to show only current child's selections
												refreshSelections();
											}
										}}
										class="w-full p-3 rounded-lg border-2 transition-all duration-200 text-left cursor-pointer select-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {selectedChildIndex === index ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'}"
									>
										<div class="flex items-center space-x-3">
											<div class="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
												<span class="text-white font-semibold text-sm">
													{(child.name || 'Kid').charAt(0).toUpperCase()}
												</span>
											</div>
											<div class="flex-1">
												<h5 class="font-medium text-gray-900 dark:text-white">
													{child.name || `Kid ${index + 1}`}
												</h5>
												<p class="text-sm text-gray-500 dark:text-gray-400">
													{child.child_age || 'Age not set'} • {child.child_gender || 'Gender not set'}
												</p>
											</div>
											{#if selectedChildIndex === index}
												<div class="w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center">
													<svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
														<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
													</svg>
												</div>
											{/if}
										</div>
										{#if child.child_characteristics}
											<p class="text-xs text-gray-600 dark:text-gray-400 mt-2 line-clamp-2">
												{child.child_characteristics}
											</p>
										{/if}
									</button>
								{/each}
							</div>
						{:else}
							<!-- Single child - show profile directly -->
							<div class="flex items-center space-x-3">
								<div class="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
									<span class="text-white font-semibold text-lg">
										{(childProfiles[selectedChildIndex]?.name || 'Kid').charAt(0).toUpperCase()}
									</span>
								</div>
								<div>
									<h4 class="font-medium text-gray-900 dark:text-white">
										{childProfiles[selectedChildIndex]?.name || `Kid ${selectedChildIndex + 1}`}
									</h4>
									<p class="text-sm text-gray-500 dark:text-gray-400">
										{childProfiles[selectedChildIndex]?.child_age || 'Age not set'} • {childProfiles[selectedChildIndex]?.child_gender || 'Gender not set'}
									</p>
								</div>
							</div>
						{/if}
						
						{#if childProfiles[selectedChildIndex]?.child_characteristics}
							<div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
								<p class="text-sm text-gray-700 dark:text-gray-300">
									<strong>Characteristics:</strong> {childProfiles[selectedChildIndex].child_characteristics}
								</p>
							</div>
						{/if}
						
						<p class="text-sm text-gray-600 dark:text-gray-400">
							This information helps personalize your AI learning experience.
						</p>
					</div>
				{:else}
					<!-- First time setup message -->
					<div class="text-center space-y-4">
						<div class="w-16 h-16 bg-gradient-to-r from-emerald-500 to-teal-600 rounded-full flex items-center justify-center mx-auto">
							<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
							</svg>
						</div>
						<div>
							<h4 class="font-medium text-gray-900 dark:text-white mb-2">Welcome to Kids Mode!</h4>
							<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
								To get the best personalized experience, set up your child profile first.
							</p>
							<button
								type="button"
								on:click={() => {
									window.location.href = '/kids/profile';
								}}
								class="w-full bg-gradient-to-r from-emerald-500 to-teal-600 text-white px-4 py-2 rounded-lg hover:from-emerald-400 hover:to-teal-500 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
							>
								Set Up Child Profile
							</button>
						</div>
					</div>
				{/if}
				
				<div class="mt-6 flex justify-end">
					<button
						type="button"
						on:click={closeChildProfilePopup}
						class="px-4 py-2 rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 {childProfiles.length > 0 && selectedChildIndex !== null && selectedChildIndex >= 0 ? 'bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:from-green-600 hover:to-emerald-700 focus:ring-green-500' : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 focus:ring-gray-500'}"
					>
						{childProfiles.length > 0 ? 'Continue' : 'Skip for now'}
					</button>
				</div>
			</div>
		</div>
	{/if}

	{#if !loading}
		<div in:fade={{ duration: 50 }} class="w-full h-full flex flex-col">
			<!-- Gradient Background -->
			<div class="gradient-background"></div>
			
			{#if $settings?.backgroundImageUrl ?? null}
				<div
					class="absolute {$showSidebar
						? 'md:max-w-[calc(100%-260px)] md:translate-x-[260px]'
						: ''} top-0 left-0 w-full h-full bg-cover bg-center bg-no-repeat"
					style="background-image: url({$settings.backgroundImageUrl})  "
				/>

				<div
					class="absolute top-0 left-0 w-full h-full bg-linear-to-t from-white to-white/85 dark:from-gray-900 dark:to-gray-900/90 z-0"
				/>
			{/if}
			
			<!-- Parent Mode Toggle -->
			<div class="absolute bottom-4 right-4 z-50">
				<button
					on:click={() => parentMode = !parentMode}
					class="px-4 py-2 rounded-lg font-medium transition-all shadow-lg {parentMode 
						? 'bg-purple-500 text-white hover:bg-purple-600' 
						: 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600'}"
				>
					{parentMode ? '👨‍👩‍👧 Parent Mode' : '🧒 Kid Mode'}
				</button>
			</div>

			{#if parentMode}
				<!-- Parent Mode: Chat-Based Iterative Moderation -->
		<div class="absolute inset-0 w-full h-full flex bg-white dark:bg-gray-900 z-10">
		<!-- Left Sidebar: Scenario List -->
					<div class="w-80 flex-shrink-0 border-r border-gray-200 dark:border-gray-800 flex flex-col bg-gray-50 dark:bg-gray-900">
						<!-- Sidebar Header -->
						<div class="flex-shrink-0 border-b border-gray-200 dark:border-gray-800 p-4">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">Scenarios</h2>
			<p class="text-xs text-gray-600 dark:text-gray-400 mb-2">
				Select a conversation to review
			</p>
			<!-- Progress Counter -->
			<div class="flex items-center justify-between text-xs">
				<span class="text-gray-500 dark:text-gray-400">
					Total: {scenarioList.length}
				</span>
				<span class="px-2 py-1 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 font-medium">
					{scenarioStates.size + (moderationResult1 && !scenarioStates.has(selectedScenarioIndex) ? 1 : 0)} Moderated
				</span>
			</div>
						</div>

		<!-- Sidebar Content (Scrollable Scenario List) -->
		<div class="flex-1 overflow-y-auto p-3 space-y-2">
			{#each scenarioList as [prompt, response], index}
				<button
					on:click={() => loadScenario(index)}
					class="w-full text-left p-3 rounded-lg border transition-all duration-200 {
						selectedScenarioIndex === index
							? 'bg-blue-50 dark:bg-blue-900/20 border-blue-500 dark:border-blue-600 shadow-sm'
							: 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700 hover:shadow-sm'
					}"
				>
					<!-- Scenario Number Badge & Status Indicator -->
					<div class="flex items-start space-x-2">
						<div class="flex-shrink-0 relative">
							<div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold {
								selectedScenarioIndex === index
									? 'bg-blue-500 text-white'
									: 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
							}">
								{index + 1}
							</div>
							<!-- Moderation Progress Indicator -->
							{#if scenarioStates.has(index) || (selectedScenarioIndex === index && (moderationResult1 || moderationResult2))}
								<div class="absolute -top-1 -right-1 w-3 h-3 bg-green-500 border-2 border-white dark:border-gray-800 rounded-full" title="Has moderation work"></div>
							{/if}
						</div>
						
						<!-- Scenario Question (truncated) -->
						<div class="flex-1 min-w-0">
							<div class="flex items-center justify-between mb-1">
								<p class="text-sm font-medium text-gray-900 dark:text-white line-clamp-2 leading-tight flex-1">
									{prompt}
								</p>
							</div>
							
							<!-- Preview of response (very short) -->
							<p class="text-xs text-gray-500 dark:text-gray-400 line-clamp-1">
								{response.substring(0, 50)}{response.length > 50 ? '...' : ''}
							</p>
							
							<!-- Progress indicators (when moderated) -->
							{#if scenarioStates.has(index) || (selectedScenarioIndex === index && (moderationResult1 || moderationResult2))}
								<div class="mt-1.5 flex items-center space-x-2 text-xs">
									{#if (scenarioStates.get(index)?.moderationResult1 || (selectedScenarioIndex === index && moderationResult1))}
										<span class="inline-flex items-center px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
											<svg class="w-2.5 h-2.5 mr-0.5" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
											</svg>
											Pass 1
										</span>
									{/if}
									{#if (scenarioStates.get(index)?.moderationResult2 || (selectedScenarioIndex === index && moderationResult2))}
										<span class="inline-flex items-center px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
											<svg class="w-2.5 h-2.5 mr-0.5" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
											</svg>
											Pass 2
										</span>
									{/if}
								</div>
							{/if}
						</div>
					</div>
					
					<!-- Selected Indicator -->
					{#if selectedScenarioIndex === index}
						<div class="mt-2 flex items-center space-x-1 text-xs text-blue-600 dark:text-blue-400">
							<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
							</svg>
							<span>Currently viewing</span>
						</div>
					{/if}
				</button>
			{/each}
		</div>

		<!-- Sidebar Footer: Reset Button -->
		<div class="flex-shrink-0 border-t border-gray-200 dark:border-gray-800 p-4">
			<button
				on:click={resetConversation}
				class="w-full px-4 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors flex items-center justify-center space-x-2"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
				</svg>
				<span>Reset Scenario</span>
			</button>
		</div>
	</div>

					<!-- Right Side: Chat Thread -->
					<div class="flex-1 flex flex-col">
						<!-- Chat Header -->
						<div class="flex-shrink-0 border-b border-gray-200 dark:border-gray-800 p-4">
							<h1 class="text-xl font-bold text-gray-900 dark:text-white">Conversation Review</h1>
							<p class="text-sm text-gray-600 dark:text-gray-400">Review and moderate AI responses</p>
						</div>

						<!-- Chat Messages Area -->
						<div class="flex-1 overflow-y-auto p-6 space-y-4">
							<!-- First Pass - Child Prompt Bubble (Blue, Right-aligned) -->
							<div class="flex justify-end">
								<div class="max-w-[80%] bg-blue-500 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
									<p class="text-sm whitespace-pre-wrap">{childPrompt1}</p>
								</div>
							</div>

							<!-- First Pass - AI Response Bubble (Gray, Left-aligned) -->
						<div class="flex justify-start">
							<div 
								bind:this={responseContainer1}
								on:mouseup={(e) => handleTextSelection(1, e)}
								class="max-w-[80%] bg-gray-100 dark:bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm relative select-text"
							>
								<div class="text-sm text-gray-900 dark:text-white whitespace-pre-wrap response-text">
									{@html response1HTML}
								</div>
								
								<!-- Floating Selection Buttons - Show when viewing original (always for first pass, or when toggled after moderation) -->
								{#if selectionButtonsVisible1 && (!moderationResult1 || showOriginal1)}
									<div 
										class="absolute z-50 bg-white dark:bg-gray-700 shadow-lg rounded-lg px-2 py-1 flex items-center space-x-2"
										style="top: {selectionButtonsTop1}px; left: {selectionButtonsLeft1}px;"
										on:mousedown|stopPropagation
										on:mouseup|stopPropagation
									>
										<button
											on:click|stopPropagation|preventDefault={(e) => {
												console.log('Highlight button clicked!');
												saveSelection(1);
											}}
											on:mousedown|stopPropagation
											class="px-3 py-1 text-xs font-medium bg-yellow-500 hover:bg-yellow-600 text-white rounded transition-colors"
										>
											💡 Highlight
										</button>
										<button
											on:click|stopPropagation={() => {
												console.log('Close button clicked');
												selectionButtonsVisible1 = false;
											}}
											on:mousedown|stopPropagation
											class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
										>
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
											</svg>
										</button>
									</div>
								{/if}
								
							<!-- Toggle Button (only show if moderation has been applied) -->
							{#if moderationResult1}
								<button
									on:click={() => showOriginal1 = !showOriginal1}
									class="mt-2 text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center space-x-1"
								>
									<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
									</svg>
									<span>{showOriginal1 ? 'View Moderated' : 'View Original'}</span>
								</button>
							{/if}
							
							<!-- Highlighted Texts Display - Show when viewing original -->
							{#if highlightedTexts1.length > 0 && (!moderationResult1 || showOriginal1)}
								<div class="mt-3 pt-2 border-t border-gray-300 dark:border-gray-600">
									<p class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Highlighted Concerns ({highlightedTexts1.length}):</p>
									<div class="flex flex-wrap gap-1">
										{#each highlightedTexts1 as highlight}
											<span 
												class="inline-flex items-center px-2 py-1 text-xs bg-yellow-100 dark:bg-yellow-700 text-gray-800 dark:text-gray-100 rounded cursor-pointer hover:bg-yellow-200 dark:hover:bg-yellow-600"
												on:click={() => removeHighlight(1, highlight)}
												title="Click to remove"
											>
												{highlight.length > 30 ? highlight.substring(0, 30) + '...' : highlight}
												<svg class="w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
												</svg>
											</span>
										{/each}
									</div>
								</div>
							{/if}
						</div>
					</div>
				
				<!-- Moderation Panel for Pass 1 (Below Response) -->
				{#if !moderationResult1 || showOriginal1}
					<div class="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
						<h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-3">Select Moderation Strategies</h3>
						
							<!-- Strategy Count -->
						<div class="flex items-center justify-between mb-3">
								<span class="text-xs text-gray-600 dark:text-gray-400">
									{selectedModerations.size} selected
								</span>
								{#if selectedModerations.size > 0}
									<button
										on:click={clearSelections}
										class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
									>
										Clear All
									</button>
								{/if}
							</div>

						<!-- Strategy Grid (3 columns for better use of space) -->
						<div class="grid grid-cols-3 gap-2 mb-3">
								{#each moderationOptions as option}
									<button
										on:click={() => toggleModerationSelection(option)}
										disabled={moderationLoading}
									class="p-3 text-xs font-medium text-center rounded-lg transition-all {
											option === 'Custom'
												? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600'
												: selectedModerations.has(option)
												? 'bg-blue-500 text-white hover:bg-blue-600 ring-2 ring-blue-400'
											: 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-600 border border-gray-200 dark:border-gray-600'
										} disabled:opacity-50"
									>
										{option === 'Custom' ? '✨ Custom' : option}
									</button>
								{/each}
							</div>

							<!-- Custom Instructions -->
							{#if customInstructions.length > 0}
							<div class="p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg mb-3">
									<h4 class="text-xs font-semibold text-purple-900 dark:text-purple-200 mb-2">
									Custom Instructions ({customInstructions.length}):
									</h4>
									<div class="space-y-2">
										{#each customInstructions as custom}
											<div class="flex items-start justify-between bg-white dark:bg-purple-900/30 p-2 rounded border-2 {
												selectedModerations.has(custom.id) 
													? 'border-purple-500' 
													: 'border-transparent'
											}">
												<button
													on:click={() => toggleModerationSelection(custom.id)}
													class="flex-1 text-left mr-2"
												>
													<div class="flex items-center space-x-1 mb-1">
														<div class="w-3 h-3 rounded border-2 {
															selectedModerations.has(custom.id)
																? 'bg-purple-500 border-purple-500'
																: 'border-gray-300 dark:border-gray-600'
														} flex items-center justify-center">
															{#if selectedModerations.has(custom.id)}
																<svg class="w-2 h-2 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																	<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
																</svg>
															{/if}
														</div>
														<p class="text-xs text-purple-800 dark:text-purple-200 font-medium">
															#{customInstructions.indexOf(custom) + 1}
														</p>
													</div>
													<p class="text-xs text-gray-700 dark:text-gray-300 line-clamp-2">
														{custom.text}
													</p>
												</button>
												<button
													on:click={() => removeCustomInstruction(custom.id)}
													class="text-red-500 hover:text-red-700 dark:text-red-400 flex-shrink-0"
													title="Remove"
												>
													<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
													</svg>
												</button>
											</div>
										{/each}
									</div>
								</div>
							{/if}

					<!-- Apply Button for Pass 1 -->
							<button
						on:click={() => applySelectedModerations(1)}
								disabled={moderationLoading || selectedModerations.size === 0}
								class="w-full px-4 py-2.5 bg-green-500 hover:bg-green-600 disabled:bg-gray-400 text-white text-sm font-semibold rounded-lg transition-colors flex items-center justify-center space-x-2"
							>
								{#if moderationLoading}
									<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
									<span>Applying...</span>
								{:else}
									<span>Apply Moderation</span>
								{/if}
							</button>
				</div>
			{/if}
				
				<!-- Applied Strategies Display (Show after moderation) -->
				{#if moderationResult1 && !showOriginal1}
					<div class="mt-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
						<h4 class="text-sm font-semibold text-green-900 dark:text-green-200 mb-2 flex items-center">
							<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
										</svg>
							Applied Strategies
						</h4>
													<ul class="space-y-1">
							{#each moderationResult1.moderation_types as strategy}
								<li class="text-xs text-green-800 dark:text-green-300 flex items-start">
									<span class="text-green-600 dark:text-green-400 mr-1.5">✓</span>
																<span>{strategy}</span>
															</li>
														{/each}
													</ul>
								</div>
									{/if}

									<!-- Generate Follow-Up Button (only show after Pass 1 moderation) -->
									{#if moderationResult1 && !showSecondPass}
							<div class="mt-3">
										<button
											on:click={generateFollowUp}
											disabled={generatingPrompt2}
									class="w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white text-sm rounded-lg font-medium transition-colors flex items-center justify-center space-x-2"
										>
											{#if generatingPrompt2}
												<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
												<span>Generating...</span>
											{:else}
												<span>➡️ Generate Follow-Up Question</span>
											{/if}
										</button>
								</div>
						{/if}

							<!-- Second Pass - Follow-Up Child Prompt Bubble (only show if generated) -->
							{#if showSecondPass && childPrompt2}
								<div class="flex justify-end mt-6">
									<div class="max-w-[80%] bg-blue-500 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
										<p class="text-sm whitespace-pre-wrap">{childPrompt2}</p>
									</div>
								</div>

								<!-- Second Pass - AI Response Bubble -->
								{#if generatingResponse2}
									<!-- Loading state -->
									<div class="flex justify-start">
										<div class="max-w-[80%] bg-gray-100 dark:bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
											<div class="flex items-center space-x-2">
												<div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms;"></div>
												<div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms;"></div>
												<div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms;"></div>
											</div>
										</div>
									</div>
								{:else if originalResponse2}
									<!-- Response generated -->
									<div class="flex justify-start">
									<div 
										bind:this={responseContainer2}
										on:mouseup={(e) => handleTextSelection(2, e)}
										class="max-w-[80%] bg-gray-100 dark:bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm relative select-text"
									>
										<div class="text-sm text-gray-900 dark:text-white whitespace-pre-wrap response-text">
											{@html response2HTML}
										</div>
										
										<!-- Floating Selection Buttons - Show when viewing original -->
										{#if selectionButtonsVisible2 && (!moderationResult2 || showOriginal2)}
											<div 
												class="absolute z-50 bg-white dark:bg-gray-700 shadow-lg rounded-lg px-2 py-1 flex items-center space-x-2"
												style="top: {selectionButtonsTop2}px; left: {selectionButtonsLeft2}px;"
												on:mousedown|stopPropagation
												on:mouseup|stopPropagation
											>
												<button
													on:click|stopPropagation|preventDefault={(e) => {
														console.log('Highlight button (Pass 2) clicked!');
														saveSelection(2);
													}}
													on:mousedown|stopPropagation
													class="px-3 py-1 text-xs font-medium bg-yellow-500 hover:bg-yellow-600 text-white rounded transition-colors"
												>
													💡 Highlight
												</button>
												<button
													on:click|stopPropagation={() => {
														console.log('Close button (Pass 2) clicked');
														selectionButtonsVisible2 = false;
													}}
													on:mousedown|stopPropagation
													class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
												>
													<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
													</svg>
												</button>
											</div>
												{/if}
											
											<!-- Toggle Button for Pass 2 -->
											{#if moderationResult2}
												<button
													on:click={() => showOriginal2 = !showOriginal2}
													class="mt-2 text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center space-x-1"
												>
													<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
													</svg>
													<span>{showOriginal2 ? 'View Moderated' : 'View Original'}</span>
												</button>
											{/if}
										
									<!-- Highlighted Texts Display - Show when viewing original -->
									{#if highlightedTexts2.length > 0 && (!moderationResult2 || showOriginal2)}
										<div class="mt-3 pt-2 border-t border-gray-300 dark:border-gray-600">
											<p class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Highlighted Concerns ({highlightedTexts2.length}):</p>
											<div class="flex flex-wrap gap-1">
												{#each highlightedTexts2 as highlight}
													<span 
														class="inline-flex items-center px-2 py-1 text-xs bg-yellow-100 dark:bg-yellow-700 text-gray-800 dark:text-gray-100 rounded cursor-pointer hover:bg-yellow-200 dark:hover:bg-yellow-600"
														on:click={() => removeHighlight(2, highlight)}
														title="Click to remove"
													>
														{highlight.length > 30 ? highlight.substring(0, 30) + '...' : highlight}
														<svg class="w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
															<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
														</svg>
													</span>
												{/each}
										</div>
									</div>
								{/if}
								</div>
							</div>
							
							<!-- Moderation Panel for Pass 2 (Below Response) -->
							{#if !moderationResult2 || showOriginal2}
								<div class="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
									<h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-3">Select Moderation Strategies (Pass 2)</h3>
									
									<!-- Strategy Count -->
									<div class="flex items-center justify-between mb-3">
										<span class="text-xs text-gray-600 dark:text-gray-400">
											{selectedModerations.size} selected
										</span>
										{#if selectedModerations.size > 0}
											<button
												on:click={clearSelections}
												class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
											>
												Clear All
											</button>
							{/if}
						</div>
									
									<!-- Strategy Grid (3 columns for better use of space) -->
									<div class="grid grid-cols-3 gap-2 mb-3">
										{#each moderationOptions as option}
											<button
												on:click={() => toggleModerationSelection(option)}
												disabled={moderationLoading}
												class="p-3 text-xs font-medium text-center rounded-lg transition-all {
													option === 'Custom'
														? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600'
														: selectedModerations.has(option)
														? 'bg-blue-500 text-white hover:bg-blue-600 ring-2 ring-blue-400'
														: 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-600 border border-gray-200 dark:border-gray-600'
												} disabled:opacity-50"
											>
												{option === 'Custom' ? '✨ Custom' : option}
											</button>
										{/each}
					</div>
									
									<!-- Custom Instructions -->
									{#if customInstructions.length > 0}
										<div class="p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg mb-3">
											<h4 class="text-xs font-semibold text-purple-900 dark:text-purple-200 mb-2">
												Custom Instructions ({customInstructions.length}):
											</h4>
											<div class="space-y-2">
												{#each customInstructions as custom}
													<div class="flex items-start justify-between bg-white dark:bg-purple-900/30 p-2 rounded border-2 {
														selectedModerations.has(custom.id) 
															? 'border-purple-500' 
															: 'border-transparent'
													}">
														<button
															on:click={() => toggleModerationSelection(custom.id)}
															class="flex-1 text-left mr-2"
														>
															<div class="flex items-center space-x-1 mb-1">
																<div class="w-3 h-3 rounded border-2 {
																	selectedModerations.has(custom.id)
																		? 'bg-purple-500 border-purple-500'
																		: 'border-gray-300 dark:border-gray-600'
																} flex items-center justify-center">
																	{#if selectedModerations.has(custom.id)}
																		<svg class="w-2 h-2 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
																		</svg>
																	{/if}
																</div>
																<p class="text-xs text-purple-800 dark:text-purple-200 font-medium">
																	#{customInstructions.indexOf(custom) + 1}
																</p>
															</div>
															<p class="text-xs text-gray-700 dark:text-gray-300 line-clamp-2">
																{custom.text}
															</p>
														</button>
														<button
															on:click={() => removeCustomInstruction(custom.id)}
															class="text-red-500 hover:text-red-700 dark:text-red-400 flex-shrink-0"
															title="Remove"
														>
															<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
															</svg>
														</button>
													</div>
												{/each}
											</div>
										</div>
									{/if}
									
								<!-- Apply Button for Pass 2 -->
								<button
									on:click={() => applySelectedModerations(2)}
									disabled={moderationLoading || selectedModerations.size === 0}
									class="w-full px-4 py-2.5 bg-green-500 hover:bg-green-600 disabled:bg-gray-400 text-white text-sm font-semibold rounded-lg transition-colors flex items-center justify-center space-x-2"
								>
									{#if moderationLoading}
										<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
										<span>Applying...</span>
									{:else}
										<span>Apply Moderation</span>
									{/if}
								</button>
							</div>
							{/if}
							
							<!-- Applied Strategies Display for Pass 2 (Show after moderation) -->
							{#if moderationResult2 && !showOriginal2}
								<div class="mt-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
									<h4 class="text-sm font-semibold text-green-900 dark:text-green-200 mb-2 flex items-center">
										<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
										</svg>
										Applied Strategies (Pass 2)
									</h4>
									<ul class="space-y-1">
										{#each moderationResult2.moderation_types as strategy}
											<li class="text-xs text-green-800 dark:text-green-300 flex items-start">
												<span class="text-green-600 dark:text-green-400 mr-1.5">✓</span>
												<span>{strategy}</span>
											</li>
										{/each}
									</ul>
								</div>
							{/if}
							{/if}
						{/if}
					</div>
				</div>
				</div>
			{:else}
				<!-- Kids Mode View (Original Chat Interface) -->
				<PaneGroup direction="horizontal" class="w-full h-full">
				<Pane defaultSize={50} class="h-full flex relative max-w-full flex-col">
					<Navbar
						bind:this={navbarElement}
						chat={{
							id: $chatId,
							chat: {
								title: $chatTitle,
								models: selectedModels,
								system: $settings.system ?? undefined,
								params: params,
								history: history,
								timestamp: Date.now()
							}
						}}
						{history}
						title={$chatTitle}
						bind:selectedModels
						shareEnabled={!!history.currentId}
						{initNewChat}
					/>
					

					<div class="flex flex-col flex-auto z-10 w-full @container">
						{#if $settings?.landingPageMode === 'chat' || createMessagesList(history, history.currentId).length > 0}
							<div
								class=" pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0 max-w-full z-10 scrollbar-hidden"
								id="messages-container"
								bind:this={messagesContainerElement}
								on:scroll={(e) => {
									autoScroll =
										messagesContainerElement.scrollHeight - messagesContainerElement.scrollTop <=
										messagesContainerElement.clientHeight + 5;
								}}
							>
								<div class=" h-full w-full flex flex-col">
									<Messages
										chatId={$chatId}
										bind:history
										bind:autoScroll
										bind:prompt
										{selectedModels}
										{atSelectedModel}
										{sendPrompt}
										{showMessage}
										{submitMessage}
										{continueResponse}
										{regenerateResponse}
										{mergeResponses}
										{chatActionHandler}
										{addMessages}
										bottomPadding={files.length > 0}
									/>
								</div>
							</div>

							<!-- Child Profile Info Display (only in kids mode) - positioned above input -->
							{#if isKidsMode}
								<div class="bg-gradient-to-r from-blue-100 to-purple-100 dark:from-blue-900/30 dark:to-purple-900/30 border-l-4 border-blue-500 dark:border-blue-400 mx-4 mb-3 p-3 rounded-lg shadow-md">
									<div class="flex items-center space-x-3">
										<div class="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg">
											<span class="text-white font-bold text-sm">
												{#if currentChild}
													{(currentChild.name || 'Kid').charAt(0).toUpperCase()}
												{:else}
													K
												{/if}
											</span>
										</div>
										<div class="flex-1 min-w-0">
											<div class="flex items-center space-x-2">
												<span class="font-semibold text-gray-900 dark:text-white text-sm">
													{#if currentChild}
														{currentChild.name || `Kid ${selectedChildIndex + 1}`}
													{:else}
														Kids Mode
													{/if}
												</span>
												{#if currentChild}
													<span class="text-xs text-gray-600 dark:text-gray-300 bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded-full">
														{currentChild.child_age || 'Age not set'}
													</span>
													<span class="text-xs text-gray-600 dark:text-gray-300 bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded-full">
														{currentChild.child_gender || 'Gender not set'}
													</span>
												{/if}
											</div>
											{#if currentChild?.child_characteristics}
												<p class="text-sm text-gray-700 dark:text-gray-300 mt-1 line-clamp-2">
													{currentChild.child_characteristics}
												</p>
											{:else if !currentChild}
												<p class="text-sm text-gray-700 dark:text-gray-300 mt-1">
													Set up your profile in Parent Dashboard for personalized AI experience
												</p>
											{/if}
										</div>
										<div class="flex space-x-2 flex-shrink-0">
											{#if currentChild && childProfiles.length > 1}
												<button
													on:click={showChildSelectionPopup}
													class="bg-gradient-to-r from-green-500 to-emerald-600 text-white text-xs font-medium px-3 py-2 rounded-lg hover:from-green-600 hover:to-emerald-700 transition-all duration-200 shadow-md hover:shadow-lg"
												>
													Change Kids
												</button>
											{/if}
											<button
												on:click={() => {
													window.location.href = '/kids/profile';
												}}
												class="bg-gradient-to-r from-blue-500 to-purple-600 text-white text-xs font-medium px-3 py-2 rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all duration-200 shadow-md hover:shadow-lg"
											>
												{#if currentChild}
													Edit Profile
												{:else}
													Set Up Profile
												{/if}
											</button>
										</div>
									</div>
								</div>
							{/if}

						<div class=" pb-2">
                                <MessageInput
									{history}
									{taskIds}
									{selectedModels}
									bind:files
									bind:prompt
									bind:autoScroll
									bind:selectedToolIds
									bind:selectedFilterIds
									bind:imageGenerationEnabled
									bind:codeInterpreterEnabled
									bind:webSearchEnabled
									bind:atSelectedModel
									toolServers={$toolServers}
									transparentBackground={$settings?.backgroundImageUrl ?? false}
									{stopResponse}
									{createMessagePair}
									onChange={(input) => {
										if (!$temporaryChatEnabled) {
											if (input.prompt !== null) {
												localStorage.setItem(
													`chat-input${$chatId ? `-${$chatId}` : ''}`,
													JSON.stringify(input)
												);
											} else {
												localStorage.removeItem(`chat-input${$chatId ? `-${$chatId}` : ''}`);
											}
										}
									}}
									on:upload={async (e) => {
										const { type, data } = e.detail;

										if (type === 'web') {
											await uploadWeb(data);
										} else if (type === 'youtube') {
											await uploadYoutubeTranscription(data);
										} else if (type === 'google-drive') {
											await uploadGoogleDriveFile(data);
										}
									}}
                                    on:submit={async (e) => {
										if (e.detail || files.length > 0) {
											await tick();
											submitPrompt(
												($settings?.richTextInput ?? true)
													? e.detail.replaceAll('\n\n', '\n')
													: e.detail
											);
										}
									}}
								/>

								<div
									class="absolute bottom-1 text-xs text-gray-500 text-center line-clamp-1 right-0 left-0"
								>
									<!-- {$i18n.t('LLMs can make mistakes. Verify important information.')} -->
								</div>
							</div>
						{:else}
							<div class="overflow-auto w-full h-full flex items-center">
								<Placeholder
									{history}
									{selectedModels}
									bind:files
									bind:prompt
									bind:autoScroll
									bind:selectedToolIds
									bind:selectedFilterIds
									bind:imageGenerationEnabled
									bind:codeInterpreterEnabled
									bind:webSearchEnabled
									bind:atSelectedModel
									transparentBackground={$settings?.backgroundImageUrl ?? false}
									toolServers={$toolServers}
									{stopResponse}
									{createMessagePair}
									on:upload={async (e) => {
										const { type, data } = e.detail;

										if (type === 'web') {
											await uploadWeb(data);
										} else if (type === 'youtube') {
											await uploadYoutubeTranscription(data);
										} else if (type === 'google-drive') {
											await uploadGoogleDriveFile(data);
										}
									}}
									on:submit={async (e) => {
										if (e.detail || files.length > 0) {
											await tick();
											submitPrompt(
												($settings?.richTextInput ?? true)
													? e.detail.replaceAll('\n\n', '\n')
													: e.detail
											);
										}
									}}
								/>
							</div>
						{/if}
					</div>
				</Pane>

				<ChatControls
					bind:this={controlPaneComponent}
					bind:history
					bind:chatFiles
					bind:params
					bind:files
					bind:pane={controlPane}
					chatId={$chatId}
					modelId={selectedModelIds?.at(0) ?? null}
					models={selectedModelIds.reduce((a, e, i, arr) => {
						const model = $models.find((m) => m.id === e);
						if (model) {
							return [...a, model];
						}
						return a;
					}, [])}
					{submitPrompt}
					{stopResponse}
					{showMessage}
					{eventTarget}
				/>
			</PaneGroup>
			{/if}
		</div>
	{:else if loading}
		<div class=" flex items-center justify-center h-full w-full">
			<div class="m-auto">
				<Spinner />
			</div>
		</div>
	{/if}
</div>

<!-- Custom Moderation Modal (Parent Mode) -->
{#if showCustomModal}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full">
			<div class="p-6">
				<div class="flex justify-between items-center mb-4">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
						<span class="text-2xl">✨</span>
						<span>Custom Moderation Instruction</span>
					</h2>
					<button
						on:click={cancelCustomModal}
						class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
					>
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
						</svg>
					</button>
				</div>
				
				<div class="mb-6">
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
						Enter a custom instruction for how the AI should moderate the response. Be specific and clear about what you want.
					</p>
					
					<div class="mb-4">
						<label for="custom-instruction-textarea" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							Custom Instruction
						</label>
						<textarea
							id="custom-instruction-textarea"
							bind:value={customInstructionInput}
							placeholder="Example: Explain this topic using simple analogies appropriate for a 7-year-old, focusing on positive aspects..."
							class="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
							rows="6"
						></textarea>
						<div class="flex justify-between items-center mt-2">
							<p class="text-xs text-gray-500 dark:text-gray-400">
								This will be combined with any other selected moderation strategies.
							</p>
							<p class="text-xs text-gray-500 dark:text-gray-400">
								{customInstructionInput.length} characters
							</p>
						</div>
					</div>
					
					<!-- Example Instructions -->
					<details class="mb-4">
						<summary class="text-sm font-medium text-gray-700 dark:text-gray-300 cursor-pointer hover:text-gray-900 dark:hover:text-white">
							💡 See example custom instructions
						</summary>
						<div class="mt-3 space-y-2 text-xs text-gray-600 dark:text-gray-400">
							<p class="p-2 bg-gray-50 dark:bg-gray-900 rounded">
								• "Use sports analogies to explain complex concepts"
							</p>
							<p class="p-2 bg-gray-50 dark:bg-gray-900 rounded">
								• "Focus on positive role models and their achievements"
							</p>
							<p class="p-2 bg-gray-50 dark:bg-gray-900 rounded">
								• "Explain both sides of the issue fairly without taking a stance"
							</p>
							<p class="p-2 bg-gray-50 dark:bg-gray-900 rounded">
								• "Keep the explanation under 3 sentences and very simple"
							</p>
						</div>
					</details>
				</div>
				
				<div class="flex justify-end space-x-3">
					<button
						on:click={cancelCustomModal}
						class="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg font-medium transition-colors"
					>
						Cancel
					</button>
					<button
						on:click={addCustomInstruction}
						disabled={!customInstructionInput.trim()}
						class="px-6 py-2 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-all shadow-md"
					>
						Add Custom Instruction
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

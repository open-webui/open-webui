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
    savedSelections,
    selectionForceInput,
	latestAssistantMessageId,
	latestUserMessageId
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
	import {
		chatCompleted,
		generateQueries,
		chatAction,
		generateMoACompletion,
		stopTask,
		getTaskIdsByChatId
	} from '$lib/apis';
	import { getTools } from '$lib/apis/tools';

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

// NOTE: We intentionally do NOT persist the model selection to
// sessionStorage or user settings. This ensures that on refresh/new chat
// the app always resets to the desired default (see initNewChat).
$: if (selectedModels && chatIdProp !== '') {
    // No-op: selection is session-only and not persisted
}

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
				initNewChat();
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

// Initial model selection policy (highest precedence first):
// 1) URL query "models" or "model" (validated against available models)
// 2) Preferred model 'gpt-5-2025-08-07' if available
// 3) Server-configured default_models (comma-separated)
// 4) First available model
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
				selectedModels = [availableModels?.at(0) ?? ''];
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

        // selection is session-only and not persisted

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
</script>

<svelte:head>
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

						<div class=" pb-2">
							<!-- Start/Done buttons moved into MessageInput bar -->
                            {#if inputPanelState === 'message'}
                                {#key messageInputResetKey}
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
                                            // Clear input box after submit
                                            prompt = '';
                                            try {
                                                const id = $chatId;
                                                if (id) localStorage.removeItem(`chat-input-${id}`);
                                                else localStorage.removeItem('chat-input');
                                            } catch {}
                                            // Force re-mount of MessageInput to clear internal editor state immediately
                                            messageInputResetKey += 1;
										}
									}}
								/>
                                {/key}
                            {:else if inputPanelState === 'selection'}
                                <!-- Always show MessageInput when in selection mode -->
                                <MessageInput
                                    key={messageInputResetKey}
                                    bind:this={messageInput}
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
                                    bind:showCommands
                                    {toolServers}
                                    {stopResponse}
                                    {createMessagePair}
                                    placeholder={$i18n.t('How can I help you today?')}
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
                                    disabled={true}
                                    on:upload={(e) => {
                                        dispatch('upload', e.detail);
                                    }}
                                    on:submit={(e) => {
                                        dispatch('submit', e.detail);
                                    }}
                                />
							{/if}

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
		</div>
	{:else if loading}
		<div class=" flex items-center justify-center h-full w-full">
			<div class="m-auto">
				<Spinner />
			</div>
		</div>
	{/if}
</div>



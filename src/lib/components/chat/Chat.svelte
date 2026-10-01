<script lang="ts">
	import { getI18n } from '$lib/utils/context';

	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';
	import { PaneGroup, Pane } from 'paneforge';

	import { onDestroy, onMount, tick } from 'svelte';
	const i18n: Writable<i18nType> = getI18n();

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { type Unsubscriber, type Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { WEBUI_BASE_URL, WEBUI_API_BASE_URL } from '$lib/constants';

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
		initNewChatAction
	} from '$lib/stores';
	import {
		convertMessagesToHistory,
		copyToClipboard,
		getMessageContentParts,
		promptTemplate,
		removeDetailsWithReasoning
	} from '$lib/utils';

	import {
		createNewChat,
		getAllTags,
		getChatById,
		getChatList,
		getTagsById,
		updateChatById
	} from '$lib/apis/chats';
	import { generateOpenAIChatCompletion } from '$lib/apis/openai';
	import { processWeb, processYoutubeVideo } from '$lib/apis/retrieval';
	import { createOpenAITextStream } from '$lib/apis/streaming';
	import { getAndUpdateUserLocation, getUserSettings } from '$lib/apis/users';
	import { chatCompleted, chatAction, generateMoACompletion, stopTask } from '$lib/apis';
	import { getTools } from '$lib/apis/tools';
	import { queryCrewMCPWebSocket } from '$lib/apis/crew-mcp';
	import { uploadFile } from '$lib/apis/files';

	import Banner from '../common/Banner.svelte';
	import MessageInput from '$lib/components/chat/MessageInput.svelte';
	import Messages from '$lib/components/chat/Messages.svelte';
	import Navbar from '$lib/components/chat/Navbar.svelte';
	import ChatControls from './ChatControls.svelte';
	import EventConfirmDialog from '../common/ConfirmDialog.svelte';
	import Placeholder from './Placeholder.svelte';
	import { getRequestToken } from '$lib/services/auth';

	export let chatIdProp = '';

	let loaded = false;
	const eventTarget = new EventTarget();
	let controlPane: any;
	let controlPaneComponent: any;

	let autoScroll = true;
	let processing = '';
	let messagesContainerElement: HTMLDivElement;

	let navbarElement: any;

	let showEventConfirmation = false;
	let eventConfirmationTitle = '';
	let eventConfirmationMessage = '';
	let eventConfirmationInput = false;
	let eventConfirmationInputPlaceholder = '';
	let eventConfirmationInputValue = '';
	let eventCallback: any = null;

	let chatIdUnsubscriber: Unsubscriber | undefined;

	let selectedModels = [''];
	let atSelectedModel: Model | undefined;
	let selectedModelIds: any[] = [];
	$: selectedModelIds = atSelectedModel !== undefined ? [atSelectedModel.id] : selectedModels;

	let chat: any = null;
	let tags = [];
	let taskIdsByMessageId: Record<string, string> = {};
	let stoppedResponseIds: Record<string, boolean> = {};

	// Default transient state values
	const TRANSIENT_DEFAULTS: any = {
		prompt: '',
		files: [],
		selectedToolIds: [],
		imageGenerationEnabled: false,
		webSearchEnabled: false,
		wikiGroundingEnabled: false,
		wikiGroundingMode: 'off',
		history: { messages: {}, currentId: null },
		chatFiles: [],
		params: {}
	};

	// Declare chat Input and transient state variables cleanly
	let prompt = TRANSIENT_DEFAULTS.prompt;
	let files = TRANSIENT_DEFAULTS.files;
	let selectedToolIds: string[] = [];
	let imageGenerationEnabled = TRANSIENT_DEFAULTS.imageGenerationEnabled;
	let webSearchEnabled = TRANSIENT_DEFAULTS.webSearchEnabled;
	let wikiGroundingEnabled = TRANSIENT_DEFAULTS.wikiGroundingEnabled;
	let wikiGroundingMode = TRANSIENT_DEFAULTS.wikiGroundingMode;
	let history: any = structuredClone(TRANSIENT_DEFAULTS.history);
	let chatFiles = TRANSIENT_DEFAULTS.chatFiles;
	let params: Record<string, any> = TRANSIENT_DEFAULTS.params;

	// Chat Input Handler for draft saving
	const handleInputChange = (input: any) => {
		if ($chatId) {
			if (input.prompt) {
				localStorage.setItem(`chat-input-${$chatId}`, JSON.stringify(input));
			} else {
				localStorage.removeItem(`chat-input-${$chatId}`);
			}
		}
	};

	const resetTransientChatInputState = () => {
		prompt = TRANSIENT_DEFAULTS.prompt;
		files = [];
		selectedToolIds = [];
		imageGenerationEnabled = TRANSIENT_DEFAULTS.imageGenerationEnabled;
		webSearchEnabled = TRANSIENT_DEFAULTS.webSearchEnabled;
		wikiGroundingEnabled = TRANSIENT_DEFAULTS.wikiGroundingEnabled;
		wikiGroundingMode = TRANSIENT_DEFAULTS.wikiGroundingMode;
		history = structuredClone(TRANSIENT_DEFAULTS.history);
		chatFiles = [];
		params = {};
		taskIdsByMessageId = {};
		stoppedResponseIds = {};
	};

	$: if (chatIdProp) {
		(async () => {
			// Reset all transient state first
			resetTransientChatInputState();

			// Restore from localStorage if available
			let storedInput: any = null;
			const storedData = localStorage.getItem(`chat-input-${chatIdProp}`);
			if (storedData) {
				try {
					storedInput = JSON.parse(storedData);
				} catch (e: any) {}
			}

			// Override with stored values if available
			if (storedInput?.prompt) prompt = storedInput.prompt;
			if (storedInput?.files) files = storedInput.files;
			if (storedInput?.selectedToolIds) selectedToolIds = storedInput.selectedToolIds;
			if (storedInput?.webSearchEnabled !== undefined)
				webSearchEnabled = storedInput.webSearchEnabled;
			if (storedInput?.wikiGroundingEnabled !== undefined)
				wikiGroundingEnabled = storedInput.wikiGroundingEnabled;
			if (storedInput?.imageGenerationEnabled !== undefined)
				imageGenerationEnabled = storedInput.imageGenerationEnabled;
			if (storedInput?.wikiGroundingEnabled) wikiGroundingMode = 'on';

			loaded = false;

			if (chatIdProp && (await loadChat())) {
				await tick();
				loaded = true;

				window.setTimeout(() => scrollToBottom(), 0);
				const chatInput = document.getElementById('chat-input');
				chatInput?.focus();
			} else {
				await goto('/');
			}
		})();
	} else {
		(async () => {
			await initNewChat();
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
	};

	$: if (selectedModels) {
		setToolIds();
	}

	const setToolIds = async () => {
		if (!$tools) {
			tools.set((await getTools(getRequestToken())) as any);
		}

		if (selectedModels.length !== 1) {
			return;
		}
		const model = $models.find((m) => m.id === selectedModels[0]);
		if (model) {
			selectedToolIds = (model?.info?.meta?.toolIds ?? []).filter((id: any) =>
				($tools as { id: string }[] | null)?.some((tool) => tool.id === id)
			);
		}
	};

	const showMessage = async (message: any) => {
		const _chatId = JSON.parse(JSON.stringify($chatId));
		let _messageId = JSON.parse(JSON.stringify(message.id));

		let messageChildrenIds = history.messages[_messageId].childrenIds;

		while (messageChildrenIds.length !== 0) {
			_messageId = messageChildrenIds.at(-1);
			messageChildrenIds = history.messages[_messageId].childrenIds;
		}

		history.currentId = _messageId;

		await tick();
		await tick();
		await tick();

		const messageElement = document.getElementById(`message-${message.id}`);
		if (messageElement) {
			messageElement.scrollIntoView({ behavior: 'smooth' });
		}

		await tick();
		saveChatHandler(_chatId);
	};

	const clearResponseTracking = (responseMessageId: string) => {
		if (responseMessageId in taskIdsByMessageId) {
			const { [responseMessageId]: _taskId, ...remainingTaskIds } = taskIdsByMessageId;
			taskIdsByMessageId = remainingTaskIds;
		}
	};

	const markResponseStopped = (responseMessageId: string) => {
		stoppedResponseIds = {
			...stoppedResponseIds,
			[responseMessageId]: true
		};
	};

	const isResponseStopped = (responseMessageId: string) =>
		stoppedResponseIds[responseMessageId] === true;

	const emitChatFinish = (message: { id: string; content: string }) => {
		eventTarget.dispatchEvent(
			new CustomEvent('chat:finish', {
				detail: {
					id: message.id,
					content: message.content
				}
			})
		);
	};

	const finalizeStoppedResponse = async (responseMessageId: string) => {
		const responseMessage = history.messages[responseMessageId];
		clearResponseTracking(responseMessageId);

		if (!responseMessage || responseMessage.done === true) {
			return;
		}

		responseMessage.done = true;
		history.messages[responseMessageId] = responseMessage;
		emitChatFinish(responseMessage);

		if (autoScroll) {
			scrollToBottom();
		}

		await tick();
		await saveChatHandler($chatId);
	};

	const stopResponseTask = async (responseTaskId: string) => {
		try {
			await stopTask(localStorage.token, responseTaskId);
		} catch (error: any) {
			const errorDetail =
				typeof error === 'string' ? error : (error?.detail ?? error?.message ?? '');
			const errorMessage = String(errorDetail).toLowerCase();

			if (!errorMessage.includes('not found')) {
				console.error('Failed to stop chat response task', error);
			}
		}
	};

	const chatEventHandler = async (event: any, cb: any) => {
		if (event.chat_id === $chatId) {
			await tick();
			let message = history.messages[event.message_id];

			if (message) {
				const type = event?.data?.type ?? null;
				const data = event?.data?.data ?? null;

				if (type === 'task-cancelled') {
					await finalizeStoppedResponse(message.id);
					return;
				}

				if (type === 'status') {
					if (message?.statusHistory) {
						message.statusHistory.push(data);
					} else {
						message.statusHistory = [data];
					}
				} else if (type === 'source' || type === 'citation') {
					if (data?.type === 'code_execution') {
						// Code execution; update existing code execution by ID, or add new one.
						if (!message?.code_executions) {
							message.code_executions = [];
						}

						const existingCodeExecutionIndex = message.code_executions.findIndex(
							(execution: any) => execution.id === data.id
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
				} else if (type === 'chat:completion') {
					chatCompletionEventHandler(data, message, event.chat_id);
				} else if (type === 'chat:title') {
					chatTitle.set(data);
					currentChatPage.set(1);
					await chats.set(await getChatList(getRequestToken(), $currentChatPage));
				} else if (type === 'chat:tags') {
					chat = await getChatById(getRequestToken(), $chatId);
					allTags.set(await getAllTags(getRequestToken()));
				} else if (type === 'message') {
					message.content += data.content;
				} else if (type === 'replace') {
					message.content = data.content;
				} else if (type === 'action') {
					if (data.action === 'continue') {
						const continueButton = document.getElementById('continue-response-button');

						if (continueButton) {
							continueButton.click();
						}
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
					} catch (error: any) {
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

			if (prompt !== '') {
				await tick();
				submitPrompt(event.data.text);
			}
		}
	};

	onMount(async () => {
		// Register initNewChat callback for sidebar to use
		initNewChatAction.set(() => initNewChat());

		window.addEventListener('message', onMessageHandler);
		$socket?.on('chat-events', chatEventHandler);

		if (!$chatId) {
			chatIdUnsubscriber = chatId.subscribe(async (value) => {
				if (!value) {
					await initNewChat();
				}
			});
		} else {
			if ($temporaryChatEnabled) {
				await goto('/');
			}
		}

		if (localStorage.getItem(`chat-input-${chatIdProp}`)) {
			try {
				const storedData = localStorage.getItem(`chat-input-${chatIdProp}`);
				if (storedData) {
					const input = JSON.parse(storedData);
					prompt = input.prompt;
					files = input.files;
					selectedToolIds = input.selectedToolIds;
					webSearchEnabled = input.webSearchEnabled;
					wikiGroundingEnabled = input.wikiGroundingEnabled || false;
					imageGenerationEnabled = input.imageGenerationEnabled;
				}
			} catch (e: any) {
				resetTransientChatInputState();
			}
		}

		showControls.subscribe(async (value) => {
			if (controlPane && !$mobile) {
				try {
					if (value) {
						controlPaneComponent.openPane();
					} else {
						controlPane.collapse();
					}
				} catch (e: any) {
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
	});

	onDestroy(() => {
		chatIdUnsubscriber?.();
		initNewChatAction.set(null);
		window.removeEventListener('message', onMessageHandler);
		$socket?.off('chat-events', chatEventHandler);
	});

	// File upload functions

	const uploadGoogleDriveFile = async (fileData: any) => {
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
			// Configure fetch options with proper headers
			const fetchOptions = {
				headers: {
					Authorization: fileData.headers.Authorization,
					Accept: '*/*'
				},
				method: 'GET'
			};

			// Attempt to fetch the file
			const fileResponse = await fetch(fileData.url, fetchOptions);

			if (!fileResponse.ok) {
				const errorText = await fileResponse.text();
				throw new Error(`Failed to fetch file (${fileResponse.status}): ${errorText}`);
			}

			// Get content type from response
			const contentType = fileResponse.headers.get('content-type') || 'application/octet-stream';

			// Convert response to blob
			const fileBlob = await fileResponse.blob();

			if (fileBlob.size === 0) {
				throw new Error('Retrieved file is empty');
			}

			// Create File object with proper MIME type
			const file = new File([fileBlob], fileData.name, {
				type: fileBlob.type || contentType
			});

			if (file.size === 0) {
				throw new Error('Created file is empty');
			}

			// Upload file to server
			const uploadedFile = await uploadFile(getRequestToken(), file);

			if (!uploadedFile) {
				throw new Error('Server returned null response for file upload');
			}

			// Update file item with upload results
			fileItem.status = 'uploaded';
			fileItem.file = uploadedFile;
			fileItem.id = uploadedFile.id;
			fileItem.size = file.size;
			fileItem.collection_name = uploadedFile?.meta?.collection_name;
			fileItem.url = `${WEBUI_API_BASE_URL}/files/${uploadedFile.id}`;

			files = files;
			toast.success($i18n.t('File uploaded successfully'));
		} catch (e: any) {
			files = files.filter((f: any) => f.itemId !== tempItemId);
			toast.error(
				$i18n.t('Error uploading file: {{error}}', {
					error: e.message || 'Unknown error'
				})
			);
		}
	};

	const uploadWeb = async (url: any) => {
		const fileItem: any = {
			type: 'doc',
			name: url,
			collection_name: '',
			status: 'uploading',
			url: url,
			error: ''
		};

		try {
			files = [...files, fileItem];
			const res = await processWeb(getRequestToken(), '', url);

			if (res) {
				fileItem.status = 'uploaded';
				fileItem.collection_name = res.collection_name;
				fileItem.file = {
					...res.file,
					...fileItem.file
				};

				files = files;
			}
		} catch (e: any) {
			// Remove the failed doc from the files array
			files = files.filter((f: any) => f.name !== url);
			toast.error(JSON.stringify(e));
		}
	};

	const uploadYoutubeTranscription = async (url: any) => {
		const fileItem: any = {
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
			const res = await processYoutubeVideo(getRequestToken(), url);

			if (res) {
				fileItem.status = 'uploaded';
				fileItem.collection_name = res.collection_name;
				fileItem.file = {
					...res.file,
					...fileItem.file
				};
				files = files;
			}
		} catch (e: any) {
			// Remove the failed doc from the files array
			files = files.filter((f: any) => f.name !== url);
			toast.error(e);
		}
	};

	//////////////////////////
	// Web functions
	//////////////////////////

	const initNewChat = async () => {
		// Clear transient chat/input state immediately to avoid prompt carryover during route transitions
		resetTransientChatInputState();

		//ensures the url is reset to the root
		if (chatIdProp || $chatId) {
			if ($chatId) {
				await chatId.set('');
			}
			await goto('/');
			return;
		}

		if ($page.url.searchParams.get('models')) {
			selectedModels = $page.url.searchParams.get('models')!.split(',');
		} else if ($page.url.searchParams.get('model')) {
			const urlModels = $page.url.searchParams.get('model')!.split(',');

			if (urlModels.length === 1) {
				const m = $models.find((m) => m.id === urlModels[0]);
				if (!m) {
					const modelSelectorButton = document.getElementById('model-selector-0-button');
					if (modelSelectorButton) {
						modelSelectorButton.click();
						await tick();

						const modelSelectorInput = document.getElementById(
							'model-search-input'
						) as HTMLInputElement | null;
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
		} else {
			// Clear sessionStorage to ensure we use default models for new chats
			sessionStorage.removeItem('selectedModels');

			if ($settings?.models) {
				selectedModels = $settings?.models;
			} else if ($config?.default_models) {
				selectedModels = $config?.default_models.split(',');
			}
		}

		selectedModels = selectedModels.filter((modelId) => $models.map((m) => m.id).includes(modelId));
		if (selectedModels.length === 0 || (selectedModels.length === 1 && selectedModels[0] === '')) {
			if ($models.length > 0) {
				selectedModels = [$models[0].id];
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

		if ($chatId) {
			await chatId.set('');
		}
		await chatTitle.set('');

		if ($page.url.searchParams.get('youtube')) {
			uploadYoutubeTranscription(
				`https://www.youtube.com/watch?v=${$page.url.searchParams.get('youtube')}`
			);
		}
		if ($page.url.searchParams.get('web-search') === 'true') {
			webSearchEnabled = true;
		}
		if ($page.url.searchParams.get('image-generation') === 'true') {
			imageGenerationEnabled = true;
		}

		if ($page.url.searchParams.get('tools')) {
			selectedToolIds = $page.url.searchParams.get('tools')?.split(',') ?? [];
			selectedToolIds = selectedToolIds.map((id) => id.trim()).filter((id) => id);
		} else if ($page.url.searchParams.get('tool-ids')) {
			selectedToolIds = $page.url.searchParams.get('tool-ids')?.split(',') ?? [];
			selectedToolIds = selectedToolIds.map((id) => id.trim()).filter((id) => id);
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

		const userSettings = await getUserSettings(getRequestToken());

		if (userSettings) {
			settings.set(userSettings.ui as Parameters<typeof settings.set>[0]);
		} else {
			settings.set(JSON.parse(localStorage.getItem('settings') ?? '{}'));
		}
		const chatInput = document.getElementById('chat-input');
		setTimeout(() => chatInput?.focus(), 0);
	};

	const loadChat = async () => {
		chatId.set(chatIdProp);
		chat = await getChatById(getRequestToken(), $chatId).catch(async (error) => {
			await goto('/');
			return null;
		});

		if (chat) {
			const chatTags = await getTagsById(getRequestToken(), $chatId).catch(() => []);
			tags = Array.isArray(chatTags) ? chatTags : [];

			const chatContent = chat.chat;

			if (chatContent) {
				selectedModels =
					(chatContent?.models ?? undefined) !== undefined
						? chatContent.models
						: [chatContent.models ?? ''];
				history =
					(chatContent?.history ?? undefined) !== undefined
						? chatContent.history
						: convertMessagesToHistory(chatContent.messages);

				chatTitle.set(chatContent.title);

				const userSettings = await getUserSettings(getRequestToken());

				if (userSettings) {
					await settings.set(userSettings.ui as Parameters<typeof settings.set>[0]);
				} else {
					await settings.set(JSON.parse(localStorage.getItem('settings') ?? '{}'));
				}

				params = chatContent?.params ?? {};
				chatFiles = chatContent?.files ?? [];

				autoScroll = true;
				await tick();

				if (history.currentId) {
					history.messages[history.currentId].done = true;
				}
				await tick();

				return true;
			} else {
				return null;
			}
		}
	};

	const scrollToBottom = async () => {
		await tick();
		if (messagesContainerElement) {
			messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
		}
	};

	const createMessagesList = (responseMessageId: any): any[] => {
		if (responseMessageId === null) {
			return [];
		}

		const message = history.messages[responseMessageId];
		if (message?.parentId) {
			return [...createMessagesList(message.parentId), message];
		} else {
			return [message];
		}
	};

	const chatCompletedHandler = async (
		chatId: any,
		modelId: any,
		responseMessageId: any,
		messages: any
	) => {
		const res: any = await chatCompleted(getRequestToken(), {
			model: modelId,
			messages: messages.map((m: any) => ({
				id: m.id,
				role: m.role,
				content: m.content,
				info: m.info ? m.info : undefined,
				timestamp: m.timestamp,
				...(m.sources ? { sources: m.sources } : {})
			})),
			chat_id: chatId,
			session_id: $socket?.id ?? ''
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
				chat = await updateChatById(getRequestToken(), chatId, {
					models: selectedModels,
					messages: messages,
					history: history,
					params: params,
					files: chatFiles
				});

				currentChatPage.set(1);
				await chats.set(await getChatList(getRequestToken(), $currentChatPage));
			}
		}
	};

	const chatActionHandler = async (
		chatId: any,
		actionId: any,
		modelId: any,
		responseMessageId: any,
		event = null
	) => {
		const messages = createMessagesList(responseMessageId);

		const res: any = await chatAction(getRequestToken(), actionId, {
			model: modelId,
			messages: messages.map((m: any) => ({
				id: m.id,
				role: m.role,
				content: m.content,
				info: m.info ? m.info : undefined,
				timestamp: m.timestamp,
				...(m.sources ? { sources: m.sources } : {})
			})),
			...(event ? { event: event } : {}),
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
				chat = await updateChatById(getRequestToken(), chatId, {
					models: selectedModels,
					messages: messages,
					history: history,
					params: params,
					files: chatFiles
				});

				currentChatPage.set(1);
				await chats.set(await getChatList(getRequestToken(), $currentChatPage));
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

	const createMessagePair = async (userPrompt: any) => {
		prompt = '';
		if (selectedModels.length === 0) {
			toast.error($i18n.t('Model not selected'));
		} else {
			const modelId = selectedModels[0];
			const model = $models.filter((m) => m.id === modelId).at(0);

			const messages = createMessagesList(history.currentId);
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
				modelName: model?.name ?? modelId,
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
				await initChatHandler();
			} else {
				await saveChatHandler($chatId);
			}
		}
	};

	const addMessages = async ({ modelId, parentId, messages }: any) => {
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
					model: modelId,
					modelName: model?.name ?? modelId,
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
			await initChatHandler();
		} else {
			await saveChatHandler($chatId);
		}
	};

	const chatCompletionEventHandler = async (data: any, message: any, chatId: any) => {
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
						message.content,
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
				message.content,
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
			clearResponseTracking(message.id);
			message.done = true;

			if ($settings.responseAutoCopy) {
				copyToClipboard(message.content);
			}

			if ($settings.responseAutoPlayback && !$showCallOverlay) {
				await tick();
				document.getElementById(`speak-button-${message.id}`)?.click();
			}

			// Emit chat event for TTS
			let lastMessageContentPart =
				getMessageContentParts(message.content, $config?.audio?.tts?.split_on ?? 'punctuation')?.at(
					-1
				) ?? '';
			if (lastMessageContentPart) {
				eventTarget.dispatchEvent(
					new CustomEvent('chat', {
						detail: { id: message.id, content: lastMessageContentPart }
					})
				);
			}
			emitChatFinish(message);

			history.messages[message.id] = message;
			await chatCompletedHandler(chatId, message.model, message.id, createMessagesList(message.id));
		}

		if (autoScroll) {
			scrollToBottom();
		}
	};

	//////////////////////////
	// Chat functions
	//////////////////////////

	const submitPrompt = async (userPrompt: any, { _raw = false } = {}) => {
		const messages = createMessagesList(history.currentId);
		const _selectedModels = selectedModels.map((modelId) =>
			$models.map((m) => m.id).includes(modelId) ? modelId : ''
		);
		if (JSON.stringify(selectedModels) !== JSON.stringify(_selectedModels)) {
			selectedModels = _selectedModels;
		}

		if (userPrompt === '') {
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
		if (messages.length != 0 && messages.at(-1).error) {
			// Error in response
			toast.error($i18n.t(`Oops! There was an error in the previous response.`));
			return;
		}
		if (
			files.length > 0 &&
			files.filter((file: any) => file.type !== 'image' && file.status === 'uploading').length > 0
		) {
			toast.error(
				$i18n.t(`Oops! There are files still uploading. Please wait for the upload to complete.`)
			);
			return;
		}
		const maxFileCount = $config?.file?.max_count;
		if (maxFileCount != null && files.length + chatFiles.length > maxFileCount) {
			toast.error(
				$i18n.t(`You can only chat with a maximum of {{maxCount}} file(s) at a time.`, {
					maxCount: maxFileCount
				})
			);
			return;
		}

		prompt = '';
		await tick();

		// Reset chat input textarea
		const chatInputElement = document.getElementById('chat-input');

		if (chatInputElement) {
			chatInputElement.style.height = '';
		}

		const _files = JSON.parse(JSON.stringify(files));
		chatFiles.push(
			..._files.filter((item: any) => ['doc', 'file', 'collection'].includes(item.type))
		);
		chatFiles = chatFiles.filter(
			// Remove duplicates
			(item: any, index: any, array: any[]) =>
				array.findIndex((i: any) => JSON.stringify(i) === JSON.stringify(item)) === index
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

		// Wait until history/message have been updated
		await tick();

		// focus on chat input
		const chatInput = document.getElementById('chat-input');
		chatInput?.focus();

		saveSessionSelectedModels();

		await sendPrompt(userPrompt, userMessageId, { newChat: true });
	};

	const sendPrompt = async (
		prompt: string,
		parentId: string,
		{ modelId = null, modelIdx = null, newChat = false } = {}
	) => {
		// Create new chat if newChat is true and first user message
		if (
			newChat &&
			history.messages[history.currentId].parentId === null &&
			history.messages[history.currentId].role === 'user'
		) {
			await initChatHandler();
		} else {
			await saveChatHandler($chatId);
		}

		// If modelId is provided, use it, else use selected model
		let selectedModelIds = modelId
			? [modelId]
			: atSelectedModel !== undefined
				? [atSelectedModel.id]
				: selectedModels;

		// Create response messages for each selected model
		const responseMessageIds: Record<PropertyKey, string> = {};
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
					userContext: null,
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
		await tick();

		// Save chat after all messages have been created
		await saveChatHandler($chatId);

		const _chatId = JSON.parse(JSON.stringify($chatId));
		await Promise.all(
			selectedModelIds.map(async (modelId, _modelIdx) => {
				const model = $models.filter((m) => m.id === modelId).at(0);

				if (model) {
					const messages = createMessagesList(parentId);
					// If there are image files, check if model is vision capable
					const hasImages = messages.some((message: any) =>
						message.files?.some((file: any) => file.type === 'image')
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
					let responseMessage = history.messages[responseMessageId];

					let userContext: any = null;
					responseMessage.userContext = userContext;

					// Web search/wiki grounding are exclusive with tool execution
					const hasSelectedTools =
						selectedToolIds.length > 0 && !webSearchEnabled && !wikiGroundingEnabled;

					if (hasSelectedTools) {
						// Use CrewAI when user has selected any tools
						try {
							console.log('Routing to CrewAI based on selected tools:', selectedToolIds);

							// Update response message to show it's using CrewAI
							responseMessage.content = $i18n.t('Consulting CrewAI agents...');
							history.messages[responseMessageId] = responseMessage;
							await tick();
							scrollToBottom();

							const crewResponse = await queryCrewMCPWebSocket(
								prompt,
								model.id,
								selectedToolIds,
								$chatId,
								(statusMessage: string) => {
									if (isResponseStopped(responseMessageId)) {
										return;
									}

									// Update UI with status from CrewAI
									responseMessage.content = statusMessage;
									history.messages[responseMessageId] = responseMessage;
									tick();
								}
							);

							if (isResponseStopped(responseMessageId)) {
								clearResponseTracking(responseMessageId);
								return;
							}

							if (crewResponse && crewResponse.result) {
								// Check if the result is a SharePoint error message and translate it
								let displayResult = crewResponse.result;
								if (
									displayResult.startsWith(
										'SharePoint delegated access is unavailable in local development mode'
									) ||
									displayResult.startsWith('Local environment lacks OAuth2 proxy')
								) {
									// This is a SharePoint error message that needs translation
									displayResult = $i18n.t(crewResponse.result);
								}

								// These translation keys need to be preserved by i18n parser
								// They are used dynamically above
								$i18n.t(
									'SharePoint delegated access is unavailable in local development mode. Delegated access requires OAuth2 proxy services that are configured only in production deployments. For full SharePoint testing with user permissions, please utilize the staging or production environments where Azure AD authentication is properly established. For local development, set SHP_USE_DELEGATED_ACCESS=false in your .env file to use application access instead, which will authenticate using client credentials and provide access to SharePoint resources.'
								);
								$i18n.t('Local environment lacks OAuth2 proxy for SharePoint delegated access');

								// Update message content with CrewAI response (translated if needed)
								responseMessage.content = displayResult;
								clearResponseTracking(responseMessageId);
								responseMessage.done = true;
								responseMessage.crewAI = true; // Mark as CrewAI response

								// Add metadata about which agents/tools were used
								if (crewResponse.metadata) {
									responseMessage.crewMetadata = crewResponse.metadata;
								}

								history.messages[responseMessageId] = responseMessage;

								// Emit completion events
								emitChatFinish(responseMessage);

								// Save the chat with CrewAI response
								await tick();
								if ($chatId && !$temporaryChatEnabled) {
									const messages = createMessagesList(responseMessageId);

									chat = await updateChatById(getRequestToken(), $chatId, {
										models: selectedModels,
										messages: messages,
										history: history,
										params: params,
										files: chatFiles
									});

									currentChatPage.set(1);
									await chats.set(await getChatList(getRequestToken(), $currentChatPage));
								}

								// Don't call chatCompletedHandler for CrewAI responses to avoid 400 error
								return; // Return early for successful CrewAI response
							} else {
								throw new Error($i18n.t('CrewAI returned no result'));
							}
						} catch (error: any) {
							console.error('CrewAI Error:', error);
							const errorMessage = (error as Error).message || String(error);
							const localizedErrorMessage = $i18n.t(errorMessage);

							// Show error toast
							toast.error($i18n.t('CrewAI Error: {{error}}', { error: localizedErrorMessage }));

							// Display error message in chat instead of falling back
							responseMessage.content = `⚠️ **${$i18n.t('CrewAI MCP Error')}**\n\n${localizedErrorMessage}\n\n*${$i18n.t('The selected tool(s) could not complete this request. This may be due to:')}*\n- ${$i18n.t('Request timeout (processing took too long)')}\n- ${$i18n.t('Network connectivity issues')}\n- ${$i18n.t('SharePoint permissions or authentication problems')}\n\n${$i18n.t('Please try again, or contact support if the issue persists.')}`;
							clearResponseTracking(responseMessageId);
							responseMessage.done = true;
							responseMessage.error = true;
							history.messages[responseMessageId] = responseMessage;

							// Save the error state
							await tick();
							if ($chatId && !$temporaryChatEnabled) {
								const messages = createMessagesList(responseMessageId);
								chat = await updateChatById(getRequestToken(), $chatId, {
									models: selectedModels,
									messages: messages,
									history: history,
									params: params,
									files: chatFiles
								});
							}

							// Don't fall back to regular completion - return early to show error
							return;
						}
					}

					// Only proceed with regular completion if CrewAI wasn't used
					const chatEventEmitter = await getChatEventEmitter(model.id, _chatId);

					scrollToBottom();
					await sendPromptSocket(model, responseMessageId, _chatId);

					if (chatEventEmitter) clearInterval(chatEventEmitter);
				} else {
					toast.error($i18n.t(`Model {{modelId}} not found`, { modelId }));
				}
			})
		);

		currentChatPage.set(1);
		chats.set(await getChatList(getRequestToken(), $currentChatPage));
	};

	const sendPromptSocket = async (model: any, responseMessageId: any, _chatId: any) => {
		const responseMessage = history.messages[responseMessageId];
		const userMessage = history.messages[responseMessage.parentId];

		let files = JSON.parse(JSON.stringify(chatFiles));
		files.push(
			...(userMessage?.files ?? []).filter((item: any) =>
				['doc', 'file', 'collection'].includes(item.type)
			),
			...(responseMessage?.files ?? []).filter((item: any) =>
				['web_search_results'].includes(item.type)
			)
		);
		// Remove duplicates
		files = files.filter(
			(item: any, index: any, array: any) =>
				array.findIndex((i: any) => JSON.stringify(i) === JSON.stringify(item)) === index
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

		const messages = [
			params?.system || $settings.system || (responseMessage?.userContext ?? null)
				? {
						role: 'system',
						content: `${await (async () => {
							// Get user's timezone preference
							const { timezoneService } = await import('$lib/services/timezone');
							const userTimezone = timezoneService.getUserTimezone();
							const userLocation = $settings?.userLocation
								? await getAndUpdateUserLocation(getRequestToken())
								: undefined;

							return promptTemplate(
								params?.system ?? $settings?.system ?? '',
								$user?.name,
								typeof userLocation === 'string'
									? userLocation
									: userLocation
										? `${userLocation.latitude.toFixed(3)}, ${userLocation.longitude.toFixed(3)} (lat, long)`
										: undefined,
								userTimezone
							);
						})()}${
							(responseMessage?.userContext ?? null)
								? `\n\nUser Context:\n${responseMessage?.userContext ?? ''}`
								: ''
						}`
					}
				: undefined,
			...createMessagesList(responseMessageId).map((message: any) => ({
				...message,
				content: removeDetailsWithReasoning(message.content)
			}))
		]
			.filter((message) => message?.content?.trim())
			.map((message, idx, arr) => ({
				role: message.role,
				...((message.files?.some((file: any) => file.type === 'image') ?? false) &&
				message.role === 'user'
					? {
							content: [
								{
									type: 'text',
									text: message?.merged?.content ?? message.content
								},
								...message.files
									.filter((file: any) => file.type === 'image')
									.map((file: any) => ({
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
			}));

		// Regular OpenAI completion
		const res = await generateOpenAIChatCompletion(
			getRequestToken(),
			{
				stream: stream,
				model: model.id,
				messages: messages,
				params: {
					...$settings?.params,
					...params,

					format: $settings.requestFormat ?? undefined,
					keep_alive: $settings.keepAlive ?? undefined,
					stop:
						(params?.stop ?? $settings?.params?.stop ?? undefined)
							? (
									params?.stop.split(',').map((token: any) => token.trim()) ??
									$settings?.params?.stop
								).map((str: any) =>
									decodeURIComponent(JSON.parse('"' + str.replace(/\"/g, '\\"') + '"'))
								)
							: undefined
				},

				files: (files?.length ?? 0) > 0 ? files : undefined,
				tool_ids:
					selectedToolIds.length > 0 && !webSearchEnabled && !wikiGroundingEnabled
						? selectedToolIds
						: undefined,
				features: {
					image_generation: imageGenerationEnabled,
					web_search: webSearchEnabled,
					wiki_grounding: wikiGroundingEnabled,
					wiki_grounding_mode: wikiGroundingMode
				},

				session_id: $socket?.id,
				chat_id: $chatId,
				id: responseMessageId,

				...(!$temporaryChatEnabled &&
				(messages.length == 1 ||
					(messages.length == 2 &&
						messages.at(0)?.role === 'system' &&
						messages.at(1)?.role === 'user')) &&
				selectedModels[0] === model.id
					? {
							background_tasks: {
								title_generation: $settings?.title?.auto ?? true,
								tags_generation: $settings?.autoTags ?? true
							}
						}
					: {}),

				...(stream && (model.info?.meta?.capabilities?.usage ?? false)
					? {
							stream_options: {
								include_usage: true
							}
						}
					: {})
			},
			`${WEBUI_BASE_URL}/api`
		).catch((error) => {
			clearResponseTracking(responseMessageId);

			if (isResponseStopped(responseMessageId)) {
				return null;
			}

			console.log(error);
			responseMessage.error = {
				content: error
			};
			responseMessage.done = true;
			history.messages[responseMessageId] = responseMessage;
			return null;
		});

		if (res?.task_id) {
			taskIdsByMessageId = {
				...taskIdsByMessageId,
				[responseMessageId]: res.task_id
			};

			if (isResponseStopped(responseMessageId)) {
				await stopResponseTask(res.task_id);
			}
		}

		await tick();
		scrollToBottom();
	};

	const handleOpenAIError = async (error: any, responseMessage: any) => {
		let errorMessage = '';
		let innerError: any;

		if (error) {
			innerError = error;
		}

		console.error(innerError);
		if ('detail' in innerError) {
			errorMessage = $i18n.t(String(innerError.detail));
			toast.error(errorMessage);
		} else if ('error' in innerError) {
			if ('message' in innerError.error) {
				errorMessage = $i18n.t(String(innerError.error.message));
				toast.error(errorMessage);
			} else {
				errorMessage = $i18n.t(String(innerError.error));
				toast.error(errorMessage);
			}
		} else if ('message' in innerError) {
			errorMessage = $i18n.t(String(innerError.message));
			toast.error(errorMessage);
		}

		responseMessage.error = {
			content: $i18n.t(`Uh-oh! There was an issue with the response.`) + '\n' + errorMessage
		};
		clearResponseTracking(responseMessage.id);
		responseMessage.done = true;

		if (responseMessage.statusHistory) {
			responseMessage.statusHistory = responseMessage.statusHistory.filter(
				(status: any) => status.action !== 'knowledge_search'
			);
		}

		history.messages[responseMessage.id] = responseMessage;
	};

	const getResponseIdToStop = () => {
		if (!history.currentId) {
			return null;
		}

		const currentResponse = history.messages[history.currentId];
		return currentResponse?.role === 'assistant' && currentResponse?.done !== true
			? history.currentId
			: null;
	};

	const stopResponse = async () => {
		const responseIdToStop = getResponseIdToStop();

		if (!responseIdToStop) {
			return;
		}

		const responseTaskId = taskIdsByMessageId[responseIdToStop];

		markResponseStopped(responseIdToStop);

		if (responseTaskId) {
			await stopResponseTask(responseTaskId);
			return;
		}

		await finalizeStoppedResponse(responseIdToStop);
	};

	const submitMessage = async (parentId: any, prompt: any) => {
		let userPrompt = prompt;
		let userMessageId = uuidv4();

		let userMessage = {
			id: userMessageId,
			parentId: parentId,
			childrenIds: [],
			role: 'user',
			content: userPrompt,
			models: selectedModels
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
		await sendPrompt(userPrompt, userMessageId);
	};

	const regenerateResponse = async (message: any) => {
		if (history.currentId) {
			let userMessage = history.messages[message.parentId];
			let userPrompt = userMessage.content;

			if ((userMessage?.models ?? [...selectedModels]).length == 1) {
				// If user message has only one model selected, sendPrompt automatically selects it for regeneration
				await sendPrompt(userPrompt, userMessage.id);
			} else {
				// If there are multiple models selected, use the model of the response message for regeneration
				// e.g. many model chat
				await sendPrompt(userPrompt, userMessage.id, {
					modelId: message.model,
					modelIdx: message.modelIdx
				});
			}
		}
	};

	const continueResponse = async () => {
		const _chatId = JSON.parse(JSON.stringify($chatId));

		if (history.currentId && history.messages[history.currentId].done == true) {
			const responseMessage = history.messages[history.currentId];
			responseMessage.done = false;
			await tick();

			const model = $models
				.filter((m) => m.id === (responseMessage?.selectedModelId ?? responseMessage.model))
				.at(0);

			if (model) {
				await sendPromptSocket(model, responseMessage.id, _chatId);
			}
		}
	};

	const mergeResponses = async (messageId: any, responses: any, _chatId: any) => {
		const message = history.messages[messageId];
		const mergedResponse = {
			status: true,
			content: ''
		};
		message.merged = mergedResponse;
		history.messages[messageId] = message;

		try {
			const [res, controller] = await generateMoACompletion(
				getRequestToken(),
				message.model,
				history.messages[message.parentId].content,
				responses
			);

			if (res && res.ok && res.body) {
				const textStream = await createOpenAITextStream(
					res.body,
					$settings.splitLargeChunks ?? false
				);
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

				await saveChatHandler(_chatId);
			} else {
				console.error(res);
			}
		} catch (e: any) {
			console.error(e);
		}
	};

	const initChatHandler = async () => {
		if (!$temporaryChatEnabled) {
			chat = await createNewChat(getRequestToken(), {
				id: $chatId,
				title: $i18n.t('New Chat'),
				models: selectedModels,
				system: $settings.system ?? undefined,
				params: params,
				history: history,
				messages: createMessagesList(history.currentId),
				tags: [],
				timestamp: Date.now()
			});

			currentChatPage.set(1);
			await chats.set(await getChatList(getRequestToken(), $currentChatPage));
			await chatId.set(chat.id);

			window.history.replaceState(history.state, '', `/c/${chat.id}`);
		} else {
			await chatId.set('local');
		}
		await tick();
	};

	const saveChatHandler = async (_chatId: any) => {
		if ($chatId == _chatId) {
			if (!$temporaryChatEnabled) {
				chat = await updateChatById(getRequestToken(), _chatId, {
					models: selectedModels,
					history: history,
					messages: createMessagesList(history.currentId),
					params: params,
					files: chatFiles
				});

				currentChatPage.set(1);
				await chats.set(await getChatList(getRequestToken(), $currentChatPage));
			}
		}
	};
</script>

<svelte:head>
	<title>
		{$chatTitle
			? `${$chatTitle.length > 30 ? `${$chatTitle.slice(0, 30)}...` : $chatTitle} | ${$WEBUI_NAME}`
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
		: ' '} w-full max-w-full flex flex-col"
	id="chat-container"
	role="main"
>
	<h1 class="sr-only">
		{$chatTitle ? `${$i18n.t('Chat')}: ${$chatTitle}` : $i18n.t('Chat')}
	</h1>
	{#if !chatIdProp || (loaded && chatIdProp)}
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
			title={$chatTitle}
			bind:selectedModels
			shareEnabled={!!history.currentId}
			{initNewChat}
		/>

		<PaneGroup direction="horizontal" class="w-full h-full">
			<Pane defaultSize={50} class="h-full flex w-full relative">
				{#if $banners.length > 0 && !history.currentId && !$chatId && selectedModels.length <= 1}
					<div class="absolute top-12 left-0 right-0 w-full z-30">
						<div class=" flex flex-col gap-1 w-full">
							{#each $banners.filter((b) => (b.lang ? b.lang === $i18n.language : true) && (b.dismissible ? !JSON.parse(localStorage.getItem('dismissedBannerIds') ?? '[]').includes(b.id) : true)) as banner}
								<Banner
									{banner}
									on:dismiss={(e) => {
										const bannerId = e.detail;

										localStorage.setItem(
											'dismissedBannerIds',
											JSON.stringify(
												[
													bannerId,
													...JSON.parse(localStorage.getItem('dismissedBannerIds') ?? '[]')
												].filter((id) => $banners.find((b) => b.id === id))
											)
										);
									}}
								/>
							{/each}
						</div>
					</div>
				{/if}

				<div class="flex flex-col flex-auto z-10 w-full">
					{#if $settings?.landingPageMode === 'chat' || createMessagesList(history.currentId).length > 0}
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
									{selectedToolIds}
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

						<div class=" pb-[1rem]">
							<MessageInput
								{history}
								{selectedModels}
								bind:files
								bind:prompt
								bind:autoScroll
								bind:selectedToolIds
								bind:imageGenerationEnabled
								bind:webSearchEnabled
								bind:wikiGroundingEnabled
								bind:wikiGroundingMode
								bind:atSelectedModel
								{stopResponse}
								{createMessagePair}
								onChange={handleInputChange}
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
									if (e.detail) {
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
								bind:imageGenerationEnabled
								bind:webSearchEnabled
								bind:wikiGroundingEnabled
								bind:wikiGroundingMode
								bind:atSelectedModel
								onChange={handleInputChange}
								{stopResponse}
								{createMessagePair}
								on:upload={async (e) => {
									const { type, data } = e.detail;

									if (type === 'web') {
										await uploadWeb(data);
									} else if (type === 'youtube') {
										await uploadYoutubeTranscription(data);
									}
								}}
								on:submit={async (e) => {
									if (e.detail) {
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

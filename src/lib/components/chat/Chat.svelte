<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';
	import mermaid from 'mermaid';
	import { PaneGroup, Pane, PaneResizer } from 'paneforge';

	import { getContext, onDestroy, onMount, tick } from 'svelte';
	const i18n: Writable<i18nType> = getContext('i18n');

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
		tools
	} from '$lib/stores';
	import {
		convertMessagesToHistory,
		copyToClipboard,
		getMessageContentParts,
		extractSentencesForAudio,
		promptTemplate,
		splitStream
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
	import {
		chatCompleted,
		generateTitle,
		generateQueries,
		chatAction,
		generateMoACompletion,
		generateTags
	} from '$lib/apis';

	import Banner from '../common/Banner.svelte';
	import MessageInput from '$lib/components/chat/MessageInput.svelte';
	import Messages from '$lib/components/chat/Messages.svelte';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import ChatControls from './ChatControls.svelte';
	import EventConfirmDialog from '../common/ConfirmDialog.svelte';
	import Placeholder from './Placeholder.svelte';
	import { getTools } from '$lib/apis/tools';

	export let chatIdProp = '';

	let loaded = false;
	const eventTarget = new EventTarget();
	let controlPane;
	let controlPaneComponent;

	let stopResponseFlag = false;
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
	let webSearchEnabled = false;

	let chat = null;
	let tags = [];

	let history = {
		messages: {},
		currentId: null
	};

	// Chat Input
	let prompt = '';
	let chatFiles = [];
	let files = [];
	let params = {};

	$: if (chatIdProp) {
		(async () => {
			console.log(chatIdProp);
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

	$: if (selectedModels) {
		setToolIds();
	}

	const setToolIds = async () => {
		if (!$tools) {
			tools.set(await getTools(localStorage.token));
		}

		if (selectedModels.length !== 1) {
			return;
		}
		const model = $models.find((m) => m.id === selectedModels[0]);
		if (model) {
			selectedToolIds = (model?.info?.meta?.toolIds ?? []).filter((id) =>
				$tools.find((t) => t.id === id)
			);
		}
	};

	const showMessage = async (message) => {
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

	const chatEventHandler = async (event, cb) => {
		if (event.chat_id === $chatId) {
			await tick();
			console.log(event);
			let message = history.messages[event.message_id];

			const type = event?.data?.type ?? null;
			const data = event?.data?.data ?? null;

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
		console.log('mounted');
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
	});

	onDestroy(() => {
		chatIdUnsubscriber?.();
		window.removeEventListener('message', onMessageHandler);
		$socket?.off('chat-events');
	});

	// File upload functions

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
			toast.error(e);
		}
	};

	//////////////////////////
	// Web functions
	//////////////////////////

	const initNewChat = async () => {
		if (sessionStorage.selectedModels) {
			selectedModels = JSON.parse(sessionStorage.selectedModels);
			sessionStorage.removeItem('selectedModels');
		} else {
			if ($page.url.searchParams.get('models')) {
				selectedModels = $page.url.searchParams.get('models')?.split(',');
			} else if ($page.url.searchParams.get('model')) {
				const urlModels = $page.url.searchParams.get('model')?.split(',');

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
			} else if ($settings?.models) {
				selectedModels = $settings?.models;
			} else if ($config?.default_models) {
				console.log($config?.default_models.split(',') ?? '');
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

		await chatId.set('');
		await chatTitle.set('');

		history = {
			messages: {},
			currentId: null
		};

		chatFiles = [];
		params = {};

		if ($page.url.searchParams.get('youtube')) {
			uploadYoutubeTranscription(
				`https://www.youtube.com/watch?v=${$page.url.searchParams.get('youtube')}`
			);
		}
		if ($page.url.searchParams.get('web-search') === 'true') {
			webSearchEnabled = true;
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

	const createMessagesList = (responseMessageId) => {
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

	const chatCompletedHandler = async (chatId, modelId, responseMessageId, messages) => {
		await mermaid.run({
			querySelector: '.mermaid'
		});

		const res = await chatCompleted(localStorage.token, {
			model: modelId,
			messages: messages.map((m) => ({
				id: m.id,
				role: m.role,
				content: m.content,
				info: m.info ? m.info : undefined,
				timestamp: m.timestamp,
				...(m.sources ? { sources: m.sources } : {})
			})),
			chat_id: chatId,
			session_id: $socket?.id,
			id: responseMessageId
		}).catch((error) => {
			toast.error(error);
			messages.at(-1).error = { content: error };

			return null;
		});

		if (res !== null) {
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
	};

	const chatActionHandler = async (chatId, actionId, modelId, responseMessageId, event = null) => {
		const messages = createMessagesList(responseMessageId);

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
			chat_id: chatId,
			session_id: $socket?.id,
			id: responseMessageId
		}).catch((error) => {
			toast.error(error);
			messages.at(-1).error = { content: error };
			return null;
		});

		if (res !== null) {
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
				await initChatHandler();
			} else {
				await saveChatHandler($chatId);
			}
		}
	};

	//////////////////////////
	// Chat functions
	//////////////////////////

	const submitPrompt = async (userPrompt, { _raw = false } = {}) => {
		console.log('submitPrompt', userPrompt, $chatId);

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

		let _responses = [];
		prompt = '';
		await tick();

		// Reset chat input textarea
		const chatInputElement = document.getElementById('chat-input');

		if (chatInputElement) {
			chatInputElement.style.height = '';
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

		// Wait until history/message have been updated
		await tick();

		// focus on chat input
		const chatInput = document.getElementById('chat-input');
		chatInput?.focus();

		saveSessionSelectedModels();
		_responses = await sendPrompt(userPrompt, userMessageId, { newChat: true });

		return _responses;
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
		}

		let _responses: string[] = [];
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
				if (parentId !== null) {
					history.messages[parentId].childrenIds = [
						...history.messages[parentId].childrenIds,
						responseMessageId
					];
				}

				responseMessageIds[`${modelId}-${modelIdx ? modelIdx : _modelIdx}`] = responseMessageId;
			}
		}
		await tick();

		const _chatId = JSON.parse(JSON.stringify($chatId));
		await Promise.all(
			selectedModelIds.map(async (modelId, _modelIdx) => {
				console.log('modelId', modelId);
				const model = $models.filter((m) => m.id === modelId).at(0);

				if (model) {
					const messages = createMessagesList(parentId);
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
					let responseMessage = history.messages[responseMessageId];

					let userContext = null;
					if ($settings?.memory ?? false) {
						if (userContext === null) {
							const res = await queryMemory(localStorage.token, prompt).catch((error) => {
								toast.error(error);
								return null;
							});
							if (res) {
								if (res.documents[0].length > 0) {
									userContext = res.documents[0].reduce((acc, doc, index) => {
										const createdAtTimestamp = res.metadatas[0][index].created_at;
										const createdAtDate = new Date(createdAtTimestamp * 1000)
											.toISOString()
											.split('T')[0];
										return `${acc}${index + 1}. [${createdAtDate}]. ${doc}\n`;
									}, '');
								}

								console.log(userContext);
							}
						}
					}
					responseMessage.userContext = userContext;

					const chatEventEmitter = await getChatEventEmitter(model.id, _chatId);

					scrollToBottom();
					if (webSearchEnabled) {
						await getWebSearchResults(model.id, parentId, responseMessageId);
					}

					let _response = null;
					if (model?.owned_by === 'ollama') {
						_response = await sendPromptOllama(model, prompt, responseMessageId, _chatId);
					} else if (model) {
						_response = await sendPromptOpenAI(model, prompt, responseMessageId, _chatId);
					}
					_responses.push(_response);

					if (chatEventEmitter) clearInterval(chatEventEmitter);
				} else {
					toast.error($i18n.t(`Model {{modelId}} not found`, { modelId }));
				}
			})
		);

		currentChatPage.set(1);
		chats.set(await getChatList(localStorage.token, $currentChatPage));

		return _responses;
	};

	const sendPromptOllama = async (model, userPrompt, responseMessageId, _chatId) => {
		let _response: string | null = null;

		const responseMessage = history.messages[responseMessageId];
		const userMessage = history.messages[responseMessage.parentId];

		// Wait until history/message have been updated
		await tick();

		// Scroll down
		scrollToBottom();

		const messagesBody = [
			params?.system || $settings.system || (responseMessage?.userContext ?? null)
				? {
						role: 'system',
						content: `${promptTemplate(
							params?.system ?? $settings?.system ?? '',
							$user.name,
							$settings?.userLocation
								? await getAndUpdateUserLocation(localStorage.token)
								: undefined
						)}${
							(responseMessage?.userContext ?? null)
								? `\n\nUser Context:\n${responseMessage?.userContext ?? ''}`
								: ''
						}`
					}
				: undefined,
			...createMessagesList(responseMessageId)
		]
			.filter((message) => message?.content?.trim())
			.map((message) => {
				// Prepare the base message object
				const baseMessage = {
					role: message.role,
					content: message?.merged?.content ?? message.content
				};

				// Extract and format image URLs if any exist
				const imageUrls = message.files
					?.filter((file) => file.type === 'image')
					.map((file) => file.url.slice(file.url.indexOf(',') + 1));

				// Add images array only if it contains elements
				if (imageUrls && imageUrls.length > 0 && message.role === 'user') {
					baseMessage.images = imageUrls;
				}
				return baseMessage;
			});

		let lastImageIndex = -1;

		// Find the index of the last object with images
		messagesBody.forEach((item, index) => {
			if (item.images) {
				lastImageIndex = index;
			}
		});

		// Remove images from all but the last one
		messagesBody.forEach((item, index) => {
			if (index !== lastImageIndex) {
				delete item.images;
			}
		});

		let files = JSON.parse(JSON.stringify(chatFiles));
		if (model?.info?.meta?.knowledge ?? false) {
			// Only initialize and add status if knowledge exists
			responseMessage.statusHistory = [
				{
					action: 'knowledge_search',
					description: $i18n.t(`Searching Knowledge for "{{searchQuery}}"`, {
						searchQuery: userMessage.content
					}),
					done: false
				}
			];
			files.push(
				...model.info.meta.knowledge.map((item) => {
					if (item?.collection_name) {
						return {
							id: item.collection_name,
							name: item.name,
							legacy: true
						};
					} else if (item?.collection_names) {
						return {
							name: item.name,
							type: 'collection',
							collection_names: item.collection_names,
							legacy: true
						};
					} else {
						return item;
					}
				})
			);
			history.messages[responseMessageId] = responseMessage;
		}
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
		const [res, controller] = await generateChatCompletion(localStorage.token, {
			stream: stream,
			model: model.id,
			messages: messagesBody,
			options: {
				...{ ...($settings?.params ?? {}), ...params },
				stop:
					(params?.stop ?? $settings?.params?.stop ?? undefined)
						? (params?.stop.split(',').map((token) => token.trim()) ?? $settings.params.stop).map(
								(str) => decodeURIComponent(JSON.parse('"' + str.replace(/\"/g, '\\"') + '"'))
							)
						: undefined,
				num_predict: params?.max_tokens ?? $settings?.params?.max_tokens ?? undefined,
				repeat_penalty:
					params?.frequency_penalty ?? $settings?.params?.frequency_penalty ?? undefined
			},
			format: $settings.requestFormat ?? undefined,
			keep_alive: $settings.keepAlive ?? undefined,
			tool_ids: selectedToolIds.length > 0 ? selectedToolIds : undefined,
			files: files.length > 0 ? files : undefined,
			session_id: $socket?.id,
			chat_id: $chatId,
			id: responseMessageId
		});

		if (res && res.ok) {
			if (!stream) {
				const response = await res.json();
				console.log(response);

				responseMessage.content = response.message.content;
				responseMessage.info = {
					eval_count: response.eval_count,
					eval_duration: response.eval_duration,
					load_duration: response.load_duration,
					prompt_eval_count: response.prompt_eval_count,
					prompt_eval_duration: response.prompt_eval_duration,
					total_duration: response.total_duration
				};
				responseMessage.done = true;
			} else {
				console.log('controller', controller);

				const reader = res.body
					.pipeThrough(new TextDecoderStream())
					.pipeThrough(splitStream('\n'))
					.getReader();

				while (true) {
					const { value, done } = await reader.read();
					if (done || stopResponseFlag || _chatId !== $chatId) {
						responseMessage.done = true;
						history.messages[responseMessageId] = responseMessage;

						if (stopResponseFlag) {
							controller.abort('User: Stop Response');
						}

						_response = responseMessage.content;
						break;
					}

					try {
						let lines = value.split('\n');

						for (const line of lines) {
							if (line !== '') {
								console.log(line);
								let data = JSON.parse(line);

								if ('sources' in data) {
									responseMessage.sources = data.sources;
									// Only remove status if it was initially set
									if (model?.info?.meta?.knowledge ?? false) {
										responseMessage.statusHistory = responseMessage.statusHistory.filter(
											(status) => status.action !== 'knowledge_search'
										);
									}
									continue;
								}

								if ('detail' in data) {
									throw data;
								}

								if (data.done == false) {
									if (responseMessage.content == '' && data.message.content == '\n') {
										continue;
									} else {
										responseMessage.content += data.message.content;

										if (navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
											navigator.vibrate(5);
										}

										const messageContentParts = getMessageContentParts(
											responseMessage.content,
											$config?.audio?.tts?.split_on ?? 'punctuation'
										);
										messageContentParts.pop();

										// dispatch only last sentence and make sure it hasn't been dispatched before
										if (
											messageContentParts.length > 0 &&
											messageContentParts[messageContentParts.length - 1] !==
												responseMessage.lastSentence
										) {
											responseMessage.lastSentence =
												messageContentParts[messageContentParts.length - 1];
											eventTarget.dispatchEvent(
												new CustomEvent('chat', {
													detail: {
														id: responseMessageId,
														content: messageContentParts[messageContentParts.length - 1]
													}
												})
											);
										}

										history.messages[responseMessageId] = responseMessage;
									}
								} else {
									responseMessage.done = true;

									if (responseMessage.content == '') {
										responseMessage.error = {
											code: 400,
											content: `Oops! No text generated from Ollama, Please try again.`
										};
									}

									responseMessage.context = data.context ?? null;
									responseMessage.info = {
										total_duration: data.total_duration,
										load_duration: data.load_duration,
										sample_count: data.sample_count,
										sample_duration: data.sample_duration,
										prompt_eval_count: data.prompt_eval_count,
										prompt_eval_duration: data.prompt_eval_duration,
										eval_count: data.eval_count,
										eval_duration: data.eval_duration
									};

									history.messages[responseMessageId] = responseMessage;

									if ($settings.notificationEnabled && !document.hasFocus()) {
										const notification = new Notification(`${model.id}`, {
											body: responseMessage.content,
											icon: `${WEBUI_BASE_URL}/static/favicon.png`
										});
									}

									if ($settings?.responseAutoCopy ?? false) {
										copyToClipboard(responseMessage.content);
									}

									if ($settings.responseAutoPlayback && !$showCallOverlay) {
										await tick();
										document.getElementById(`speak-button-${responseMessage.id}`)?.click();
									}
								}
							}
						}
					} catch (error) {
						console.log(error);
						if ('detail' in error) {
							toast.error(error.detail);
						}
						break;
					}

					if (autoScroll) {
						scrollToBottom();
					}
				}
			}
		} else {
			if (res !== null) {
				const error = await res.json();
				console.log(error);
				if ('detail' in error) {
					toast.error(error.detail);
					responseMessage.error = { content: error.detail };
				} else {
					toast.error(error.error);
					responseMessage.error = { content: error.error };
				}
			} else {
				toast.error(
					$i18n.t(`Uh-oh! There was an issue connecting to {{provider}}.`, { provider: 'Ollama' })
				);
				responseMessage.error = {
					content: $i18n.t(`Uh-oh! There was an issue connecting to {{provider}}.`, {
						provider: 'Ollama'
					})
				};
			}
			responseMessage.done = true;

			if (responseMessage.statusHistory) {
				responseMessage.statusHistory = responseMessage.statusHistory.filter(
					(status) => status.action !== 'knowledge_search'
				);
			}
		}
		await saveChatHandler(_chatId);

		history.messages[responseMessageId] = responseMessage;

		await chatCompletedHandler(
			_chatId,
			model.id,
			responseMessageId,
			createMessagesList(responseMessageId)
		);

		stopResponseFlag = false;
		await tick();

		let lastMessageContentPart =
			getMessageContentParts(
				responseMessage.content,
				$config?.audio?.tts?.split_on ?? 'punctuation'
			)?.at(-1) ?? '';
		if (lastMessageContentPart) {
			eventTarget.dispatchEvent(
				new CustomEvent('chat', {
					detail: { id: responseMessageId, content: lastMessageContentPart }
				})
			);
		}

		eventTarget.dispatchEvent(
			new CustomEvent('chat:finish', {
				detail: {
					id: responseMessageId,
					content: responseMessage.content
				}
			})
		);

		if (autoScroll) {
			scrollToBottom();
		}

		const messages = createMessagesList(responseMessageId);
		if (messages.length == 2 && messages.at(-1).content !== '' && selectedModels[0] === model.id) {
			window.history.replaceState(history.state, '', `/c/${_chatId}`);

			const title = await generateChatTitle(messages);
			await setChatTitle(_chatId, title);

			if ($settings?.autoTags ?? true) {
				await setChatTags(messages);
			}
		}

		return _response;
	};

	const sendPromptOpenAI = async (model, userPrompt, responseMessageId, _chatId) => {
		let _response = null;

		const responseMessage = history.messages[responseMessageId];
		const userMessage = history.messages[responseMessage.parentId];

		let files = JSON.parse(JSON.stringify(chatFiles));
		if (model?.info?.meta?.knowledge ?? false) {
			// Only initialize and add status if knowledge exists
			responseMessage.statusHistory = [
				{
					action: 'knowledge_search',
					description: $i18n.t(`Searching Knowledge for "{{searchQuery}}"`, {
						searchQuery: userMessage.content
					}),
					done: false
				}
			];
			files.push(
				...model.info.meta.knowledge.map((item) => {
					if (item?.collection_name) {
						return {
							id: item.collection_name,
							name: item.name,
							legacy: true
						};
					} else if (item?.collection_names) {
						return {
							name: item.name,
							type: 'collection',
							collection_names: item.collection_names,
							legacy: true
						};
					} else {
						return item;
					}
				})
			);
			history.messages[responseMessageId] = responseMessage;
		}
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

		try {
			const stream =
				model?.info?.params?.stream_response ??
				$settings?.params?.stream_response ??
				params?.stream_response ??
				true;

			const [res, controller] = await generateOpenAIChatCompletion(
				localStorage.token,
				{
					stream: stream,
					model: model.id,
					...(stream && (model.info?.meta?.capabilities?.usage ?? false)
						? {
								stream_options: {
									include_usage: true
								}
							}
						: {}),
					messages: [
						params?.system || $settings.system || (responseMessage?.userContext ?? null)
							? {
									role: 'system',
									content: `${promptTemplate(
										params?.system ?? $settings?.system ?? '',
										$user.name,
										$settings?.userLocation
											? await getAndUpdateUserLocation(localStorage.token)
											: undefined
									)}${
										(responseMessage?.userContext ?? null)
											? `\n\nUser Context:\n${responseMessage?.userContext ?? ''}`
											: ''
									}`
								}
							: undefined,
						...createMessagesList(responseMessageId)
					]
						.filter((message) => message?.content?.trim())
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
						})),
					seed: params?.seed ?? $settings?.params?.seed ?? undefined,
					stop:
						(params?.stop ?? $settings?.params?.stop ?? undefined)
							? (params?.stop.split(',').map((token) => token.trim()) ?? $settings.params.stop).map(
									(str) => decodeURIComponent(JSON.parse('"' + str.replace(/\"/g, '\\"') + '"'))
								)
							: undefined,
					temperature: params?.temperature ?? $settings?.params?.temperature ?? undefined,
					top_p: params?.top_p ?? $settings?.params?.top_p ?? undefined,
					frequency_penalty:
						params?.frequency_penalty ?? $settings?.params?.frequency_penalty ?? undefined,
					max_tokens: params?.max_tokens ?? $settings?.params?.max_tokens ?? undefined,
					tool_ids: selectedToolIds.length > 0 ? selectedToolIds : undefined,
					files: files.length > 0 ? files : undefined,
					session_id: $socket?.id,
					chat_id: $chatId,
					id: responseMessageId
				},
				`${WEBUI_BASE_URL}/api`
			);

			// Wait until history/message have been updated
			await tick();

			scrollToBottom();

			if (res && res.ok && res.body) {
				if (!stream) {
					const response = await res.json();
					console.log(response);

					responseMessage.content = response.choices[0].message.content;
					responseMessage.info = { ...response.usage, openai: true };
					responseMessage.done = true;
				} else {
					const textStream = await createOpenAITextStream(res.body, $settings.splitLargeChunks);

					for await (const update of textStream) {
						const { value, done, sources, selectedModelId, error, usage } = update;
						if (error) {
							await handleOpenAIError(error, null, model, responseMessage);
							break;
						}
						if (done || stopResponseFlag || _chatId !== $chatId) {
							responseMessage.done = true;
							history.messages[responseMessageId] = responseMessage;

							if (stopResponseFlag) {
								controller.abort('User: Stop Response');
							}
							_response = responseMessage.content;
							break;
						}

						if (usage) {
							responseMessage.info = { ...usage, openai: true, usage };
						}

						if (selectedModelId) {
							responseMessage.selectedModelId = selectedModelId;
							responseMessage.arena = true;
							continue;
						}

						if (sources) {
							responseMessage.sources = sources;
							// Only remove status if it was initially set
							if (model?.info?.meta?.knowledge ?? false) {
								responseMessage.statusHistory = responseMessage.statusHistory.filter(
									(status) => status.action !== 'knowledge_search'
								);
							}
							continue;
						}

						if (responseMessage.content == '' && value == '\n') {
							continue;
						} else {
							responseMessage.content += value;

							if (navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
								navigator.vibrate(5);
							}

							const messageContentParts = getMessageContentParts(
								responseMessage.content,
								$config?.audio?.tts?.split_on ?? 'punctuation'
							);
							messageContentParts.pop();

							// dispatch only last sentence and make sure it hasn't been dispatched before
							if (
								messageContentParts.length > 0 &&
								messageContentParts[messageContentParts.length - 1] !== responseMessage.lastSentence
							) {
								responseMessage.lastSentence = messageContentParts[messageContentParts.length - 1];
								eventTarget.dispatchEvent(
									new CustomEvent('chat', {
										detail: {
											id: responseMessageId,
											content: messageContentParts[messageContentParts.length - 1]
										}
									})
								);
							}

							history.messages[responseMessageId] = responseMessage;
						}

						if (autoScroll) {
							scrollToBottom();
						}
					}
				}

				if ($settings.notificationEnabled && !document.hasFocus()) {
					const notification = new Notification(`${model.id}`, {
						body: responseMessage.content,
						icon: `${WEBUI_BASE_URL}/static/favicon.png`
					});
				}

				if ($settings.responseAutoCopy) {
					copyToClipboard(responseMessage.content);
				}

				if ($settings.responseAutoPlayback && !$showCallOverlay) {
					await tick();

					document.getElementById(`speak-button-${responseMessage.id}`)?.click();
				}
			} else {
				await handleOpenAIError(null, res, model, responseMessage);
			}
		} catch (error) {
			await handleOpenAIError(error, null, model, responseMessage);
		}

		await saveChatHandler(_chatId);

		history.messages[responseMessageId] = responseMessage;

		await chatCompletedHandler(
			_chatId,
			model.id,
			responseMessageId,
			createMessagesList(responseMessageId)
		);

		stopResponseFlag = false;
		await tick();

		let lastMessageContentPart =
			getMessageContentParts(
				responseMessage.content,
				$config?.audio?.tts?.split_on ?? 'punctuation'
			)?.at(-1) ?? '';
		if (lastMessageContentPart) {
			eventTarget.dispatchEvent(
				new CustomEvent('chat', {
					detail: { id: responseMessageId, content: lastMessageContentPart }
				})
			);
		}

		eventTarget.dispatchEvent(
			new CustomEvent('chat:finish', {
				detail: {
					id: responseMessageId,
					content: responseMessage.content
				}
			})
		);

		if (autoScroll) {
			scrollToBottom();
		}

		const messages = createMessagesList(responseMessageId);
		if (messages.length == 2 && selectedModels[0] === model.id) {
			window.history.replaceState(history.state, '', `/c/${_chatId}`);

			const title = await generateChatTitle(messages);
			await setChatTitle(_chatId, title);

			if ($settings?.autoTags ?? true) {
				await setChatTags(messages);
			}
		}

		return _response;
	};

	const handleOpenAIError = async (error, res: Response | null, model, responseMessage) => {
		let errorMessage = '';
		let innerError;

		if (error) {
			innerError = error;
		} else if (res !== null) {
			innerError = await res.json();
		}
		console.error(innerError);
		if ('detail' in innerError) {
			toast.error(innerError.detail);
			errorMessage = innerError.detail;
		} else if ('error' in innerError) {
			if ('message' in innerError.error) {
				toast.error(innerError.error.message);
				errorMessage = innerError.error.message;
			} else {
				toast.error(innerError.error);
				errorMessage = innerError.error;
			}
		} else if ('message' in innerError) {
			toast.error(innerError.message);
			errorMessage = innerError.message;
		}

		responseMessage.error = {
			content:
				$i18n.t(`Uh-oh! There was an issue connecting to {{provider}}.`, {
					provider: model.name ?? model.id
				}) +
				'\n' +
				errorMessage
		};
		responseMessage.done = true;

		if (responseMessage.statusHistory) {
			responseMessage.statusHistory = responseMessage.statusHistory.filter(
				(status) => status.action !== 'knowledge_search'
			);
		}

		history.messages[responseMessage.id] = responseMessage;
	};

	const stopResponse = () => {
		stopResponseFlag = true;
		console.log('stopResponse');
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

	const regenerateResponse = async (message) => {
		console.log('regenerateResponse');

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
				if (model?.owned_by === 'openai') {
					await sendPromptOpenAI(
						model,
						history.messages[responseMessage.parentId].content,
						responseMessage.id,
						_chatId
					);
				} else
					await sendPromptOllama(
						model,
						history.messages[responseMessage.parentId].content,
						responseMessage.id,
						_chatId
					);
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

				await saveChatHandler(_chatId);
			} else {
				console.error(res);
			}
		} catch (e) {
			console.error(e);
		}
	};

	const generateChatTitle = async (messages) => {
		const lastUserMessage = messages.filter((message) => message.role === 'user').at(-1);

		if ($settings?.title?.auto ?? true) {
			const modelId = selectedModels[0];

			const title = await generateTitle(localStorage.token, modelId, messages, $chatId).catch(
				(error) => {
					console.error(error);
					return lastUserMessage?.content ?? 'New Chat';
				}
			);

			return title ? title : (lastUserMessage?.content ?? 'New Chat');
		} else {
			return lastUserMessage?.content ?? 'New Chat';
		}
	};

	const setChatTitle = async (_chatId, title) => {
		if (_chatId === $chatId) {
			chatTitle.set(title);
		}

		if (!$temporaryChatEnabled) {
			chat = await updateChatById(localStorage.token, _chatId, { title: title });

			currentChatPage.set(1);
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
		}
	};

	const setChatTags = async (messages) => {
		if (!$temporaryChatEnabled) {
			const currentTags = await getTagsById(localStorage.token, $chatId);
			if (currentTags.length > 0) {
				const res = await deleteTagsById(localStorage.token, $chatId);
				if (res) {
					allTags.set(await getAllTags(localStorage.token));
				}
			}

			const lastMessage = messages.at(-1);
			const modelId = selectedModels[0];

			let generatedTags = await generateTags(localStorage.token, modelId, messages, $chatId).catch(
				(error) => {
					console.error(error);
					return [];
				}
			);

			generatedTags = generatedTags.filter(
				(tag) => !currentTags.find((t) => t.id === tag.replaceAll(' ', '_').toLowerCase())
			);
			console.log(generatedTags);

			for (const tag of generatedTags) {
				await addTagById(localStorage.token, $chatId, tag);
			}

			chat = await getChatById(localStorage.token, $chatId);
			allTags.set(await getAllTags(localStorage.token));
		}
	};

	const getWebSearchResults = async (
		model: string,
		parentId: string,
		responseMessageId: string
	) => {
		// TODO: move this to the backend
		const responseMessage = history.messages[responseMessageId];
		const userMessage = history.messages[parentId];
		const messages = createMessagesList(history.currentId);

		responseMessage.statusHistory = [
			{
				done: false,
				action: 'web_search',
				description: $i18n.t('Generating search query')
			}
		];
		history.messages[responseMessageId] = responseMessage;

		const prompt = userMessage.content;
		let queries = await generateQueries(
			localStorage.token,
			model,
			messages.filter((message) => message?.content?.trim()),
			prompt
		).catch((error) => {
			console.log(error);
			return [prompt];
		});

		if (queries.length === 0) {
			responseMessage.statusHistory.push({
				done: true,
				error: true,
				action: 'web_search',
				description: $i18n.t('No search query generated')
			});
			history.messages[responseMessageId] = responseMessage;
			return;
		}

		const searchQuery = queries[0];

		responseMessage.statusHistory.push({
			done: false,
			action: 'web_search',
			description: $i18n.t(`Searching "{{searchQuery}}"`, { searchQuery })
		});
		history.messages[responseMessageId] = responseMessage;

		const results = await processWebSearch(localStorage.token, searchQuery).catch((error) => {
			console.log(error);
			toast.error(error);

			return null;
		});

		if (results) {
			responseMessage.statusHistory.push({
				done: true,
				action: 'web_search',
				description: $i18n.t('Searched {{count}} sites', { count: results.filenames.length }),
				query: searchQuery,
				urls: results.filenames
			});

			if (responseMessage?.files ?? undefined === undefined) {
				responseMessage.files = [];
			}

			responseMessage.files.push({
				collection_name: results.collection_name,
				name: searchQuery,
				type: 'web_search_results',
				urls: results.filenames
			});
			history.messages[responseMessageId] = responseMessage;
		} else {
			responseMessage.statusHistory.push({
				done: true,
				error: true,
				action: 'web_search',
				description: 'No search results found'
			});
			history.messages[responseMessageId] = responseMessage;
		}
	};

	const initChatHandler = async () => {
		if (!$temporaryChatEnabled) {
			chat = await createNewChat(localStorage.token, {
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
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
			await chatId.set(chat.id);
		} else {
			await chatId.set('local');
		}
		await tick();
	};

	const saveChatHandler = async (_chatId) => {
		if ($chatId == _chatId) {
			if (!$temporaryChatEnabled) {
				chat = await updateChatById(localStorage.token, _chatId, {
					models: selectedModels,
					history: history,
					messages: createMessagesList(history.currentId),
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

{#if !chatIdProp || (loaded && chatIdProp)}
	<div
		class="h-screen max-h-[100dvh] {$showSidebar
			? 'md:max-w-[calc(100%-260px)]'
			: ''} w-full max-w-full flex flex-col"
		id="chat-container"
	>
		{#if $settings?.backgroundImageUrl ?? null}
			<div
				class="absolute {$showSidebar
					? 'md:max-w-[calc(100%-260px)] md:translate-x-[260px]'
					: ''} top-0 left-0 w-full h-full bg-cover bg-center bg-no-repeat"
				style="background-image: url({$settings.backgroundImageUrl})  "
			/>

			<div
				class="absolute top-0 left-0 w-full h-full bg-gradient-to-t from-white to-white/85 dark:from-gray-900 dark:to-[#171717]/90 z-0"
			/>
		{/if}

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
							{#each $banners.filter( (b) => (b.dismissible ? !JSON.parse(localStorage.getItem('dismissedBannerIds') ?? '[]').includes(b.id) : true) ) as banner}
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
									{sendPrompt}
									{showMessage}
									{submitMessage}
									{continueResponse}
									{regenerateResponse}
									{mergeResponses}
									{chatActionHandler}
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
								bind:webSearchEnabled
								bind:atSelectedModel
								transparentBackground={$settings?.backgroundImageUrl ?? false}
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
								bind:webSearchEnabled
								bind:atSelectedModel
								transparentBackground={$settings?.backgroundImageUrl ?? false}
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
	</div>
{/if}

<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';
	import { config, settings, user as _user, mobile, temporaryChatEnabled } from '$lib/stores';
	import { refreshChatList } from '$lib/stores/chatList';
	import { tick, getContext, onMount, onDestroy, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import { toast } from 'svelte-sonner';
	import {
		deleteChatMessageById,
		getChatHistoryWindow,
		updateChatByIdWindow,
		updateChatMessageById
	} from '$lib/apis/chats';
	import { copyToClipboard, extractCurlyBraceWords } from '$lib/utils';
	import {
		createMessagePatch,
		DEFAULT_CHAT_MESSAGE_WINDOW,
		isChatMessageLoaded,
		mergeChatHistoryWindow,
		serializeChatForWindowSave
	} from '$lib/utils/chatHistoryWindow';

	import Message from './Messages/Message.svelte';
	import Loader from '../common/Loader.svelte';
	import Spinner from '../common/Spinner.svelte';

	import ChatPlaceholder from './ChatPlaceholder.svelte';

	const i18n: any = getContext('i18n');

	type ChatHistoryState = {
		currentId: string | null;
		messages: Record<string, any>;
		messageWindow?: {
			loadedIds?: string[];
			hasMore?: boolean;
			[key: string]: unknown;
		};
		[key: string]: unknown;
	};

	export let className = 'h-full flex pt-18';

	export let chatId = '';
	export let user = $_user;

	export let prompt;
	export let history: ChatHistoryState = { messages: {}, currentId: null };
	export let selectedModels;
	export let atSelectedModel;

	let messages: any[] = [];

	export let setInputText: Function = () => {};

	export let sendMessage: Function;
	export let continueResponse: Function;
	export let regenerateResponse: Function;
	export let mergeResponses: Function;

	export let chatActionHandler: Function;
	export let showMessage: Function = () => {};
	export let submitMessage: Function = () => {};
	export let addMessages: Function = () => {};
	export let forkHandler: Function | null = null;

	export let readOnly = false;
	export let preview = false;
	export let editCodeBlock = true;

	export let topPadding = false;
	export let bottomPadding = false;
	export let autoScroll: boolean;
	export let messagesContainerId = 'messages-container';

	export let onSelect = (e: any) => {};
	export let onInsertToNote: ((content: string) => void) | null = null;

	export let messagesCount: number | null = 8;
	let messagesLoading = false;
	let destroyed = false;
	const historyWindowRequests = new Map<string, Promise<boolean>>();
	const branchHasMoreByCurrentId = new Map<string, boolean>();
	let pendingRebuild: number | null = null;
	let lastCurrentId: string | null = null;
	let branchNavigationGeneration = 0;
	let historyGeneration = 0;
	let observedHistory = history;
	let observedChatId = chatId;

	const getMessagesContainer = () => document.getElementById(messagesContainerId);

	const resetLazyPaginationState = () => {
		messagesCount = 8;
		messagesLoading = false;
		branchNavigationGeneration += 1;
		historyGeneration += 1;
		historyWindowRequests.clear();
		branchHasMoreByCurrentId.clear();
		lastCurrentId = null;
		if (pendingRebuild !== null) cancelAnimationFrame(pendingRebuild);
		pendingRebuild = null;
	};

	const setMergedHistory = (nextHistory: ChatHistoryState) => {
		observedHistory = nextHistory;
		history = nextHistory;
	};

	const replaceHistory = (nextHistory: ChatHistoryState) => {
		resetLazyPaginationState();
		observedHistory = nextHistory;
		observedChatId = chatId;
		history = nextHistory;
	};

	const observeHistoryReplacement = (nextHistory: ChatHistoryState, nextChatId: string) => {
		if (nextHistory === observedHistory && nextChatId === observedChatId) return;

		resetLazyPaginationState();
		observedHistory = nextHistory;
		observedChatId = nextChatId;
	};

	onDestroy(() => {
		destroyed = true;
		branchNavigationGeneration += 1;
		historyGeneration += 1;
		historyWindowRequests.clear();
		branchHasMoreByCurrentId.clear();
		if (pendingRebuild !== null) cancelAnimationFrame(pendingRebuild);
	});

	$: observeHistoryReplacement(history, chatId);

	const getBranchLoadState = (currentId = history?.currentId) => {
		let loadedCount = 0;
		let earliestLoadedId: string | null = null;
		let blockedId: string | null = null;
		let reachedRoot = false;
		let messageId = currentId;
		const visited = new Set<string>();

		while (messageId) {
			if (visited.has(messageId)) {
				reachedRoot = true;
				break;
			}
			visited.add(messageId);

			const message = history?.messages?.[messageId];
			if (!message || !isChatMessageLoaded(history, messageId)) {
				blockedId = messageId;
				break;
			}

			loadedCount += 1;
			earliestLoadedId = messageId;
			if (message.parentId === null || message.parentId === undefined) {
				reachedRoot = true;
				break;
			}
			messageId = message.parentId;
		}

		return { loadedCount, earliestLoadedId, blockedId, reachedRoot };
	};

	const hydrateHistoryWindow = async (currentId: string, beforeId?: string) => {
		if (
			!currentId ||
			!history?.messageWindow ||
			$temporaryChatEnabled ||
			!chatId ||
			chatId.startsWith('local:')
		) {
			return true;
		}

		const requestChatId = chatId;
		const requestGeneration = historyGeneration;
		const requestKey = `${requestGeneration}:${requestChatId}:${currentId}:${beforeId ?? ''}`;
		const pendingRequest = historyWindowRequests.get(requestKey);
		if (pendingRequest) return await pendingRequest;

		const request = (async () => {
			try {
				const historyWindow = await getChatHistoryWindow(
					localStorage.token,
					requestChatId,
					currentId,
					DEFAULT_CHAT_MESSAGE_WINDOW,
					beforeId
				);
				if (
					!historyWindow ||
					destroyed ||
					chatId !== requestChatId ||
					historyGeneration !== requestGeneration
				) {
					return false;
				}

				const activeCurrentId = history.currentId;
				branchHasMoreByCurrentId.set(currentId, historyWindow.hasMore);
				const mergedHistory = mergeChatHistoryWindow(history, historyWindow) as ChatHistoryState;
				mergedHistory.currentId = activeCurrentId;
				if (currentId !== activeCurrentId && mergedHistory.messageWindow) {
					mergedHistory.messageWindow.hasMore = history.messageWindow?.hasMore;
				}
				setMergedHistory(mergedHistory);
				return true;
			} catch (error) {
				console.error('Failed to load chat history window', error);
				toast.error($i18n.t('Failed to load chat'));
				return false;
			} finally {
				historyWindowRequests.delete(requestKey);
			}
		})();

		historyWindowRequests.set(requestKey, request);
		return await request;
	};

	const ensureLoadedAncestors = async (targetCount: number) => {
		while (true) {
			const state = getBranchLoadState();
			if (state.loadedCount >= targetCount || state.reachedRoot) return true;
			if (!state.earliestLoadedId || history?.messageWindow?.hasMore === false) return false;

			const currentId = history.currentId;
			if (!currentId) return false;
			const loaded = await hydrateHistoryWindow(currentId, state.earliestLoadedId);
			if (!loaded) return false;

			const nextState = getBranchLoadState();
			if (nextState.loadedCount <= state.loadedCount) return false;
		}
	};

	const loadMoreMessages = async () => {
		if (messagesLoading || messagesCount === null) return;

		// scroll slightly down to disable continuous loading
		const element = getMessagesContainer();
		if (element) element.scrollTop += 100;

		messagesLoading = true;
		try {
			const nextCount = messagesCount + 8;
			if (!(await ensureLoadedAncestors(nextCount))) return;

			messagesCount = nextCount;
			buildMessages();
			await tick();
		} finally {
			messagesLoading = false;
		}
	};

	const buildMessages = () => {
		let _messages = [];

		let message = history.currentId ? history.messages[history.currentId] : null;
		const visitedMessageIds = new Set();

		while (message && (messagesCount !== null ? _messages.length < messagesCount : true)) {
			if (visitedMessageIds.has(message.id)) {
				console.warn('Circular dependency detected in message history', message.id);
				break;
			}
			visitedMessageIds.add(message.id);

			if (!isChatMessageLoaded(history, message.id)) break;
			_messages.push(message);
			message = message.parentId !== null ? history.messages[message.parentId] : null;
		}

		messages = _messages.reverse();
	};

	// Throttle message list rebuilds to once per animation frame during streaming.
	// Structural changes (currentId change) always rebuild immediately.
	const handleHistoryChange = (currentId: string | null, _messages: Record<string, any>) => {
		if (!currentId) {
			messages = [];
			return;
		}

		const currentIdChanged = currentId !== lastCurrentId;
		lastCurrentId = currentId;

		if (currentIdChanged) {
			// Structural change: new chat, navigation, new message — rebuild immediately
			if (pendingRebuild !== null) cancelAnimationFrame(pendingRebuild);
			pendingRebuild = null;
			buildMessages();
		} else if (_messages) {
			// Content update (streaming) — throttle to once per frame
			if (!pendingRebuild) {
				pendingRebuild = requestAnimationFrame(() => {
					pendingRebuild = null;
					buildMessages();
				});
			}
		}
	};

	$: handleHistoryChange(history.currentId, history.messages);

	$: if (autoScroll && bottomPadding) {
		(async () => {
			await tick();
			scrollToBottom();
		})();
	}

	const scrollToBottom = () => {
		const element = getMessagesContainer();
		if (element) {
			element.scrollTop = element.scrollHeight;

			// Follow-up scroll to account for content-visibility: auto re-layouts
			requestAnimationFrame(() => {
				if (element) {
					element.scrollTop = element.scrollHeight;
				}
			});
		}
	};

	export const scrollToTop = async () => {
		if (messagesLoading) return;

		messagesLoading = true;
		try {
			while (true) {
				const state = getBranchLoadState();
				if (state.reachedRoot) break;
				if (!state.earliestLoadedId || history?.messageWindow?.hasMore === false) return;

				const currentId = history.currentId;
				if (!currentId) return;
				const loaded = await hydrateHistoryWindow(currentId, state.earliestLoadedId);
				if (!loaded) return;

				const nextState = getBranchLoadState();
				if (nextState.loadedCount <= state.loadedCount) return;
			}

			messagesCount = null;
			buildMessages();
			await tick();
			if (messages.length > 0) {
				const firstMessageEl = document.getElementById(`message-${messages[0].id}`);
				if (firstMessageEl) {
					firstMessageEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
				}
			}
		} finally {
			messagesLoading = false;
		}
	};

	const updateChat = async () => {
		if (!$temporaryChatEnabled) {
			history = history;
			await tick();
			const payload = serializeChatForWindowSave({
				history: history,
				messages: messages
			});
			await updateChatByIdWindow(localStorage.token, chatId, payload);

			await refreshChatList(localStorage.token);
		}
	};

	const getSiblingIds = (message: any): string[] =>
		message.parentId !== null
			? (history.messages[message.parentId]?.childrenIds ?? [])
			: Object.values(history.messages)
					.filter((candidate) => candidate.parentId === null)
					.map((candidate) => candidate.id);

	const getDeepestLeafId = (messageId: string) => {
		const visited = new Set<string>();
		let leafId = messageId;

		while (leafId && !visited.has(leafId)) {
			visited.add(leafId);
			const childrenIds = history.messages[leafId]?.childrenIds ?? [];
			if (childrenIds.length === 0) break;
			leafId = childrenIds.at(-1);
		}

		return leafId;
	};

	const ensureMessageLoaded = async (messageId: string) => {
		if (!messageId || isChatMessageLoaded(history, messageId)) return true;
		return await hydrateHistoryWindow(messageId);
	};

	const scrollAfterBranchChange = async () => {
		await tick();
		if (!($settings?.scrollOnBranchChange ?? true)) return;

		const element = getMessagesContainer();
		if (element) {
			autoScroll = element.scrollHeight - element.scrollTop <= element.clientHeight + 50;
		}

		setTimeout(() => {
			scrollToBottom();
		}, 100);
	};

	const switchToBranchLeaf = async (messageId: string) => {
		if (!messageId) return false;
		const navigationGeneration = ++branchNavigationGeneration;
		if (messageId === history.currentId) return true;
		if (!(await ensureMessageLoaded(messageId))) return false;
		if (navigationGeneration !== branchNavigationGeneration) return false;

		messagesCount = 8;
		history.currentId = messageId;
		const targetHasMore = branchHasMoreByCurrentId.get(messageId);
		if (typeof targetHasMore === 'boolean' && history.messageWindow) {
			history.messageWindow.hasMore = targetHasMore;
		}
		history = history;
		await scrollAfterBranchChange();
		return true;
	};

	const gotoMessage = async (message: any, idx: number) => {
		const siblings = getSiblingIds(message);
		if (siblings.length === 0) return;

		const siblingIndex = Math.max(0, Math.min(idx, siblings.length - 1));
		const leafId = getDeepestLeafId(siblings[siblingIndex]);
		await switchToBranchLeaf(leafId);
	};

	const showPreviousMessage = async (message: any) => {
		const siblings = getSiblingIds(message);
		if (siblings.length === 0) return;

		const siblingIndex = Math.max(siblings.indexOf(message.id) - 1, 0);
		const leafId = getDeepestLeafId(siblings[siblingIndex]);
		await switchToBranchLeaf(leafId);
	};

	const showNextMessage = async (message: any) => {
		const siblings = getSiblingIds(message);
		if (siblings.length === 0) return;

		const siblingIndex = Math.min(siblings.indexOf(message.id) + 1, siblings.length - 1);
		const leafId = getDeepestLeafId(siblings[siblingIndex]);
		await switchToBranchLeaf(leafId);
	};

	const rateMessage = async (messageId, rating) => {
		await saveMessage(messageId, {
			...history.messages[messageId],
			annotation: {
				...history.messages[messageId].annotation,
				rating: rating
			}
		});
	};

	const editMessage = async (messageId, { content, files, output = undefined }, submit = true) => {
		if (submit && (selectedModels ?? []).filter((id) => id).length === 0) {
			toast.error($i18n.t('Model not selected'));
			return;
		}
		if (history.messages[messageId].role === 'user') {
			if (submit) {
				// New user message
				let userPrompt = content;
				let userMessageId = uuidv4();

				let userMessage = {
					id: userMessageId,
					parentId: history.messages[messageId].parentId,
					childrenIds: [],
					role: 'user',
					content: userPrompt,
					...(files && { files: files }),
					models: selectedModels,
					timestamp: Math.floor(Date.now() / 1000) // Unix epoch
				};

				let messageParentId = history.messages[messageId].parentId;

				if (messageParentId !== null) {
					history.messages[messageParentId].childrenIds = [
						...history.messages[messageParentId].childrenIds,
						userMessageId
					];
				}

				history.messages[userMessageId] = userMessage;
				history.currentId = userMessageId;

				await tick();
				await sendMessage(history, userMessageId);
			} else {
				// Edit user message
				await saveMessage(messageId, {
					...history.messages[messageId],
					content,
					files
				});
			}
		} else {
			if (submit) {
				// New response message (Save As Copy)
				const responseMessageId = uuidv4();
				const message = history.messages[messageId];
				const parentId = message.parentId;

				const responseMessage = {
					...message,
					id: responseMessageId,
					parentId: parentId,
					childrenIds: [],
					files: undefined,
					content: output !== undefined ? '' : content,
					...(output !== undefined ? { output } : {}),
					timestamp: Math.floor(Date.now() / 1000) // Unix epoch
				};

				history.messages[responseMessageId] = responseMessage;
				history.currentId = responseMessageId;

				// Append messageId to childrenIds of parent message
				if (parentId !== null) {
					history.messages[parentId].childrenIds = [
						...history.messages[parentId].childrenIds,
						responseMessageId
					];
				}

				await updateChat();
			} else {
				// Edit response message
				const updatedMessage = { ...history.messages[messageId] };
				if (content !== undefined) {
					updatedMessage.originalContent = history.messages[messageId].content;
					updatedMessage.content = content;
				}
				if (output !== undefined) {
					updatedMessage.output = output;
					updatedMessage.content = '';
				}
				await saveMessage(messageId, updatedMessage);
			}
		}
	};

	const actionMessage = async (actionId, message, event = null) => {
		await chatActionHandler(chatId, actionId, message.model, message.id, event);
	};

	const saveMessage = async (messageId, message) => {
		if (!history.messages?.[messageId]) {
			return null;
		}

		const previousMessage = structuredClone(history.messages[messageId]);
		const messagePatch = createMessagePatch(previousMessage, message);
		history.messages[messageId] = { ...structuredClone(message), __loaded: true };
		history = history;
		await tick();

		if ($temporaryChatEnabled) {
			return history.messages[messageId];
		}
		if (Object.keys(messagePatch).length === 0) {
			return history.messages[messageId];
		}

		try {
			const savedMessage = await updateChatMessageById(
				localStorage.token,
				chatId,
				messageId,
				messagePatch
			);

			if (savedMessage) {
				history.messages[messageId] = {
					...history.messages[messageId],
					...savedMessage,
					__loaded: true
				};
				history = history;
				await tick();
			}

			void refreshChatList(localStorage.token);
			return savedMessage;
		} catch (error) {
			history.messages[messageId] = previousMessage;
			history = history;
			await tick();
			toast.error(`${error}`);
			throw error;
		}
	};

	const deleteMessage = async (messageId) => {
		const messageToDelete = history.messages[messageId];
		if (!messageToDelete) return;

		if (!$temporaryChatEnabled) {
			try {
				const response = await deleteChatMessageById(localStorage.token, chatId, messageId);
				let nextHistory = response?.chat?.history as ChatHistoryState | undefined;

				if (nextHistory?.currentId && !isChatMessageLoaded(nextHistory, nextHistory.currentId)) {
					const historyWindow = await getChatHistoryWindow(
						localStorage.token,
						chatId,
						nextHistory.currentId,
						DEFAULT_CHAT_MESSAGE_WINDOW
					);
					nextHistory = mergeChatHistoryWindow(nextHistory, historyWindow) as ChatHistoryState;
				}

				if (nextHistory) replaceHistory(nextHistory);
				void refreshChatList(localStorage.token);
			} catch (error) {
				toast.error(`${error}`);
			}
			return;
		}

		const parentMessageId = messageToDelete.parentId;
		const childMessageIds = messageToDelete.childrenIds ?? [];

		// Collect all grandchildren
		const grandchildrenIds = childMessageIds.flatMap(
			(childId) => history.messages[childId]?.childrenIds ?? []
		);

		// Update parent's children
		if (parentMessageId && history.messages[parentMessageId]) {
			history.messages[parentMessageId].childrenIds = [
				...history.messages[parentMessageId].childrenIds.filter((id) => id !== messageId),
				...grandchildrenIds
			];
		}

		// Update grandchildren's parent
		grandchildrenIds.forEach((grandchildId) => {
			if (history.messages[grandchildId]) {
				history.messages[grandchildId].parentId = parentMessageId;
			}
		});

		// Delete the message and its children
		[messageId, ...childMessageIds].forEach((id) => {
			delete history.messages[id];
		});

		let nextMessageId = parentMessageId;
		let nextChildrenIds =
			nextMessageId === null
				? Object.keys(history.messages).filter((id) => history.messages[id].parentId === null)
				: (history.messages[nextMessageId]?.childrenIds ?? []);
		while (nextChildrenIds.length > 0) {
			nextMessageId = nextChildrenIds.at(-1);
			nextChildrenIds = history.messages[nextMessageId]?.childrenIds ?? [];
		}
		history.currentId = nextMessageId;
		history = history;
	};

	const triggerScroll = () => {
		if (autoScroll) {
			const element = getMessagesContainer();
			if (element) {
				autoScroll = element.scrollHeight - element.scrollTop <= element.clientHeight + 50;
				setTimeout(() => {
					scrollToBottom();
				}, 100);
			}
		}
	};
</script>

<div class={className}>
	{#if Object.keys(history?.messages ?? {}).length == 0}
		<ChatPlaceholder modelIds={selectedModels} {atSelectedModel} {onSelect} />
	{:else}
		<div class="w-full pt-2">
			{#key chatId}
				<section class="w-full" aria-labelledby="chat-conversation">
					<h2 class="sr-only" id="chat-conversation">{$i18n.t('Chat Conversation')}</h2>
					{#if messages.at(0)?.parentId !== null}
						<Loader
							on:visible={(e) => {
								console.log('visible');
								if (!messagesLoading) {
									loadMoreMessages();
								}
							}}
						>
							<div class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2">
								<Spinner className=" size-4" />
								<div class=" ">{$i18n.t('Loading...')}</div>
							</div>
						</Loader>
					{/if}
					<ul role="log" aria-live="polite" aria-relevant="additions" aria-atomic="false">
						{#each messages as message, messageIdx (message.id)}
							<Message
								{chatId}
								bind:history
								{selectedModels}
								messageId={message.id}
								idx={messageIdx}
								{user}
								{setInputText}
								{gotoMessage}
								{showPreviousMessage}
								{showNextMessage}
								navigateToMessageId={switchToBranchLeaf}
								{ensureMessageLoaded}
								{updateChat}
								{editMessage}
								{deleteMessage}
								{rateMessage}
								{actionMessage}
								{saveMessage}
								{submitMessage}
								{regenerateResponse}
								{continueResponse}
								{mergeResponses}
								{addMessages}
								{forkHandler}
								{triggerScroll}
								{readOnly}
								{preview}
								{editCodeBlock}
								{topPadding}
								{onInsertToNote}
							/>
						{/each}
					</ul>
				</section>
				<div class="pb-18" />
				{#if bottomPadding}
					<div class="  pb-6" />
				{/if}
			{/key}
		</div>
	{/if}
</div>

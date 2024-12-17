<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';
	import { chats, config, settings, user as _user, mobile, currentChatPage } from '$lib/stores';
	import { tick, getContext, onMount, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import { toast } from 'svelte-sonner';
	import { getChatList, updateChatById } from '$lib/apis/chats';
	import { copyToClipboard, findWordIndices } from '$lib/utils';
	import { renderLatex } from '$lib/utils/latex';
	import { createCopyCodeBlockButton } from '$lib/utils/codeblock';
	import hljs from 'highlight.js';
	import type { Message, ChatHistory } from '$lib/types/chat';

	import Message from './Messages/Message.svelte';
	import Loader from '../common/Loader.svelte';
	import Spinner from '../common/Spinner.svelte';

	import ChatPlaceholder from './ChatPlaceholder.svelte';

	const i18n = getContext('i18n');

	export let chatId = '';
	export let user = $_user;

	export let prompt;
	export let history: ChatHistory = { messages: {}, currentId: '' };
	export let selectedModels;

	let messages: Message[] = [];

	export let sendPrompt: Function;
	export let continueResponse: Function;
	export let regenerateResponse: Function;
	export let mergeResponses: Function;

	export let chatActionHandler: Function;
	export let showMessage: Function = () => {};
	export let submitMessage: Function = () => {};

	export let readOnly = false;

	export let bottomPadding = false;
	export let autoScroll;

	let messagesCount = 20;
	let messagesLoading = false;
	let loadingTimeout: NodeJS.Timeout | null = null;
	let isLoadingMore = false;

	const loadMoreMessages = async () => {
		if (isLoadingMore) return;
		
		try {
			isLoadingMore = true;
			const element = document.getElementById('messages-container');
			if (!element) return;
			
			// Store current scroll position
			const scrollHeight = element.scrollHeight;
			const scrollTop = element.scrollTop;
			
			// Clear any pending load requests
			if (loadingTimeout) {
				clearTimeout(loadingTimeout);
			}
			
			// Debounce the load request
			loadingTimeout = setTimeout(async () => {
				messagesLoading = true;
				messagesCount += 20;
				
				// Wait for DOM update
				await tick();
				
				// Restore scroll position
				element.scrollTop = scrollTop + (element.scrollHeight - scrollHeight);
				messagesLoading = false;
				isLoadingMore = false;
			}, 250);
			
		} catch (error) {
			console.error('Error loading more messages:', error);
			toast.error($i18n.t('Error loading messages'));
			messagesLoading = false;
			isLoadingMore = false;
		}
	};

	$: if (history.currentId) {
		let _messages = [];

		let message = history.messages[history.currentId];
		while (message && _messages.length <= messagesCount) {
			_messages.unshift({ ...message });
			message = message.parentId !== null ? history.messages[message.parentId] : null;
		}

		messages = _messages;
	} else {
		messages = [];
	}

	$: if (autoScroll && bottomPadding) {
		(async () => {
			await tick();
			scrollToBottom();
		})();
	}

	const scrollToBottom = () => {
		const element = document.getElementById('messages-container');
		element.scrollTop = element.scrollHeight;
	};

	const updateChat = async () => {
		history = history;
		await tick();
		await updateChatById(localStorage.token, chatId, {
			history: history,
			messages: messages
		});

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
	};

	const showPreviousMessage = async (message) => {
		if (message.parentId !== null) {
			let messageId =
				history.messages[message.parentId].childrenIds[
					Math.max(history.messages[message.parentId].childrenIds.indexOf(message.id) - 1, 0)
				];

			if (message.id !== messageId) {
				let messageChildrenIds = history.messages[messageId].childrenIds;

				while (messageChildrenIds.length !== 0) {
					messageId = messageChildrenIds.at(-1);
					messageChildrenIds = history.messages[messageId].childrenIds;
				}

				history.currentId = messageId;
			}
		} else {
			let childrenIds = Object.values(history.messages)
				.filter((message) => message.parentId === null)
				.map((message) => message.id);
			let messageId = childrenIds[Math.max(childrenIds.indexOf(message.id) - 1, 0)];

			if (message.id !== messageId) {
				let messageChildrenIds = history.messages[messageId].childrenIds;

				while (messageChildrenIds.length !== 0) {
					messageId = messageChildrenIds.at(-1);
					messageChildrenIds = history.messages[messageId].childrenIds;
				}

				history.currentId = messageId;
			}
		}

		await tick();

		if ($settings?.scrollOnBranchChange ?? true) {
			const element = document.getElementById('messages-container');
			autoScroll = element.scrollHeight - element.scrollTop <= element.clientHeight + 50;

			setTimeout(() => {
				scrollToBottom();
			}, 100);
		}
	};

	const showNextMessage = async (message) => {
		if (message.parentId !== null) {
			let messageId =
				history.messages[message.parentId].childrenIds[
					Math.min(
						history.messages[message.parentId].childrenIds.indexOf(message.id) + 1,
						history.messages[message.parentId].childrenIds.length - 1
					)
				];

			if (message.id !== messageId) {
				let messageChildrenIds = history.messages[messageId].childrenIds;

				while (messageChildrenIds.length !== 0) {
					messageId = messageChildrenIds.at(-1);
					messageChildrenIds = history.messages[messageId].childrenIds;
				}

				history.currentId = messageId;
			}
		} else {
			let childrenIds = Object.values(history.messages)
				.filter((message) => message.parentId === null)
				.map((message) => message.id);
			let messageId =
				childrenIds[Math.min(childrenIds.indexOf(message.id) + 1, childrenIds.length - 1)];

			if (message.id !== messageId) {
				let messageChildrenIds = history.messages[messageId].childrenIds;

				while (messageChildrenIds.length !== 0) {
					messageId = messageChildrenIds.at(-1);
					messageChildrenIds = history.messages[messageId].childrenIds;
				}

				history.currentId = messageId;
			}
		}

		await tick();

		if ($settings?.scrollOnBranchChange ?? true) {
			const element = document.getElementById('messages-container');
			autoScroll = element.scrollHeight - element.scrollTop <= element.clientHeight + 50;

			setTimeout(() => {
				scrollToBottom();
			}, 100);
		}
	};

	const rateMessage = async (messageId, rating) => {
		history.messages[messageId].annotation = {
			...history.messages[messageId].annotation,
			rating: rating
		};

		await updateChat();
	};

	const editMessage = async (messageId, content, submit = true) => {
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
					...(history.messages[messageId].files && { files: history.messages[messageId].files }),
					models: selectedModels
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
				await sendPrompt(userPrompt, userMessageId);
			} else {
				// Edit user message
				history.messages[messageId].content = content;
				await updateChat();
			}
		} else {
			if (submit) {
				// New response message
				const responseMessageId = uuidv4();
				const message = history.messages[messageId];
				const parentId = message.parentId;

				const responseMessage = {
					...message,
					id: responseMessageId,
					parentId: parentId,
					childrenIds: [],
					content: content,
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
				history.messages[messageId].originalContent = history.messages[messageId].content;
				history.messages[messageId].content = content;
				await updateChat();
			}
		}
	};

	const actionMessage = async (actionId, message, event = null) => {
		await chatActionHandler(chatId, actionId, message.model, message.id, event);
	};

	const saveMessage = async (messageId, message) => {
		history.messages[messageId] = message;
		await updateChat();
	};

	const deleteMessage = async (messageId: string) => {
		try {
			const messageToDelete = history.messages[messageId];
			if (!messageToDelete) return;
			
			// Remove message from parent's children
			if (messageToDelete.parentId !== null) {
				const parentMessage = history.messages[messageToDelete.parentId];
				if (parentMessage) {
					parentMessage.childrenIds = parentMessage.childrenIds.filter(id => id !== messageId);
				}
			}

			// Recursively delete all child messages
			const deleteChildren = (childIds: string[]) => {
				for (const childId of childIds) {
					const childMessage = history.messages[childId];
					if (childMessage && childMessage.childrenIds.length > 0) {
						deleteChildren(childMessage.childrenIds);
					}
					delete history.messages[childId];
				}
			};

			if (messageToDelete.childrenIds.length > 0) {
				deleteChildren(messageToDelete.childrenIds);
			}

			// Delete the message itself
			delete history.messages[messageId];

			// Update chat history in backend
			await updateChatById(localStorage.token, chatId, {
				messages: messages,
				history: history
			});

			// Update chat list
			await chats.set(await getChatList(localStorage.token));

			toast.success('Message deleted successfully');
		} catch (error) {
			console.error('Error deleting message:', error);
			toast.error('Failed to delete message');
		}
	};

	const mergeMessages = async (messageIds: string[]) => {
		try {
			if (messageIds.length < 2) {
				throw new Error('At least two messages are required for merging');
			}

			// Sort messages by timestamp to maintain chronological order
			messageIds.sort((a, b) => {
				const msgA = history.messages[a];
				const msgB = history.messages[b];
				return msgA.timestamp - msgB.timestamp;
			});

			const baseMessage = history.messages[messageIds[0]];
			if (!baseMessage) throw new Error('Base message not found');

			// Merge content from subsequent messages
			let mergedContent = baseMessage.content;
			for (let i = 1; i < messageIds.length; i++) {
				const msgId = messageIds[i];
				const msg = history.messages[msgId];
				if (!msg) continue;
				
				mergedContent += '\n\n' + msg.content;
				
				// Clean up relationships
				if (msg.parentId) {
					const parent = history.messages[msg.parentId];
					if (parent) {
						parent.childrenIds = parent.childrenIds.filter(id => id !== msgId);
					}
				}
				
				// Transfer any children to the base message
				if (msg.childrenIds.length > 0) {
					baseMessage.childrenIds = [...baseMessage.childrenIds, ...msg.childrenIds];
					msg.childrenIds.forEach(childId => {
						const child = history.messages[childId];
						if (child) child.parentId = baseMessage.id;
					});
				}

				delete history.messages[msgId];
			}

			// Update base message
			baseMessage.content = mergedContent;
			baseMessage.updated = new Date().toISOString();

			// Update chat in backend
			await updateChatById(localStorage.token, chatId, {
				messages: Object.values(history.messages)
			});

			history = { ...history };
			await tick();
			toast.success('Messages merged successfully');

		} catch (error) {
			console.error('Error merging messages:', error);
			toast.error(error.message || 'Failed to merge messages');
		}
	};

	const triggerScroll = () => {
		if (autoScroll) {
			const element = document.getElementById('messages-container');
			autoScroll = element.scrollHeight - element.scrollTop <= element.clientHeight + 50;
			setTimeout(() => {
				scrollToBottom();
			}, 100);
		}
	};

	$: if (messages && messages.length > 0 && (messages.at(-1).done ?? false)) {
		(async () => {
			await tick();

			// Clean up existing tooltips to prevent memory leaks
			[...document.querySelectorAll('*')].forEach((node) => {
				if (node._tippy) {
					node._tippy.destroy();
				}
			});

			renderLatex();
			hljs.highlightAll();
			createCopyCodeBlockButton();

			// Debounced loading of tooltips
			if (loadingTimeout) {
				clearTimeout(loadingTimeout);
			}

			loadingTimeout = setTimeout(() => {
				for (const message of messages) {
					if (message.info) {
						tippy(`#info-${message.id}`, {
							content: `<span class="text-xs" id="tooltip-${message.id}">token/s: ${
								Math.round(((message.info.eval_count ?? 0) / (message.info.eval_duration / 1000000000)) * 100) / 100
							} tokens<br/>
							total_duration: ${Math.round(((message.info.total_duration ?? 0) / 1000000) * 100) / 100}ms<br/>
							load_duration: ${Math.round(((message.info.load_duration ?? 0) / 1000000) * 100) / 100}ms<br/>
							prompt_eval_count: ${message.info.prompt_eval_count ?? 'N/A'}<br/>
							prompt_eval_duration: ${Math.round(((message.info.prompt_eval_duration ?? 0) / 1000000) * 100) / 100}ms<br/>
							eval_count: ${message.info.eval_count ?? 'N/A'}<br/>
							eval_duration: ${Math.round(((message.info.eval_duration ?? 0) / 1000000) * 100) / 100}ms</span>`,
							allowHTML: true,
							placement: 'right'
						});
					}
				}
			}, 100);
		})();
	}
</script>

<div class="h-full flex pt-8">
	{#if Object.keys(history?.messages ?? {}).length == 0}
		<ChatPlaceholder
			modelIds={selectedModels}
			submitPrompt={async (p) => {
				let text = p;

				if (p.includes('{{CLIPBOARD}}')) {
					const clipboardText = await navigator.clipboard.readText().catch((err) => {
						toast.error($i18n.t('Failed to read clipboard contents'));
						return '{{CLIPBOARD}}';
					});

					text = p.replaceAll('{{CLIPBOARD}}', clipboardText);
				}

				prompt = text;

				await tick();

				const chatInputContainerElement = document.getElementById('chat-input-container');
				if (chatInputContainerElement) {
					prompt = p;

					chatInputContainerElement.style.height = '';
					chatInputContainerElement.style.height =
						Math.min(chatInputContainerElement.scrollHeight, 200) + 'px';
					chatInputContainerElement.focus();
				}

				await tick();
			}}
		/>
	{:else}
		<div class="w-full pt-2">
			{#key chatId}
				<div class="w-full">
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
								<div class=" ">Loading...</div>
							</div>
						</Loader>
					{/if}

					{#each messages as message, messageIdx (message.id)}
						<Message
							{chatId}
							bind:history
							messageId={message.id}
							idx={messageIdx}
							{user}
							{showPreviousMessage}
							{showNextMessage}
							{updateChat}
							{editMessage}
							{deleteMessage}
							{rateMessage}
							{actionMessage}
							{saveMessage}
							{submitMessage}
							{regenerateResponse}
							{continueResponse}
							{mergeMessages}
							{triggerScroll}
							{readOnly}
						/>
					{/each}
				</div>
				<div class="pb-12" />
				{#if bottomPadding}
					<div class="  pb-6" />
				{/if}
			{/key}
		</div>
	{/if}
</div>

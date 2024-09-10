<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';
	import { chats, config, settings, user as _user, mobile, currentChatPage } from '$lib/stores';
	import { tick, getContext, onMount } from 'svelte';

	import { toast } from 'svelte-sonner';
	import { getChatList, updateChatById } from '$lib/apis/chats';
	import { copyToClipboard, findWordIndices } from '$lib/utils';

	import UserMessage from './Messages/UserMessage.svelte';
	import ResponseMessage from './Messages/ResponseMessage.svelte';
	import Placeholder from './Messages/Placeholder.svelte';
	import MultiResponseMessages from './Messages/MultiResponseMessages.svelte';

	const i18n = getContext('i18n');

	export let chatId = '';
	export let readOnly = false;
	export let sendPrompt: Function;
	export let continueGeneration: Function;
	export let regenerateResponse: Function;
	export let mergeResponses: Function;
	export let chatActionHandler: Function;

	export let user = $_user;
	export let prompt;
	export let processing = '';
	export let bottomPadding = false;
	export let autoScroll;
	export let history = {};
	export let messages = [];

	export let selectedModels;

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

	const copyToClipboardWithToast = async (text) => {
		const res = await copyToClipboard(text);
		if (res) {
			toast.success($i18n.t('Copying to clipboard was successful!'));
		}
	};

	const confirmEditMessage = async (messageId, content, submit = true) => {
		if (submit) {
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
			history.messages[messageId].content = content;
			await tick();
			await updateChatById(localStorage.token, chatId, {
				messages: messages,
				history: history
			});
		}
	};

	const updateChatMessages = async () => {
		await tick();
		await updateChatById(localStorage.token, chatId, {
			messages: messages,
			history: history
		});

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
	};

	const confirmEditResponseMessage = async (messageId, content) => {
		history.messages[messageId].originalContent = history.messages[messageId].content;
		history.messages[messageId].content = content;

		await updateChatMessages();
	};

	const rateMessage = async (messageId, rating) => {
		history.messages[messageId].annotation = {
			...history.messages[messageId].annotation,
			rating: rating
		};

		await updateChatMessages();
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

	const deleteMessageHandler = async (messageId) => {
		const messageToDelete = history.messages[messageId];

		const parentMessageId = messageToDelete.parentId;
		const childMessageIds = messageToDelete.childrenIds ?? [];

		const hasDescendantMessages = childMessageIds.some(
			(childId) => history.messages[childId]?.childrenIds?.length > 0
		);

		history.currentId = parentMessageId;
		await tick();

		// Remove the message itself from the parent message's children array
		history.messages[parentMessageId].childrenIds = history.messages[
			parentMessageId
		].childrenIds.filter((id) => id !== messageId);

		await tick();

		childMessageIds.forEach((childId) => {
			const childMessage = history.messages[childId];

			if (childMessage && childMessage.childrenIds) {
				if (childMessage.childrenIds.length === 0 && !hasDescendantMessages) {
					// If there are no other responses/prompts
					history.messages[parentMessageId].childrenIds = [];
				} else {
					childMessage.childrenIds.forEach((grandChildId) => {
						if (history.messages[grandChildId]) {
							history.messages[grandChildId].parentId = parentMessageId;
							history.messages[parentMessageId].childrenIds.push(grandChildId);
						}
					});
				}
			}

			// Remove child message id from the parent message's children array
			history.messages[parentMessageId].childrenIds = history.messages[
				parentMessageId
			].childrenIds.filter((id) => id !== childId);
		});

		await tick();

		await updateChatById(localStorage.token, chatId, {
			messages: messages,
			history: history
		});
	};
</script>

<div class="h-full flex">
	{#if messages.length == 0}
		<Placeholder
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

				const chatInputElement = document.getElementById('chat-textarea');
				if (chatInputElement) {
					prompt = p;

					chatInputElement.style.height = '';
					chatInputElement.style.height = Math.min(chatInputElement.scrollHeight, 200) + 'px';
					chatInputElement.focus();

					const words = findWordIndices(prompt);

					if (words.length > 0) {
						const word = words.at(0);
						chatInputElement.setSelectionRange(word?.startIndex, word.endIndex + 1);
					}
				}

				await tick();
			}}
		/>
	{:else}
		<div class="w-full pt-2">
			{#key chatId}
				{#each messages as message, messageIdx (message.id)}
					<div class=" w-full {messageIdx === messages.length - 1 ? ' pb-12' : ''}">
						<div
							class="flex flex-col justify-between px-5 mb-3 {($settings?.widescreenMode ?? null)
								? 'max-w-full'
								: 'max-w-5xl'} mx-auto rounded-lg group"
						>
							{#if message.role === 'user'}
								<UserMessage
									on:delete={() => deleteMessageHandler(message.id)}
									{user}
									{readOnly}
									{message}
									isFirstMessage={messageIdx === 0}
									siblings={message.parentId !== null
										? (history.messages[message.parentId]?.childrenIds ?? [])
										: (Object.values(history.messages)
												.filter((message) => message.parentId === null)
												.map((message) => message.id) ?? [])}
									{confirmEditMessage}
									{showPreviousMessage}
									{showNextMessage}
									copyToClipboard={copyToClipboardWithToast}
								/>
							{:else if (history.messages[message.parentId]?.models?.length ?? 1) === 1}
								{#key message.id}
									<ResponseMessage
										{message}
										siblings={history.messages[message.parentId]?.childrenIds ?? []}
										isLastMessage={messageIdx + 1 === messages.length}
										{readOnly}
										{updateChatMessages}
										{confirmEditResponseMessage}
										{showPreviousMessage}
										{showNextMessage}
										{rateMessage}
										copyToClipboard={copyToClipboardWithToast}
										{continueGeneration}
										{regenerateResponse}
										on:action={async (e) => {
											console.log('action', e);
											if (typeof e.detail === 'string') {
												await chatActionHandler(chatId, e.detail, message.model, message.id);
											} else {
												const { id, event } = e.detail;
												await chatActionHandler(chatId, id, message.model, message.id, event);
											}
										}}
										on:save={async (e) => {
											console.log('save', e);

											const message = e.detail;
											history.messages[message.id] = message;
											await updateChatById(localStorage.token, chatId, {
												messages: messages,
												history: history
											});
										}}
									/>
								{/key}
							{:else}
								{#key message.parentId}
									<MultiResponseMessages
										bind:history
										isLastMessage={messageIdx + 1 === messages.length}
										{messages}
										{readOnly}
										{chatId}
										parentMessage={history.messages[message.parentId]}
										{messageIdx}
										{updateChatMessages}
										{confirmEditResponseMessage}
										{rateMessage}
										copyToClipboard={copyToClipboardWithToast}
										{continueGeneration}
										{mergeResponses}
										{regenerateResponse}
										on:action={async (e) => {
											console.log('action', e);
											if (typeof e.detail === 'string') {
												await chatActionHandler(chatId, e.detail, message.model, message.id);
											} else {
												const { id, event } = e.detail;
												await chatActionHandler(chatId, id, message.model, message.id, event);
											}
										}}
										on:change={async () => {
											await updateChatById(localStorage.token, chatId, {
												messages: messages,
												history: history
											});

											if (autoScroll) {
												const element = document.getElementById('messages-container');
												autoScroll =
													element.scrollHeight - element.scrollTop <= element.clientHeight + 50;
												setTimeout(() => {
													scrollToBottom();
												}, 100);
											}
										}}
									/>
								{/key}
							{/if}
						</div>
					</div>
				{/each}

				{#if bottomPadding}
					<div class="  pb-6" />
				{/if}
			{/key}
		</div>
	{/if}
</div>

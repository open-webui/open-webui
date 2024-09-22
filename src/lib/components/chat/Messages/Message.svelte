<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { tick, getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { settings } from '$lib/stores';
	import { copyToClipboard } from '$lib/utils';

	import MultiResponseMessages from './MultiResponseMessages.svelte';
	import ResponseMessage from './ResponseMessage.svelte';
	import UserMessage from './UserMessage.svelte';
	import { updateChatById } from '$lib/apis/chats';

	// h here refers to the height of the message graph
	export let h;

	export let chatId;

	export let history;
	export let messageId;

	export let user;

	export let scrollToBottom;
	export let chatActionHandler;

	export let showPreviousMessage;
	export let showNextMessage;

	export let editMessage;
	export let deleteMessage;
	export let rateMessage;

	export let regenerateResponse;
	export let continueResponse;

	// MultiResponseMessages
	export let mergeResponses;

	export let readOnly = false;

	const copyToClipboardWithToast = async (text) => {
		const res = await copyToClipboard(text);
		if (res) {
			toast.success($i18n.t('Copying to clipboard was successful!'));
		}
	};
</script>

<div
	class="flex flex-col justify-between px-5 mb-3 w-full {($settings?.widescreenMode ?? null)
		? 'max-w-full'
		: 'max-w-5xl'} mx-auto rounded-lg group"
>
	{#if history.messages[messageId]}
		{@const message = history.messages[messageId]}
		{#if message.role === 'user'}
			<UserMessage
				{user}
				{message}
				isFirstMessage={h === 0}
				siblings={message.parentId !== null
					? (history.messages[message.parentId]?.childrenIds ?? [])
					: (Object.values(history.messages)
							.filter((message) => message.parentId === null)
							.map((message) => message.id) ?? [])}
				{showPreviousMessage}
				{showNextMessage}
				{editMessage}
				on:delete={() => deleteMessage(message.id)}
				{readOnly}
			/>
		{:else if (history.messages[message.parentId]?.models?.length ?? 1) === 1}
			<ResponseMessage
				{message}
				isLastMessage={messageId === history.currentId}
				siblings={history.messages[message.parentId]?.childrenIds ?? []}
				{showPreviousMessage}
				{showNextMessage}
				{editMessage}
				{rateMessage}
				{continueResponse}
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
				on:update={async (e) => {
					console.log('update', e);
					// call updateChatHistory
				}}
				on:save={async (e) => {
					console.log('save', e);

					const message = e.detail;
					if (message) {
						history.messages[message.id] = message;
						await updateChatById(localStorage.token, chatId, {
							history: history
						});
					} else {
						await updateChatById(localStorage.token, chatId, {
							history: history
						});
					}
				}}
				{readOnly}
			/>
		{:else}
			<MultiResponseMessages
				bind:history
				{chatId}
				messageIds={[]}
				parentMessage={history.messages[message.parentId]}
				isLastMessage={messageId === history.currentId}
				{editMessage}
				{rateMessage}
				{continueResponse}
				{mergeResponses}
				{regenerateResponse}
				copyToClipboard={copyToClipboardWithToast}
				{readOnly}
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
						history: history
					});

					if (autoScroll) {
						const element = document.getElementById('messages-container');
						autoScroll = element.scrollHeight - element.scrollTop <= element.clientHeight + 50;
						setTimeout(() => {
							scrollToBottom();
						}, 100);
					}
				}}
			/>
		{/if}
	{/if}
</div>

{#if history.messages[messageId]?.parentId !== null}
	<svelte:self
		h={h + 1}
		{chatId}
		{history}
		messageId={history.messages[messageId]?.parentId}
		{user}
		{scrollToBottom}
		{chatActionHandler}
		{showPreviousMessage}
		{showNextMessage}
		{editMessage}
		{deleteMessage}
		{rateMessage}
		{regenerateResponse}
		{continueResponse}
		{mergeResponses}
		{readOnly}
	></svelte:self>
{/if}

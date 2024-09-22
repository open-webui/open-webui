<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { tick, getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { settings } from '$lib/stores';
	import { copyToClipboard } from '$lib/utils';

	import MultiResponseMessages from './MultiResponseMessages.svelte';
	import ResponseMessage from './ResponseMessage.svelte';
	import UserMessage from './UserMessage.svelte';

	export let chatId;

	export let history;
	export let messageId;

	export let user;

	export let scrollToBottom;
	export let chatActionHandler;

	export let confirmEditMessage;
	export let confirmEditResponseMessage;

	export let showPreviousMessage;
	export let showNextMessage;

	export let rateMessage;
	export let deleteMessage;

	export let saveNewResponseMessage;

	export let regenerateResponse;
	export let continueGeneration;

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

<div class="w-full">
	<div
		class="flex flex-col justify-between px-5 mb-3 {($settings?.widescreenMode ?? null)
			? 'max-w-full'
			: 'max-w-5xl'} mx-auto rounded-lg group"
	>
		{#if history.messages[messageId].role === 'user'}
			{@const message = history.messages[messageId]}
			<UserMessage
				{user}
				{history}
				siblings={message.parentId !== null
					? (history.messages[message.parentId]?.childrenIds ?? [])
					: (Object.values(history.messages)
							.filter((message) => message.parentId === null)
							.map((message) => message.id) ?? [])}
				{confirmEditMessage}
				{showPreviousMessage}
				{showNextMessage}
				copyToClipboard={copyToClipboardWithToast}
				isFirstMessage={messageIdx === 0}
				on:delete={() => deleteMessage(message.id)}
				{readOnly}
			/>
		{:else if (history.messages[message.parentId]?.models?.length ?? 1) === 1}
			<ResponseMessage
				{message}
				siblings={history.messages[message.parentId]?.childrenIds ?? []}
				isLastMessage={messageIdx + 1 === messages.length}
				{readOnly}
				{updateChatMessages}
				{confirmEditResponseMessage}
				{saveNewResponseMessage}
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
			/>
		{:else}
			<MultiResponseMessages
				bind:history
				{chatId}
				messageIds={[]}
				parentMessage={history.messages[message.parentId]}
				isLastMessage={messageIdx + 1 === messages.length}
				{readOnly}
				{updateChatMessages}
				{saveNewResponseMessage}
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
	</div>
</div>

<script lang="ts">
	import { getI18n } from '$lib/utils/context';

	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getI18n();

	import { settings } from '$lib/stores';
	import { messageNavigation } from '$lib/utils/message-navigation';

	import MultiResponseMessages from './MultiResponseMessages.svelte';
	import ResponseMessage from './ResponseMessage.svelte';
	import UserMessage from './UserMessage.svelte';

	export let chatId: any;
	export let idx = 0;

	export let history: any;
	export let messageId: any;

	export let user: any;
	export let selectedToolIds: string[] = [];

	export let showPreviousMessage: any;
	export let showNextMessage: any;
	export let updateChat: any;

	export let editMessage: any;
	export let saveMessage: any;
	export let deleteMessage: any;
	export let rateMessage: any;
	export let actionMessage: any;
	export let submitMessage: any;

	export let regenerateResponse: any;
	export let continueResponse: any;
	export let mergeResponses: any;

	export let addMessages: any;
	export let triggerScroll: any;
	export let readOnly = false;
</script>

<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
<div
	use:messageNavigation
	data-keyboard-message
	role="group"
	tabindex={idx === 0 ? 0 : -1}
	aria-label={$i18n.t('Message {{number}} from {{name}}', {
		number: idx + 1,
		name: history.messages[messageId]?.role === 'user' ? $i18n.t('You') : $i18n.t('Assistant')
	})}
	aria-describedby="message-keyboard-help-{chatId}"
	class="flex flex-col justify-between px-5 mb-3 w-full {($settings?.widescreenMode ?? null)
		? 'max-w-full'
		: 'max-w-5xl'} mx-auto rounded-lg group keyboard-message"
>
	{#if idx === 0}
		<span id="message-keyboard-help-{chatId}" hidden>
			{$i18n.t(
				'Use Up and Down to navigate messages, Enter for actions, Left and Right to navigate actions, and Escape to return to the message.'
			)}
		</span>
	{/if}
	{#if history.messages[messageId]}
		{#if history.messages[messageId].role === 'user'}
			<UserMessage
				{user}
				{history}
				{messageId}
				isFirstMessage={idx === 0}
				siblings={history.messages[messageId].parentId !== null
					? (history.messages[history.messages[messageId].parentId]?.childrenIds ?? [])
					: (Object.values(history.messages)
							.filter((message) => message.parentId === null)
							.map((message) => message.id) ?? [])}
				{showPreviousMessage}
				{showNextMessage}
				{editMessage}
				{deleteMessage}
				{readOnly}
			/>
		{:else if (history.messages[history.messages[messageId].parentId]?.models?.length ?? 1) === 1}
			<ResponseMessage
				{chatId}
				{history}
				{messageId}
				{selectedToolIds}
				isLastMessage={messageId === history.currentId}
				siblings={history.messages[history.messages[messageId].parentId]?.childrenIds ?? []}
				{showPreviousMessage}
				{showNextMessage}
				{updateChat}
				{editMessage}
				{saveMessage}
				{rateMessage}
				{actionMessage}
				{submitMessage}
				{continueResponse}
				{regenerateResponse}
				{addMessages}
				{readOnly}
			/>
		{:else}
			<MultiResponseMessages
				bind:history
				{chatId}
				{messageId}
				{selectedToolIds}
				isLastMessage={messageId === history?.currentId}
				{updateChat}
				{editMessage}
				{saveMessage}
				{rateMessage}
				{actionMessage}
				{submitMessage}
				{continueResponse}
				{regenerateResponse}
				{mergeResponses}
				{triggerScroll}
				{addMessages}
				{readOnly}
			/>
		{/if}
	{/if}
</div>

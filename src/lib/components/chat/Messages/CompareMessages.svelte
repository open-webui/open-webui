<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import { updateChatById } from '$lib/apis/chats';
	import { onMount, tick } from 'svelte';
	import ResponseMessage from './ResponseMessage.svelte';

	export let chatId;

	export let history;
	export let messages = [];
	export let messageIdx;

	export let parentMessage;

	export let readOnly = false;

	export let updateChatMessages: Function;
	export let confirmEditResponseMessage: Function;
	export let rateMessage: Function;

	export let copyToClipboard: Function;
	export let continueGeneration: Function;
	export let regenerateResponse: Function;

	const dispatch = createEventDispatcher();

	let currentMessageId;

	let groupedMessagesIdx = {};
	let groupedMessages = {};

	$: groupedMessages = parentMessage?.models.reduce((a, model) => {
		const modelMessages = parentMessage?.childrenIds
			.map((id) => history.messages[id])
			.filter((m) => m.model === model);

		return {
			...a,
			[model]: { messages: modelMessages }
		};
	}, {});

	const showPreviousMessage = (model) => {
		groupedMessagesIdx[model] = Math.max(0, groupedMessagesIdx[model] - 1);
		let messageId = groupedMessages[model].messages[groupedMessagesIdx[model]].id;

		console.log(messageId);
		let messageChildrenIds = history.messages[messageId].childrenIds;

		while (messageChildrenIds.length !== 0) {
			messageId = messageChildrenIds.at(-1);
			messageChildrenIds = history.messages[messageId].childrenIds;
		}

		history.currentId = messageId;

		dispatch('change');
	};

	const showNextMessage = (model) => {
		groupedMessagesIdx[model] = Math.min(
			groupedMessages[model].messages.length - 1,
			groupedMessagesIdx[model] + 1
		);

		let messageId = groupedMessages[model].messages[groupedMessagesIdx[model]].id;
		console.log(messageId);

		let messageChildrenIds = history.messages[messageId].childrenIds;

		while (messageChildrenIds.length !== 0) {
			messageId = messageChildrenIds.at(-1);
			messageChildrenIds = history.messages[messageId].childrenIds;
		}

		history.currentId = messageId;

		dispatch('change');
	};

	onMount(async () => {
		await tick();
		currentMessageId = messages[messageIdx].id;

		for (const model of parentMessage?.models) {
			const idx = groupedMessages[model].messages.findIndex((m) => m.id === currentMessageId);

			if (idx !== -1) {
				groupedMessagesIdx[model] = idx;
			} else {
				groupedMessagesIdx[model] = 0;
			}
		}
	});
</script>

<div>
	<div
		class="flex snap-x snap-mandatory overflow-x-auto scrollbar-hidden"
		id="responses-container-{parentMessage.id}"
	>
		{#each Object.keys(groupedMessages) as model}
			{#if groupedMessagesIdx[model] !== undefined && groupedMessages[model].messages.length > 0}
				<!-- svelte-ignore a11y-no-static-element-interactions -->
				<!-- svelte-ignore a11y-click-events-have-key-events -->

				<div
					class=" snap-center min-w-80 w-full max-w-full m-1 border {history.messages[
						currentMessageId
					].model === model
						? 'border-gray-100 dark:border-gray-850 border-[1.5px]'
						: 'border-gray-50 dark:border-gray-850 '} transition p-5 rounded-3xl"
					on:click={() => {
						currentMessageId = groupedMessages[model].messages[groupedMessagesIdx[model]].id;

						let messageId = groupedMessages[model].messages[groupedMessagesIdx[model]].id;

						console.log(messageId);
						let messageChildrenIds = history.messages[messageId].childrenIds;

						while (messageChildrenIds.length !== 0) {
							messageId = messageChildrenIds.at(-1);
							messageChildrenIds = history.messages[messageId].childrenIds;
						}

						history.currentId = messageId;
						dispatch('change');
					}}
				>
					<ResponseMessage
						message={groupedMessages[model].messages[groupedMessagesIdx[model]]}
						siblings={groupedMessages[model].messages.map((m) => m.id)}
						isLastMessage={true}
						{updateChatMessages}
						{confirmEditResponseMessage}
						showPreviousMessage={() => showPreviousMessage(model)}
						showNextMessage={() => showNextMessage(model)}
						{readOnly}
						{rateMessage}
						{copyToClipboard}
						{continueGeneration}
						regenerateResponse={async (message) => {
							regenerateResponse(message);
							await tick();
							groupedMessagesIdx[model] = groupedMessages[model].messages.length - 1;
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
				</div>
			{/if}
		{/each}
	</div>
</div>

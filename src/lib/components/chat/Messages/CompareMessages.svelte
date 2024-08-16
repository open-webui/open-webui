<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { createEventDispatcher } from 'svelte';

	import { updateChatById } from '$lib/apis/chats';

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
	let groupedMessages = {};
	let groupedMessagesIdx = {};

	$: groupedMessages = parentMessage?.models.reduce((a, model, modelIdx) => {
		// Find all messages that are children of the parent message and have the same model
		const modelMessages = parentMessage?.childrenIds
			.map((id) => history.messages[id])
			.filter((m) => m.modelIdx === modelIdx);

		return {
			...a,
			[modelIdx]: { messages: modelMessages }
		};
	}, {});

	const showPreviousMessage = (modelIdx) => {
		groupedMessagesIdx[modelIdx] = Math.max(0, groupedMessagesIdx[modelIdx] - 1);
		let messageId = groupedMessages[modelIdx].messages[groupedMessagesIdx[modelIdx]].id;

		console.log(messageId);
		let messageChildrenIds = history.messages[messageId].childrenIds;

		while (messageChildrenIds.length !== 0) {
			messageId = messageChildrenIds.at(-1);
			messageChildrenIds = history.messages[messageId].childrenIds;
		}

		history.currentId = messageId;
		dispatch('change');
	};

	const showNextMessage = (modelIdx) => {
		groupedMessagesIdx[modelIdx] = Math.min(
			groupedMessages[modelIdx].messages.length - 1,
			groupedMessagesIdx[modelIdx] + 1
		);

		let messageId = groupedMessages[modelIdx].messages[groupedMessagesIdx[modelIdx]].id;
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

		for (const [modelIdx, model] of parentMessage?.models.entries()) {
			const idx = groupedMessages[modelIdx].messages.findIndex((m) => m.id === currentMessageId);
			if (idx !== -1) {
				groupedMessagesIdx[modelIdx] = idx;
			} else {
				groupedMessagesIdx[modelIdx] = 0;
			}
		}
	});
</script>

<div>
	<div
		class="flex snap-x snap-mandatory overflow-x-auto scrollbar-hidden"
		id="responses-container-{parentMessage.id}"
	>
		{#key currentMessageId}
			{#each Object.keys(groupedMessages) as modelIdx}
				{#if groupedMessagesIdx[modelIdx] !== undefined && groupedMessages[modelIdx].messages.length > 0}
					<!-- svelte-ignore a11y-no-static-element-interactions -->
					<!-- svelte-ignore a11y-click-events-have-key-events -->
					{@const message = groupedMessages[modelIdx].messages[groupedMessagesIdx[modelIdx]]}

					<div
						class=" snap-center min-w-80 w-full max-w-full m-1 border {history.messages[
							currentMessageId
						]?.modelIdx == modelIdx
							? 'border-gray-100 dark:border-gray-800 border-[1.5px]'
							: 'border-gray-50 dark:border-gray-850 '} transition p-5 rounded-3xl"
						on:click={() => {
							if (currentMessageId != message.id) {
								currentMessageId = message.id;
								let messageId = message.id;
								console.log(messageId);
								//
								let messageChildrenIds = history.messages[messageId].childrenIds;
								while (messageChildrenIds.length !== 0) {
									messageId = messageChildrenIds.at(-1);
									messageChildrenIds = history.messages[messageId].childrenIds;
								}
								history.currentId = messageId;
								dispatch('change');
							}
						}}
					>
						{#key history.currentId}
							<ResponseMessage
								message={groupedMessages[modelIdx].messages[groupedMessagesIdx[modelIdx]]}
								siblings={groupedMessages[modelIdx].messages.map((m) => m.id)}
								isLastMessage={true}
								{updateChatMessages}
								{confirmEditResponseMessage}
								showPreviousMessage={() => showPreviousMessage(modelIdx)}
								showNextMessage={() => showNextMessage(modelIdx)}
								{readOnly}
								{rateMessage}
								{copyToClipboard}
								{continueGeneration}
								regenerateResponse={async (message) => {
									regenerateResponse(message);
									await tick();
									groupedMessagesIdx[modelIdx] = groupedMessages[modelIdx].messages.length - 1;
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
					</div>
				{/if}
			{/each}
		{/key}
	</div>
</div>

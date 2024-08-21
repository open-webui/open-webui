<script lang="ts">
	import dayjs from 'dayjs';
	import { onMount, tick, getContext } from 'svelte';
	import { createEventDispatcher } from 'svelte';

	import { mobile, settings } from '$lib/stores';

	import { generateMoACompletion } from '$lib/apis';
	import { updateChatById } from '$lib/apis/chats';
	import { createOpenAITextStream } from '$lib/apis/streaming';

	import ResponseMessage from './ResponseMessage.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Merge from '$lib/components/icons/Merge.svelte';

	import Markdown from './Markdown.svelte';
	import Name from './Name.svelte';
	import Skeleton from './Skeleton.svelte';

	const i18n = getContext('i18n');

	export let chatId;

	export let history;
	export let messages = [];
	export let messageIdx;

	export let parentMessage;
	export let isLastMessage;

	export let readOnly = false;

	export let updateChatMessages: Function;
	export let confirmEditResponseMessage: Function;
	export let rateMessage: Function;

	export let copyToClipboard: Function;
	export let continueGeneration: Function;
	export let mergeResponses: Function;
	export let regenerateResponse: Function;

	const dispatch = createEventDispatcher();

	let currentMessageId;
	let groupedMessages = {};
	let groupedMessagesIdx = {};

	$: if (parentMessage) {
		initHandler();
	}

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

	const initHandler = async () => {
		await tick();
		currentMessageId = messages[messageIdx].id;

		groupedMessages = parentMessage?.models.reduce((a, model, modelIdx) => {
			// Find all messages that are children of the parent message and have the same model
			let modelMessages = parentMessage?.childrenIds
				.map((id) => history.messages[id])
				.filter((m) => m?.modelIdx === modelIdx);

			if (modelMessages.length === 0) {
				modelMessages = parentMessage?.childrenIds
					.map((id) => history.messages[id])
					.filter((m) => m?.model === model);

				modelMessages.forEach((m) => {
					m.modelIdx = modelIdx;
				});
			}

			return {
				...a,
				[modelIdx]: { messages: modelMessages }
			};
		}, {});

		groupedMessagesIdx = parentMessage?.models.reduce((a, model, modelIdx) => {
			const idx = groupedMessages[modelIdx].messages.findIndex((m) => m.id === currentMessageId);
			if (idx !== -1) {
				return {
					...a,
					[modelIdx]: idx
				};
			} else {
				return {
					...a,
					[modelIdx]: 0
				};
			}
		}, {});
	};

	const mergeResponsesHandler = async () => {
		const responses = Object.keys(groupedMessages).map((modelIdx) => {
			const { messages } = groupedMessages[modelIdx];
			return messages[groupedMessagesIdx[modelIdx]].content;
		});
		mergeResponses(currentMessageId, responses, chatId);
	};

	onMount(async () => {
		initHandler();
	});
</script>

<div>
	<div
		class="flex snap-x snap-mandatory overflow-x-auto scrollbar-hidden"
		id="responses-container-{chatId}-{parentMessage.id}"
	>
		{#key currentMessageId}
			{#each Object.keys(groupedMessages) as modelIdx}
				{#if groupedMessagesIdx[modelIdx] !== undefined && groupedMessages[modelIdx].messages.length > 0}
					<!-- svelte-ignore a11y-no-static-element-interactions -->
					<!-- svelte-ignore a11y-click-events-have-key-events -->
					{@const message = groupedMessages[modelIdx].messages[groupedMessagesIdx[modelIdx]]}

					<div
						class=" snap-center w-full max-w-full m-1 border {history.messages[currentMessageId]
							?.modelIdx == modelIdx
							? `border-gray-100 dark:border-gray-800 border-[1.5px] ${
									$mobile ? 'min-w-full' : 'min-w-[32rem]'
								}`
							: `border-gray-50 dark:border-gray-850 border-dashed ${
									$mobile ? 'min-w-full' : 'min-w-80'
								}`} transition-all p-5 rounded-2xl"
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
							{#if message}
								<ResponseMessage
									{message}
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
									on:action={async (e) => {
										dispatch('action', e.detail);
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
							{/if}
						{/key}
					</div>
				{/if}
			{/each}
		{/key}
	</div>

	{#if !readOnly && isLastMessage}
		{#if !Object.keys(groupedMessages).find((modelIdx) => {
			const { messages } = groupedMessages[modelIdx];
			return !messages[groupedMessagesIdx[modelIdx]]?.done ?? false;
		})}
			<div class="flex justify-end">
				<div class="w-full">
					{#if history.messages[currentMessageId]?.merged?.status}
						{@const message = history.messages[currentMessageId]?.merged}

						<div class="w-full rounded-xl pl-5 pr-2 py-2">
							<Name>
								Merged Response

								{#if message.timestamp}
									<span
										class=" self-center invisible group-hover:visible text-gray-400 text-xs font-medium uppercase ml-0.5 -mt-0.5"
									>
										{dayjs(message.timestamp * 1000).format($i18n.t('h:mm a'))}
									</span>
								{/if}
							</Name>

							<div class="mt-1 markdown-prose w-full min-w-full">
								{#if (message?.content ?? '') === ''}
									<Skeleton />
								{:else}
									<Markdown id={`merged`} content={message.content ?? ''} />
								{/if}
							</div>
						</div>
					{/if}
				</div>

				<div class=" flex-shrink-0 text-gray-600 dark:text-gray-500 mt-1">
					<Tooltip content={$i18n.t('Merge Responses')} placement="bottom">
						<button
							type="button"
							id="merge-response-button"
							class="{true
								? 'visible'
								: 'invisible group-hover:visible'} p-1 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition regenerate-response-button"
							on:click={() => {
								mergeResponsesHandler();
							}}
						>
							<Merge className=" size-5 " />
						</button>
					</Tooltip>
				</div>
			</div>
		{/if}
	{/if}
</div>

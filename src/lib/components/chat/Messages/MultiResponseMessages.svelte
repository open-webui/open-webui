<script lang="ts">
	import { run } from 'svelte/legacy';

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
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	const i18n = getContext('i18n');
	dayjs.extend(localizedFormat);

	interface Props {
		chatId: any;
		history: any;
		messageId: any;
		isLastMessage: any;
		readOnly?: boolean;
		updateChat: Function;
		editMessage: Function;
		saveMessage: Function;
		rateMessage: Function;
		actionMessage: Function;
		submitMessage: Function;
		deleteMessage: Function;
		continueResponse: Function;
		regenerateResponse: Function;
		mergeResponses: Function;
		addMessages: Function;
		triggerScroll: Function;
	}

	let {
		chatId,
		history = $bindable(),
		messageId,
		isLastMessage,
		readOnly = false,
		updateChat,
		editMessage,
		saveMessage,
		rateMessage,
		actionMessage,
		submitMessage,
		deleteMessage,
		continueResponse,
		regenerateResponse,
		mergeResponses,
		addMessages,
		triggerScroll
	}: Props = $props();

	const dispatch = createEventDispatcher();

	let currentMessageId;
	let parentMessage = $state();
	let groupedMessageIds = $state({});
	let groupedMessageIdsIdx = $state({});

	let message = $state(JSON.parse(JSON.stringify(history.messages[messageId])));
	run(() => {
		if (history.messages) {
			if (JSON.stringify(message) !== JSON.stringify(history.messages[messageId])) {
				message = JSON.parse(JSON.stringify(history.messages[messageId]));
			}
		}
	});

	const showPreviousMessage = async (modelIdx) => {
		groupedMessageIdsIdx[modelIdx] = Math.max(0, groupedMessageIdsIdx[modelIdx] - 1);

		let messageId = groupedMessageIds[modelIdx].messageIds[groupedMessageIdsIdx[modelIdx]];
		console.log(messageId);

		let messageChildrenIds = history.messages[messageId].childrenIds;

		while (messageChildrenIds.length !== 0) {
			messageId = messageChildrenIds.at(-1);
			messageChildrenIds = history.messages[messageId].childrenIds;
		}

		history.currentId = messageId;

		await tick();
		await updateChat();
		triggerScroll();
	};

	const showNextMessage = async (modelIdx) => {
		groupedMessageIdsIdx[modelIdx] = Math.min(
			groupedMessageIds[modelIdx].messageIds.length - 1,
			groupedMessageIdsIdx[modelIdx] + 1
		);

		let messageId = groupedMessageIds[modelIdx].messageIds[groupedMessageIdsIdx[modelIdx]];
		console.log(messageId);

		let messageChildrenIds = history.messages[messageId].childrenIds;

		while (messageChildrenIds.length !== 0) {
			messageId = messageChildrenIds.at(-1);
			messageChildrenIds = history.messages[messageId].childrenIds;
		}

		history.currentId = messageId;

		await tick();
		await updateChat();
		triggerScroll();
	};

	const initHandler = async () => {
		console.log('multiresponse:initHandler');
		await tick();

		currentMessageId = messageId;
		parentMessage = history.messages[messageId].parentId
			? history.messages[history.messages[messageId].parentId]
			: null;

		groupedMessageIds = parentMessage?.models.reduce((a, model, modelIdx) => {
			// Find all messages that are children of the parent message and have the same model
			let modelMessageIds = parentMessage?.childrenIds
				.map((id) => history.messages[id])
				.filter((m) => m?.modelIdx === modelIdx)
				.map((m) => m.id);

			// Legacy support for messages that don't have a modelIdx
			// Find all messages that are children of the parent message and have the same model
			if (modelMessageIds.length === 0) {
				let modelMessages = parentMessage?.childrenIds
					.map((id) => history.messages[id])
					.filter((m) => m?.model === model);

				modelMessages.forEach((m) => {
					m.modelIdx = modelIdx;
				});

				modelMessageIds = modelMessages.map((m) => m.id);
			}

			return {
				...a,
				[modelIdx]: { messageIds: modelMessageIds }
			};
		}, {});

		groupedMessageIdsIdx = parentMessage?.models.reduce((a, model, modelIdx) => {
			const idx = groupedMessageIds[modelIdx].messageIds.findIndex((id) => id === messageId);
			if (idx !== -1) {
				return {
					...a,
					[modelIdx]: idx
				};
			} else {
				return {
					...a,
					[modelIdx]: groupedMessageIds[modelIdx].messageIds.length - 1
				};
			}
		}, {});

		console.log(groupedMessageIds, groupedMessageIdsIdx);

		await tick();
	};

	const mergeResponsesHandler = async () => {
		const responses = Object.keys(groupedMessageIds).map((modelIdx) => {
			const { messageIds } = groupedMessageIds[modelIdx];
			const messageId = messageIds[groupedMessageIdsIdx[modelIdx]];

			return history.messages[messageId].content;
		});
		mergeResponses(messageId, responses, chatId);
	};

	onMount(async () => {
		await initHandler();
		await tick();

		const messageElement = document.getElementById(`message-${messageId}`);
		if (messageElement) {
			messageElement.scrollIntoView({ block: 'start' });
		}
	});
</script>

{#if parentMessage}
	<div>
		<div
			id="responses-container-{chatId}-{parentMessage.id}"
			class="flex snap-x snap-mandatory overflow-x-auto scrollbar-hidden"
		>
			{#each Object.keys(groupedMessageIds) as modelIdx}
				{#if groupedMessageIdsIdx[modelIdx] !== undefined && groupedMessageIds[modelIdx].messageIds.length > 0}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					{@const _messageId =
						groupedMessageIds[modelIdx].messageIds[groupedMessageIdsIdx[modelIdx]]}

					<div
						class=" snap-center w-full max-w-full m-1 border {history.messages[messageId]
							?.modelIdx == modelIdx
							? `border-gray-100 dark:border-gray-850 border-[1.5px] ${
									$mobile ? 'min-w-full' : 'min-w-80'
								}`
							: `border-gray-100 dark:border-gray-850 border-dashed ${
									$mobile ? 'min-w-full' : 'min-w-80'
								}`} transition-all p-5 rounded-2xl"
						onclick={async () => {
							if (messageId != _messageId) {
								let currentMessageId = _messageId;
								let messageChildrenIds = history.messages[currentMessageId].childrenIds;
								while (messageChildrenIds.length !== 0) {
									currentMessageId = messageChildrenIds.at(-1);
									messageChildrenIds = history.messages[currentMessageId].childrenIds;
								}
								history.currentId = currentMessageId;

								await tick();
								await updateChat();
								triggerScroll();
							}
						}}
					>
						{#key history.currentId}
							{#if message}
								<ResponseMessage
									{actionMessage}
									{addMessages}
									{chatId}
									{continueResponse}
									{deleteMessage}
									{editMessage}
									{history}
									isLastMessage={true}
									messageId={_messageId}
									{rateMessage}
									{readOnly}
									regenerateResponse={async (message) => {
										regenerateResponse(message);
										await tick();
										groupedMessageIdsIdx[modelIdx] =
											groupedMessageIds[modelIdx].messageIds.length - 1;
									}}
									{saveMessage}
									showNextMessage={() => showNextMessage(modelIdx)}
									showPreviousMessage={() => showPreviousMessage(modelIdx)}
									siblings={groupedMessageIds[modelIdx].messageIds}
									{submitMessage}
									{updateChat}
								/>
							{/if}
						{/key}
					</div>
				{/if}
			{/each}
		</div>

		{#if !readOnly}
			{#if !Object.keys(groupedMessageIds).find((modelIdx) => {
				const { messageIds } = groupedMessageIds[modelIdx];
				const _messageId = messageIds[groupedMessageIdsIdx[modelIdx]];
				return !history.messages[_messageId]?.done ?? false;
			})}
				<div class="flex justify-end">
					<div class="w-full">
						{#if history.messages[messageId]?.merged?.status}
							{@const message = history.messages[messageId]?.merged}

							<div class="w-full rounded-xl pl-5 pr-2 py-2">
								<Name>
									Merged Response

									{#if message.timestamp}
										<span
											class=" self-center invisible group-hover:visible text-gray-400 text-xs font-medium uppercase ml-0.5 -mt-0.5"
										>
											{dayjs(message.timestamp * 1000).format('LT')}
										</span>
									{/if}
								</Name>

								<div class="mt-1 markdown-prose w-full min-w-full">
									{#if (message?.content ?? '') === ''}
										<Skeleton />
									{:else}
										<Markdown id="merged" content={message.content ?? ''} />
									{/if}
								</div>
							</div>
						{/if}
					</div>

					{#if isLastMessage}
						<div class=" shrink-0 text-gray-600 dark:text-gray-500 mt-1">
							<Tooltip content={$i18n.t('Merge Responses')} placement="bottom">
								<button
									id="merge-response-button"
									class="{true
										? 'visible'
										: 'invisible group-hover:visible'} p-1 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition regenerate-response-button"
									onclick={() => {
										mergeResponsesHandler();
									}}
									type="button"
								>
									<Merge className=" size-5 " />
								</button>
							</Tooltip>
						</div>
					{/if}
				</div>
			{/if}
		{/if}
	</div>
{/if}

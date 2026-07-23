<script lang="ts">
	import { onDestroy, onMount, tick, getContext } from 'svelte';
	import { createEventDispatcher } from 'svelte';

	import { mobile, models, settings } from '$lib/stores';

	import { generateMoACompletion } from '$lib/apis';
	import { createOpenAITextStream } from '$lib/apis/streaming';
	import { groupMessageIdsByModel, isChatMessageLoaded } from '$lib/utils/chatHistoryWindow';

	import ResponseMessage from './ResponseMessage.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Merge from '$lib/components/icons/Merge.svelte';

	import Markdown from './Markdown.svelte';
	import Name from './Name.svelte';
	import Skeleton from './Skeleton.svelte';
	import ProfileImage from './ProfileImage.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import equal from 'fast-deep-equal';
	import { formatMessageTimestamp, formatMessageTimestampFull } from '$lib/utils';
	const i18n = getContext('i18n');

	export let chatId;
	export let history;
	export let messageId;
	export let selectedModels = [];
	export let navigateToMessageId: (messageId: string) => Promise<boolean>;
	export let ensureMessageLoaded: (messageId: string) => Promise<boolean>;

	export let isLastMessage;
	export let readOnly = false;
	export let preview = false;
	export let editCodeBlock = true;

	export let setInputText: Function = () => {};
	export let updateChat: Function;
	export let editMessage: Function;
	export let saveMessage: Function;
	export let rateMessage: Function;
	export let actionMessage: Function;

	export let submitMessage: Function;
	export let deleteMessage: Function;

	export let continueResponse: Function;
	export let regenerateResponse: Function;
	export let mergeResponses: Function;

	export let addMessages: Function;
	export let forkHandler: Function | null = null;

	export let triggerScroll: Function;

	export let topPadding = false;
	export let onInsertToNote: ((content: string) => void) | null = null;

	const dispatch = createEventDispatcher();

	let currentMessageId;
	let parentMessage;
	let groupedMessageIds = {};
	let groupedMessageIdsIdx = {};

	let selectedModelIdx = null;
	let destroyed = false;
	onDestroy(() => {
		destroyed = true;
	});

	let message = structuredClone(history.messages[messageId]);
	$: if (history.messages) {
		const source = history.messages[messageId];
		if (source) {
			if (message.content !== source.content || message.done !== source.done) {
				message = structuredClone(source);
			} else if (!equal(message, source)) {
				message = structuredClone(source);
			}
		}
	}

	const getDeepestLeafId = (rootMessageId: string) => {
		let leafId = rootMessageId;
		const visited = new Set<string>();

		while (leafId && !visited.has(leafId)) {
			visited.add(leafId);
			const childrenIds = history.messages[leafId]?.childrenIds ?? [];
			if (childrenIds.length === 0) break;
			leafId = childrenIds.at(-1);
		}

		return leafId;
	};

	const navigateToGroupedMessage = async (modelIdx, messageIdx) => {
		const messageIds = groupedMessageIds[modelIdx]?.messageIds ?? [];
		if (messageIds.length === 0) return false;

		const nextMessageIdx = Math.max(0, Math.min(messageIdx, messageIds.length - 1));
		const leafId = getDeepestLeafId(messageIds[nextMessageIdx]);
		if (!(await navigateToMessageId(leafId))) return false;

		groupedMessageIdsIdx[modelIdx] = nextMessageIdx;
		selectedModelIdx = Number(modelIdx);
		triggerScroll();
		return true;
	};

	const gotoMessage = async (modelIdx, messageIdx) =>
		await navigateToGroupedMessage(modelIdx, messageIdx);

	const showPreviousMessage = async (modelIdx) =>
		await navigateToGroupedMessage(modelIdx, groupedMessageIdsIdx[modelIdx] - 1);

	const showNextMessage = async (modelIdx) =>
		await navigateToGroupedMessage(modelIdx, groupedMessageIdsIdx[modelIdx] + 1);

	const initHandler = async () => {
		console.log('multiresponse:initHandler');
		await tick();

		currentMessageId = messageId;
		parentMessage = history.messages[messageId].parentId
			? history.messages[history.messages[messageId].parentId]
			: null;

		const unloadedSiblingIds = (parentMessage?.childrenIds ?? []).filter(
			(id) => !isChatMessageLoaded(history, id)
		);
		await Promise.all(unloadedSiblingIds.map((id) => ensureMessageLoaded(id)));
		if (destroyed) return;
		await tick();

		parentMessage = history.messages[messageId].parentId
			? history.messages[history.messages[messageId].parentId]
			: null;
		groupedMessageIds = groupMessageIdsByModel(parentMessage, history.messages);

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

		selectedModelIdx =
			history.messages[messageId]?.modelIdx ??
			Number(
				Object.keys(groupedMessageIds).find((modelIdx) =>
					groupedMessageIds[modelIdx].messageIds.includes(messageId)
				) ?? 0
			);

		console.log(groupedMessageIds, groupedMessageIdsIdx);

		await tick();
	};

	const onGroupClick = async (_messageId, modelIdx) => {
		if (messageId != _messageId) {
			const messageIdx = groupedMessageIds[modelIdx]?.messageIds.indexOf(_messageId) ?? -1;
			if (messageIdx !== -1) await navigateToGroupedMessage(modelIdx, messageIdx);
		}
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

		if ($settings?.scrollOnBranchChange ?? true) {
			const messageElement = document.getElementById(`message-${messageId}`);
			if (messageElement) {
				messageElement.scrollIntoView({ block: 'start' });
			}
		}
	});
</script>

{#if parentMessage}
	<div>
		<div
			class="flex snap-x snap-mandatory overflow-x-auto scrollbar-hidden"
			id="responses-container-{chatId}-{parentMessage.id}"
		>
			{#if $settings?.displayMultiModelResponsesInTabs ?? false}
				<div class="w-full">
					<div
						class=" flex w-full mb-4.5 border-b border-gray-200 dark:border-gray-850 {preview
							? 'hidden'
							: ''}"
					>
						<div
							class="flex gap-2 scrollbar-none overflow-x-auto w-fit text-center font-normal bg-transparent pt-1 text-sm"
							on:wheel|preventDefault={(e) => {
								e.currentTarget.scrollLeft += e.deltaY;
							}}
						>
							{#each Object.keys(groupedMessageIds) as modelIdx}
								{#if groupedMessageIdsIdx[modelIdx] !== undefined && (groupedMessageIds[modelIdx]?.messageIds ?? []).length > 0}
									<!-- svelte-ignore a11y-no-static-element-interactions -->
									<!-- svelte-ignore a11y-click-events-have-key-events -->

									{@const _messageId =
										groupedMessageIds[modelIdx].messageIds[groupedMessageIdsIdx[modelIdx]]}

									{@const modelId =
										history.messages[_messageId]?.model ?? parentMessage.models?.[Number(modelIdx)]}
									{@const model = $models.find((m) => m.id === modelId)}

									<button
										class="min-w-fit {selectedModelIdx == modelIdx
											? ' dark:border-gray-300 '
											: ' opacity-35 border-transparent'} pb-1.5 px-2.5 transition border-b-2"
										on:click={async () => {
											if (selectedModelIdx != modelIdx) {
												selectedModelIdx = modelIdx;
											}

											await onGroupClick(_messageId, modelIdx);
										}}
									>
										<div class="flex items-center gap-1.5">
											<div class="-translate-y-[1px]">
												{model?.name ?? history.messages[_messageId]?.modelName ?? modelId}
											</div>
										</div>
									</button>
								{/if}
							{/each}
						</div>
					</div>

					{#if selectedModelIdx !== null}
						{#key history.currentId}
							{#if message}
								<ResponseMessage
									{chatId}
									{history}
									messageId={message?.id}
									{selectedModels}
									isLastMessage={true}
									siblings={groupedMessageIds[selectedModelIdx].messageIds}
									gotoMessage={(message, messageIdx) => gotoMessage(selectedModelIdx, messageIdx)}
									showPreviousMessage={() => showPreviousMessage(selectedModelIdx)}
									showNextMessage={() => showNextMessage(selectedModelIdx)}
									{setInputText}
									{updateChat}
									{editMessage}
									{saveMessage}
									{rateMessage}
									{deleteMessage}
									{actionMessage}
									{submitMessage}
									{continueResponse}
									regenerateResponse={async (message, prompt = null) => {
										regenerateResponse(message, prompt);
										await tick();
										groupedMessageIdsIdx[selectedModelIdx] =
											groupedMessageIds[selectedModelIdx].messageIds.length - 1;
									}}
									{addMessages}
									{forkHandler}
									{readOnly}
									{preview}
									{topPadding}
									{onInsertToNote}
								/>
							{/if}
						{/key}
					{/if}
				</div>
			{:else}
				{#each Object.keys(groupedMessageIds) as modelIdx}
					{#if groupedMessageIdsIdx[modelIdx] !== undefined && groupedMessageIds[modelIdx].messageIds.length > 0}
						<!-- svelte-ignore a11y-no-static-element-interactions -->
						<!-- svelte-ignore a11y-click-events-have-key-events -->
						{@const _messageId =
							groupedMessageIds[modelIdx].messageIds[groupedMessageIdsIdx[modelIdx]]}

						<div
							class="snap-center w-full max-w-full transition-all {preview
								? ''
								: `m-1 border p-5 rounded-2xl ${
										history.messages[messageId]?.modelIdx == modelIdx
											? `bg-gray-50 dark:bg-gray-850 border-gray-100 dark:border-gray-800 border-2 ${
													$mobile ? 'min-w-full' : 'min-w-80'
												}`
											: `border-gray-100/30 dark:border-gray-850/30 border-dashed ${
													$mobile ? 'min-w-full' : 'min-w-80'
												}`
									}`}"
							on:click={async () => {
								await onGroupClick(_messageId, modelIdx);
							}}
						>
							{#key history.currentId}
								{#if message}
									<ResponseMessage
										{chatId}
										{history}
										messageId={_messageId}
										{selectedModels}
										isLastMessage={true}
										siblings={groupedMessageIds[modelIdx].messageIds}
										gotoMessage={(message, messageIdx) => gotoMessage(modelIdx, messageIdx)}
										showPreviousMessage={() => showPreviousMessage(modelIdx)}
										showNextMessage={() => showNextMessage(modelIdx)}
										{setInputText}
										{updateChat}
										{editMessage}
										{saveMessage}
										{rateMessage}
										{deleteMessage}
										{actionMessage}
										{submitMessage}
										{continueResponse}
										regenerateResponse={async (message, prompt = null) => {
											regenerateResponse(message, prompt);
											await tick();
											groupedMessageIdsIdx[modelIdx] =
												groupedMessageIds[modelIdx].messageIds.length - 1;
										}}
										{addMessages}
										{forkHandler}
										{readOnly}
										{preview}
										{editCodeBlock}
										{topPadding}
										{onInsertToNote}
									/>
								{/if}
							{/key}
						</div>
					{/if}
				{/each}
			{/if}
		</div>

		{#if !preview && !readOnly}
			{#if !Object.keys(groupedMessageIds).find((modelIdx) => {
				const { messageIds } = groupedMessageIds[modelIdx];
				const _messageId = messageIds[groupedMessageIdsIdx[modelIdx]];
				return !history.messages[_messageId]?.done ?? false;
			})}
				<div class="flex justify-end">
					<div class="w-full">
						{#if history.messages[messageId]?.merged?.status}
							{@const message = history.messages[messageId]?.merged}

							<div class="w-full rounded-xl pl-5 pr-2 py-2 mt-2">
								<Name>
									{$i18n.t('Merged Response')}
								</Name>

								<div class="mt-1 w-full min-w-full">
									{#if (message?.content ?? '') === ''}
										<Skeleton />
									{:else}
										<div class="markdown-prose">
											<Markdown id={`merged`} content={message.content ?? ''} />
										</div>
									{/if}
								</div>

								{#if message.timestamp}
									<div
										class="mt-0.5 flex justify-start whitespace-nowrap text-gray-600 dark:text-gray-500"
									>
										<Tooltip
											className="flex self-center"
											content={formatMessageTimestampFull(message.timestamp * 1000)}
											placement="bottom"
										>
											<time
												datetime={new Date(message.timestamp * 1000).toISOString()}
												class="invisible group-hover:visible ml-1 shrink-0 whitespace-nowrap text-[0.6875rem] tabular-nums text-gray-400 dark:text-gray-600 select-none"
											>
												{formatMessageTimestamp(message.timestamp * 1000)}
											</time>
										</Tooltip>
									</div>
								{/if}
							</div>
						{/if}
					</div>

					{#if isLastMessage}
						<div class=" shrink-0 text-gray-600 dark:text-gray-500 mt-1">
							<Tooltip content={$i18n.t('Merge Responses')} placement="bottom">
								<button
									type="button"
									id="merge-response-button"
									class="{true
										? 'visible'
										: 'invisible group-hover:visible'} p-1 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
									on:click={() => {
										mergeResponsesHandler();
									}}
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

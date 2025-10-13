<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { tick, getContext, onMount, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import { settings } from '$lib/stores';
	import { copyToClipboard } from '$lib/utils';

	import MultiResponseMessages from './MultiResponseMessages.svelte';
	import ResponseMessage from './ResponseMessage.svelte';
	import UserMessage from './UserMessage.svelte';

	export let chatId;
	export let selectedModels = [];
	export let idx = 0;

	export let history;
	export let messageId;

	export let user;

	export let setInputText: Function = () => {};
	export let gotoMessage;
	export let showPreviousMessage;
	export let showNextMessage;
	export let updateChat;

	export let editMessage;
	export let saveMessage;
	export let deleteMessage;
	export let rateMessage;
	export let actionMessage;
	export let submitMessage;

	export let regenerateResponse;
	export let continueResponse;
	export let mergeResponses;

	export let addMessages;
	export let triggerScroll;
	export let readOnly = false;
	export let editCodeBlock = true;
	export let topPadding = false;
</script>

<div
	class="flex flex-col justify-between px-5 mb-3 w-full {($settings?.widescreenMode ?? null)
		? 'max-w-full'
		: 'max-w-5xl'} mx-auto rounded-lg group"
>
	{#if history.messages[messageId]}
		{#if history.messages[messageId].role === 'user'}
			<UserMessage
				{user}
				{chatId}
				{history}
				{messageId}
				isFirstMessage={idx === 0}
				siblings={history.messages[messageId].parentId !== null
					? (history.messages[history.messages[messageId].parentId]?.childrenIds ?? [])
					: (Object.values(history.messages)
							.filter((message) => message.parentId === null)
							.map((message) => message.id) ?? [])}
				{gotoMessage}
				{showPreviousMessage}
				{showNextMessage}
				{editMessage}
				{deleteMessage}
				{readOnly}
				{editCodeBlock}
				{topPadding}
			/>
		{:else if history.messages[messageId].isMultiAgent}
			<!-- 九天平台多智能体消息 -->
			<div class="w-full">
				<div class="flex items-start space-x-3 p-4 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg border border-blue-200 dark:border-blue-700">
					<div class="flex-shrink-0">
						<div class="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
							<span class="text-white text-sm font-bold">🤖</span>
						</div>
					</div>
					<div class="flex-1 min-w-0">
						<div class="flex items-center space-x-2 mb-3">
							<span class="text-sm font-semibold text-gray-900 dark:text-gray-100">九天平台多智能体协作</span>
							{#if history.messages[messageId].currentAgent}
								<div class="flex items-center space-x-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 rounded-full">
									<div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
									<span class="text-xs text-green-700 dark:text-green-300">
										{history.messages[messageId].currentAgent.name} 正在回答
									</span>
								</div>
							{/if}
						</div>
						
						<div class="flex flex-wrap gap-1 mb-3">
							{#each history.messages[messageId].models || [] as model, index}
								<span class="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-200 rounded-full border border-blue-200 dark:border-blue-700 flex items-center space-x-1">
									<div class="w-2 h-2 bg-blue-500 rounded-full"></div>
									<span>{model.name || model.id}</span>
								</span>
							{/each}
						</div>
						
						<div class="prose dark:prose-invert max-w-none">
							<div class="whitespace-pre-wrap text-gray-800 dark:text-gray-200 leading-relaxed">
								{history.messages[messageId].content}
								{#if history.messages[messageId].content.endsWith('思考中...')}
									<span class="inline-block w-1 h-4 bg-blue-500 animate-pulse ml-1"></span>
								{/if}
							</div>
						</div>
						
						{#if history.messages[messageId].models && history.messages[messageId].models.length > 1}
							<div class="mt-3 pt-3 border-t border-blue-200 dark:border-blue-700">
								<div class="text-xs text-gray-500 dark:text-gray-400 flex items-center space-x-1">
									<span>💡</span>
									<span>多个AI模型正在协作为您提供更全面的回答</span>
								</div>
							</div>
						{/if}
					</div>
				</div>
			</div>
		{:else if (history.messages[history.messages[messageId].parentId]?.models?.length ?? 1) === 1}
			<ResponseMessage
				{chatId}
				{history}
				{messageId}
				{selectedModels}
				isLastMessage={messageId === history.currentId}
				siblings={history.messages[history.messages[messageId].parentId]?.childrenIds ?? []}
				{setInputText}
				{gotoMessage}
				{showPreviousMessage}
				{showNextMessage}
				{updateChat}
				{editMessage}
				{saveMessage}
				{rateMessage}
				{actionMessage}
				{submitMessage}
				{deleteMessage}
				{continueResponse}
				{regenerateResponse}
				{addMessages}
				{readOnly}
				{editCodeBlock}
				{topPadding}
			/>
		{:else}
			<MultiResponseMessages
				bind:history
				{chatId}
				{messageId}
				{selectedModels}
				isLastMessage={messageId === history?.currentId}
				{setInputText}
				{updateChat}
				{editMessage}
				{saveMessage}
				{rateMessage}
				{actionMessage}
				{submitMessage}
				{deleteMessage}
				{continueResponse}
				{regenerateResponse}
				{mergeResponses}
				{triggerScroll}
				{addMessages}
				{readOnly}
				{editCodeBlock}
				{topPadding}
			/>
		{/if}
	{/if}
</div>

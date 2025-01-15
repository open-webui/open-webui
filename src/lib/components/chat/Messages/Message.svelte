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
	import Badge from '$lib/components/common/Badge.svelte';

	import  Feedback from '$lib/components/admin/Evaluations/Feedbacks.svelte';

	export let chatId;
	export let idx = 0;

	export let history;
	export let messageId;

	export let user;

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

	export let feedback: Feedback | undefined = undefined;
</script>

<div
	class="flex flex-col justify-between px-5 mb-3 w-full {($settings?.widescreenMode ?? null)
		? 'max-w-full'
		: 'max-w-5xl'} mx-auto rounded-lg group"
>
	{#if history.messages[messageId]}
		<div style="border: {feedback ? feedback.data.rating === 1 ? '2px solid green' : '2px solid red' : 'none'}; border-radius: 10px; padding: 10px;">
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
		</div>

		{#if feedback}
			<div class="flex gap-2 mt-2">
				<div class="flex items-start mt-1">
					{#if feedback.data?.rating === 1}
						<Badge type="success" content={$i18n.t('Feedback')} />
					{:else if feedback.data?.rating === 0}
						<Badge type="info" content={$i18n.t('Feedback')} />
					{:else if feedback.data?.rating === -1}
						<Badge type="error" content={$i18n.t('Feedback')} />
					{/if}
				</div>
				<div class="flex flex-col gap-1">
					<div>
						{$i18n.t('Comment')}: {feedback.data?.comment}
					</div>
					<div>
						{$i18n.t('Reason')}: 
						{#if feedback.data?.reason === 'accurate_information'}
							{$i18n.t('Accurate information')}
						{:else if feedback.data?.reason === 'followed_instructions_perfectly'}
							{$i18n.t('Followed instructions perfectly')}
						{:else if feedback.data?.reason === 'showcased_creativity'}
							{$i18n.t('Showcased creativity')}
						{:else if feedback.data?.reason === 'positive_attitude'}
							{$i18n.t('Positive attitude')}
						{:else if feedback.data?.reason === 'attention_to_detail'}
							{$i18n.t('Attention to detail')}
						{:else if feedback.data?.reason === 'thorough_explanation'}
							{$i18n.t('Thorough explanation')}
						{:else if feedback.data?.reason === 'dont_like_the_style'}
							{$i18n.t("Don't like the style")}
						{:else if feedback.data?.reason === 'too_verbose'}
							{$i18n.t('Too verbose')}
						{:else if feedback.data?.reason === 'not_helpful'}
							{$i18n.t('Not helpful')}
						{:else if feedback.data?.reason === 'not_factually_correct'}
							{$i18n.t('Not factually correct')}
						{:else if feedback.data?.reason === 'didnt_fully_follow_instructions'}
							{$i18n.t("Didn't fully follow instructions")}
						{:else if feedback.data?.reason === 'refused_when_it_shouldnt_have'}
							{$i18n.t("Refused when it shouldn't have")}
						{:else if feedback.data?.reason === 'being_lazy'}
							{$i18n.t('Being lazy')}
						{:else if feedback.data?.reason === 'other'}
							{$i18n.t('Other')}
						{:else}
							{feedback.data?.reason}
						{/if}
					</div>
					<div>
						{$i18n.t('Rating')}: {feedback.data?.details?.rating}/10
					</div>
				</div>
			</div>
		{/if}
	{/if}
</div>

<script lang="ts">
	import { getContext, onDestroy, tick } from 'svelte';
	import { LinkPreview } from 'bits-ui';

	import { getChatById } from '$lib/apis/chats';
	import Messages from '$lib/components/chat/Messages.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { user } from '$lib/stores';

	const i18n: any = getContext('i18n');

	export let chatId = '';
	export let title = '';
	export let openPreview = false;
	export let side: 'left' | 'right' | 'bottom' | 'top' = 'right';
	export let align: 'start' | 'end' | 'center' = 'start';
	export let sideOffset = 12;

	let messagesContainerElement: HTMLElement | null = null;

	let selectedModels = [''];
	let history: any = null;
	let previewReady = false;
	let loading = false;
	let error = '';
	let requestedChatId = '';
	let loadToken = 0;

	$: messagesContainerId = `chat-hover-preview-messages-${chatId}`;

	const scrollPreviewToBottom = async () => {
		await tick();
		requestAnimationFrame(() => {
			if (messagesContainerElement) {
				messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;

				requestAnimationFrame(() => {
					if (messagesContainerElement) {
						messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
					}
				});
			}
		});
		setTimeout(() => {
			if (messagesContainerElement) {
				messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
			}
		}, 80);
	};

	const loadChatPreview = async (id: string) => {
		if (!id || loading || requestedChatId === id) return;

		const token = ++loadToken;
		requestedChatId = id;
		loading = true;
		error = '';
		previewReady = false;
		history = null;
		selectedModels = [''];

		const chat = await getChatById(localStorage.token, id).catch(() => null);
		if (token !== loadToken) return;

		if (chat?.chat?.history) {
			selectedModels = Array.isArray(chat.chat.models)
				? chat.chat.models
				: [chat.chat.models ?? ''];
			history = chat.chat.history;
			previewReady = true;
			scrollPreviewToBottom();
		} else if (chat) {
			previewReady = true;
		} else {
			error = $i18n.t('Failed to load chat preview');
		}

		loading = false;
	};

	$: if (openPreview && chatId && requestedChatId !== chatId) {
		loadChatPreview(chatId);
	}

	$: if (openPreview && previewReady) {
		scrollPreviewToBottom();
	}

	onDestroy(() => {
		loadToken += 1;
	});
</script>

{#if openPreview}
	<LinkPreview.Portal>
		<LinkPreview.Content
			class="z-[9999] hidden max-h-[min(17.5rem,calc(100vh-1.5rem))] w-[20rem] max-w-[calc(100vw-1.5rem)] overflow-hidden rounded-2xl bg-white shadow-[0_16px_40px_-28px_rgba(0,0,0,0.55)] ring-1 ring-black/5 transition md:block dark:bg-gray-850 dark:text-white dark:ring-white/10"
			{side}
			{align}
			{sideOffset}
		>
			<div class="border-b border-gray-50/60 px-3 py-2 dark:border-gray-800/25">
				<div class="truncate text-[13px] font-medium leading-5 text-gray-900 dark:text-gray-100">
					{title || $i18n.t('Chat')}
				</div>
			</div>
			<div
				id={messagesContainerId}
				bind:this={messagesContainerElement}
				class="max-h-[min(15rem,calc(100vh-4rem))] overflow-y-auto bg-white scrollbar-hover @container dark:bg-gray-850"
			>
				{#if loading}
					<div
						class="flex w-full items-center justify-center py-8 text-gray-500 dark:text-gray-400"
					>
						<Spinner className="size-5" />
					</div>
				{:else if error}
					<div
						class="flex w-full items-center justify-center px-6 py-6 text-center text-sm text-gray-500 dark:text-gray-400"
					>
						{error}
					</div>
				{:else if previewReady}
					<Messages
						className="flex w-full pt-2 pb-0 [&_.message-listitem]:!mb-1 [&_.message-listitem]:!max-w-none [&_.message-listitem]:!px-3 [&_.pb-18]:!pb-1.5 [&_.markdown-prose]:!text-xs [&_.markdown-prose]:!leading-snug [&_.whitespace-pre-wrap]:!text-xs [&_.whitespace-pre-wrap]:!leading-snug [&_.text-\[0\.9375rem\]]:!text-xs [&_.text-sm]:!text-xs [&_.tool-call-body_pre]:!text-[11px] [&_.rounded-3xl]:!rounded-2xl [&_.chat-user_.rounded-3xl]:!bg-gray-50 dark:[&_.chat-user_.rounded-3xl]:!bg-gray-800 [&_.px-4]:!px-3 [&_.py-3]:!py-2 [&_.py-1\.5]:!py-1"
						chatId={`chat-hover-preview-${chatId}`}
						user={$user}
						prompt=""
						readOnly={true}
						compactPreview={true}
						{selectedModels}
						atSelectedModel={null}
						{history}
						autoScroll={true}
						{messagesContainerId}
						messagesCount={8}
						sendMessage={() => {}}
						continueResponse={() => {}}
						regenerateResponse={() => {}}
						mergeResponses={() => {}}
						chatActionHandler={() => {}}
					/>
				{/if}
			</div>
		</LinkPreview.Content>
	</LinkPreview.Portal>
{/if}

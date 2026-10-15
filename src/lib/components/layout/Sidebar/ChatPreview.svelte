<script lang="ts">
	import { getContext, onDestroy, tick } from 'svelte';
	import { getChatById, getChatByShareId } from '$lib/apis/chats';
	import { convertMessagesToHistory, getDeepestChildId } from '$lib/utils';
	import Messages from '$lib/components/chat/Messages.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { user } from '$lib/stores';

	const i18n: any = getContext('i18n');
	export let chatId = '';
	export let shareId = '';
	export let messageId = '';
	export let className = 'h-full';
	let container: HTMLDivElement;
	let messagesComponent: Messages;
	let history: any = null;
	let selectedModels: string[] = [];
	let loading = true;
	let error = false;
	let generation = 0;
	$: containerId = `chat-preview-${shareId || chatId}`;
	$: load(chatId, shareId, messageId);

	async function load(id: string, shared: string, target: string) {
		const version = ++generation;
		loading = true;
		error = false;
		history = null;
		if (!id && !shared) {
			loading = false;
			return;
		}
		const chat = await (
			shared ? getChatByShareId(localStorage.token, shared) : getChatById(localStorage.token, id)
		).catch(() => null);
		if (version !== generation) return;
		if (chat) {
			history = chat.chat?.history ?? convertMessagesToHistory(chat.chat?.messages ?? []);
			selectedModels = Array.isArray(chat.chat?.models) ? chat.chat.models : [];
			if (target && history.messages?.[target])
				history.currentId = getDeepestChildId(history, target);
		} else error = true;
		loading = false;
		await tick();
		if (version !== generation) return;
		if (target && history?.messages?.[target]) await messagesComponent?.scrollToMessage(target);
		else if (container) container.scrollTop = container.scrollHeight;
	}
	onDestroy(() => (generation += 1));
</script>

<div
	id={containerId}
	bind:this={container}
	class="min-h-0 overflow-y-auto scrollbar-hover @container {className}"
>
	{#if loading}<div
			class="flex h-full min-h-20 items-center justify-center text-gray-500 dark:text-gray-400"
		>
			<Spinner className="size-4" />
		</div>
	{:else if error}<div class="px-3 py-6 text-center text-xs text-gray-500 dark:text-gray-400">
			<p>{$i18n.t('Failed to load chat preview')}</p>
			<button
				class="mt-2 underline underline-offset-2"
				on:click={() => load(chatId, shareId, messageId)}>{$i18n.t('Try again')}</button
			>
		</div>
	{:else if history}<Messages
			bind:this={messagesComponent}
			className="flex w-full pt-2 pb-0 [&_.message-listitem]:!mb-1 [&_.message-listitem]:!max-w-none [&_.message-listitem]:!px-3 [&_.pb-18]:!pb-1.5 [&_.markdown-prose]:!text-xs [&_.markdown-prose]:!leading-snug [&_.whitespace-pre-wrap]:!text-xs [&_.whitespace-pre-wrap]:!leading-snug [&_.text-\[0\.9375rem\]]:!text-xs [&_.text-sm]:!text-xs [&_.tool-call-body_pre]:!text-[0.6875rem] [&_.rounded-3xl]:!rounded-2xl [&_.chat-user_.rounded-3xl]:!bg-gray-50 dark:[&_.chat-user_.rounded-3xl]:!bg-gray-800 [&_.px-4]:!px-3 [&_.py-3]:!py-2 [&_.py-1\.5]:!py-1 [&_button]:!pointer-events-none [&_.font-medium]:!font-normal [&_.font-semibold]:!font-normal"
			chatId={containerId}
			user={$user}
			prompt=""
			readOnly={true}
			compactPreview={true}
			{selectedModels}
			atSelectedModel={null}
			{history}
			autoScroll={!messageId}
			messagesContainerId={containerId}
			messagesCount={8}
			sendMessage={() => {}}
			continueResponse={() => {}}
			regenerateResponse={() => {}}
			mergeResponses={() => {}}
			chatActionHandler={() => {}}
		/>{/if}
</div>

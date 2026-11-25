<script lang="ts">
	import { getContext, onDestroy, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { socket } from '$lib/stores';
	import { stopTasksByChatId } from '$lib/apis';
	import { deleteChatById, getChatChildren, type ChatChild } from '$lib/apis/chats';
	import { formatElapsedShort } from '$lib/utils';
	import type { AppLayoutContext } from '$lib/types';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import List from '$lib/components/icons/List.svelte';
	import StatusDetails from './StatusDetails.svelte';

	const i18n = getContext<any>('i18n');
	const appLayout = getContext<AppLayoutContext | undefined>('appLayout');

	export let chatId: string;
	export let contextUsage: any = null;
	export let queuedCount = 0;
	export let taskCount = 0;
	export let onCompact: (() => void) | undefined = undefined;

	let show = false;
	let children: ChatChild[] = [];
	let loadedChatId = '';

	let showDone = false;
	const order = ['waiting', 'running', 'scheduled'];
	$: active = children
		.filter(({ status }) => status !== 'done')
		.sort((a, b) => order.indexOf(a.status) - order.indexOf(b.status));
	$: done = children.filter(({ status }) => status === 'done');
	$: waiting = children.some(({ status }) => status === 'waiting');
	$: running = children.some(({ status }) => status === 'running');

	const load = async () => {
		const id = chatId;
		const result = await getChatChildren(localStorage.token, id).catch(() => null);
		if (result && id === chatId) children = result;
	};

	$: if (chatId !== loadedChatId) {
		loadedChatId = chatId;
		children = [];
		load();
	}

	const onEvent = (event: any) => {
		if (
			event.chat_id === chatId &&
			['chat:children', 'chat:active', 'chat:reload'].includes(event.data?.type)
		)
			load();
	};

	// Sub-agents report only that they started.
	const interval = setInterval(() => {
		if (!document.hidden && (waiting || running)) load();
	}, 3000);

	onMount(() => $socket?.on('events', onEvent));
	onDestroy(() => {
		clearInterval(interval);
		$socket?.off('events', onEvent);
	});

	const open = (child: ChatChild) => {
		show = false;
		appLayout?.openPageTab?.({ href: `/c/${child.id}`, label: child.title });
	};

	const stop = async (child: ChatChild) => {
		try {
			if (child.type === 'timer') await deleteChatById(localStorage.token, child.id);
			else await stopTasksByChatId(localStorage.token, child.id);
		} catch (error) {
			toast.error(`${error}`);
		}
		await load();
	};
</script>

{#snippet row(child: ChatChild)}
	<li class="flex min-h-6 items-center gap-2">
		<button
			type="button"
			class="flex min-w-0 flex-1 items-center gap-2 text-left enabled:hover:text-base-900 dark:enabled:hover:text-base-100"
			disabled={child.type === 'timer' || !appLayout?.openPageTab}
			on:click={() => open(child)}
		>
			{#if child.status === 'waiting'}
				<span
					class="mx-0.75 size-1.5 shrink-0 rounded-full bg-yellow-500"
					role="img"
					aria-label={$i18n.t('Waiting for your answer')}
				></span>
			{:else if child.status === 'running'}
				<Spinner className="size-3 shrink-0" />
			{/if}
			<span dir="auto" class="truncate">{child.title}</span>
		</button>
		<span class="shrink-0 tabular-nums text-base-400 dark:text-base-600">
			{child.due_at
				? new Date(child.due_at * 1000).toLocaleTimeString([], { timeStyle: 'short' })
				: formatElapsedShort(child.created_at)}
		</span>
		{#if child.status !== 'done'}
			<button
				type="button"
				class="shrink-0 hover:text-base-900 dark:hover:text-base-100"
				on:click={() => stop(child)}
			>
				{child.type === 'timer' ? $i18n.t('Cancel') : $i18n.t('Stop')}
			</button>
		{/if}
	</li>
{/snippet}

<Dropdown bind:show align="end">
	<Tooltip content={$i18n.t('Status')}>
		<button
			type="button"
			class="flex size-6 cursor-pointer items-center justify-center rounded-lg text-base-500 transition hover:bg-base-50/40 hover:text-base-700 dark:text-base-400 dark:hover:bg-base-800/40 dark:hover:text-base-200"
			aria-label={$i18n.t('Status')}
		>
			<List className="size-4.5" strokeWidth="1" />
		</button>
	</Tooltip>

	<div
		slot="content"
		class="app-dropdown-menu z-50 w-80 max-w-[calc(100vw-1rem)] rounded-xl border border-base-100 bg-base-0 px-3 py-2 text-xs text-base-600 shadow-lg dark:border-base-800 dark:bg-base-850 dark:text-base-400"
	>
		<div class="mb-0.5 text-base-400 dark:text-base-500">{$i18n.t('Status')}</div>
		<StatusDetails
			{contextUsage}
			{queuedCount}
			{taskCount}
			{chatId}
			onCompact={onCompact &&
				(() => {
					show = false;
					onCompact();
				})}
		/>

		{#if children.length}
			<div
				class="mb-0.5 mt-1.5 border-t border-base-100 pt-1.5 text-base-400 dark:border-base-800 dark:text-base-500"
			>
				{$i18n.t('Threads')}
			</div>
			<ul>
				{#each active as child (child.id)}
					{@render row(child)}
				{/each}
				{#if done.length}
					<li>
						<button
							type="button"
							class="flex min-h-6 w-full items-center gap-1 text-left text-base-400 hover:text-base-600 dark:text-base-500 dark:hover:text-base-300"
							aria-expanded={showDone}
							on:click={() => (showDone = !showDone)}
						>
							{done.length}
							{$i18n.t('done')}
							<ChevronDown className="size-2.5 {showDone ? 'rotate-180' : ''}" />
						</button>
					</li>
					{#if showDone}
						{#each done as child (child.id)}
							{@render row(child)}
						{/each}
					{/if}
				{/if}
			</ul>
		{/if}
	</div>
</Dropdown>

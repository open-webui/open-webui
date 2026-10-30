<script lang="ts">
	import { onDestroy, getContext, createEventDispatcher } from 'svelte';
	import type { ListeningPort } from '$lib/apis/terminal';
	import { getListeningPorts, getPortProxyUrl } from '$lib/apis/terminal';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Icon from './Icon.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher<{ previewPort: number }>();

	export let baseUrl: string;
	export let previewBaseUrl: string | null = null;
	export let apiKey: string;
	export let chatId: string | null = null;

	let ports: ListeningPort[] = [];
	let expanded = false;
	let loading = false;
	let pollTimer: ReturnType<typeof setInterval> | null = null;

	const loadPorts = async () => {
		loading = true;
		ports = await getListeningPorts(baseUrl, apiKey, chatId);
		loading = false;
	};

	const startPolling = () => {
		stopPolling();
		loadPorts();
		pollTimer = setInterval(loadPorts, 5000);
	};

	const stopPolling = () => {
		if (pollTimer) {
			clearInterval(pollTimer);
			pollTimer = null;
		}
	};

	const previewPort = (port: number) => {
		dispatch('previewPort', port);
	};

	const openPortExternal = (port: number) => {
		const url = getPortProxyUrl(previewBaseUrl ?? baseUrl, port);
		window.open(url, '_blank', 'noopener,noreferrer');
	};

	// Start polling when baseUrl is available
	$: if (baseUrl) {
		startPolling();
	}

	onDestroy(() => {
		stopPolling();
	});
</script>

<div class="px-2 py-1">
	<div
		class="flex items-center gap-1 w-full text-xs font-normal text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors duration-100"
	>
		<button class="flex flex-1 items-center gap-1" on:click={() => (expanded = !expanded)}>
			<Icon
				name="chevron-down"
				size={12}
				strokeWidth={1.4}
				class="transition-transform {expanded ? '' : '-rotate-90'}"
			/>
			{$i18n.t('Ports')}
			{#if ports.length > 0}
				<span
					class="ml-auto text-[0.625rem] px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400"
				>
					{ports.length}
				</span>
			{/if}
		</button>
		<span class="flex items-center gap-1">
			<Tooltip content={$i18n.t('Refresh')}>
				<button
					class="flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
					on:click|stopPropagation={loadPorts}
					aria-label={$i18n.t('Refresh')}
				>
					<Icon name="refresh" size={11} strokeWidth={1.4} class={loading ? 'animate-spin' : ''} />
				</button>
			</Tooltip>
		</span>
	</div>

	{#if expanded}
		<div class="mt-1 space-y-0.5 max-h-[9.375rem] overflow-y-auto">
			{#if ports.length === 0}
				<div class="text-xs text-gray-400 dark:text-gray-500 px-1 py-1">
					{$i18n.t('No servers detected')}
				</div>
			{:else}
				{#each ports as port}
					<div
						class="flex h-7 items-center w-full gap-2 px-1.5 text-xs rounded-lg hover:bg-gray-50/40 dark:hover:bg-white/4 transition-colors duration-75 group"
					>
						<button
							class="flex min-w-0 flex-1 items-center gap-2 self-stretch"
							on:click={() => previewPort(port.port)}
						>
							<span class="font-mono text-blue-500 dark:text-blue-400 shrink-0">
								:{port.port}
							</span>
							<span class="text-gray-500 dark:text-gray-400 truncate flex-1 text-left">
								{port.process ?? ''}
							</span>
						</button>
						<Tooltip content={$i18n.t('Open in new tab')}>
							<button
								class="text-gray-400 dark:text-gray-500 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition shrink-0 flex h-5 w-5 items-center justify-center rounded hover:text-gray-600 dark:hover:text-gray-300"
								aria-label={$i18n.t('Open in new tab')}
								on:click={() => openPortExternal(port.port)}
							>
								<Icon name="external-link" size={11} strokeWidth={1.4} />
							</button>
						</Tooltip>
					</div>
				{/each}
			{/if}
		</div>
	{/if}
</div>

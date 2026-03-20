<script lang="ts">
	import { onDestroy, getContext } from 'svelte';
	import type { ListeningPort } from '$lib/apis/terminal';
	import { getListeningPorts, getPortProxyUrl } from '$lib/apis/terminal';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let baseUrl: string;
	export let apiKey: string;

	let ports: ListeningPort[] = [];
	let expanded = false;
	let loading = false;
	let pollTimer: ReturnType<typeof setInterval> | null = null;

	const loadPorts = async () => {
		loading = true;
		ports = await getListeningPorts(baseUrl, apiKey);
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

	const openPort = (port: number) => {
		const url = getPortProxyUrl(baseUrl, port);
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
	<button
		class="flex items-center gap-1 w-full text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition"
		on:click={() => (expanded = !expanded)}
	>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			viewBox="0 0 20 20"
			fill="currentColor"
			class="size-3 transition-transform {expanded ? '' : '-rotate-90'}"
		>
			<path
				fill-rule="evenodd"
				d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
				clip-rule="evenodd"
			/>
		</svg>
		{$i18n.t('Ports')}
		<span class="ml-auto flex items-center gap-1">
			{#if ports.length > 0}
				<span
					class="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400"
				>
					{ports.length}
				</span>
			{/if}
			<Tooltip content={$i18n.t('Refresh')}>
				<button
					class="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
					on:click|stopPropagation={loadPorts}
					aria-label={$i18n.t('Refresh')}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-3 {loading ? 'animate-spin' : ''}"
					>
						<path
							fill-rule="evenodd"
							d="M15.312 11.424a5.5 5.5 0 0 1-9.201 2.466l-.312-.311h2.451a.75.75 0 0 0 0-1.5H4.5a.75.75 0 0 0-.75.75v3.75a.75.75 0 0 0 1.5 0v-2.127l.13.13a7 7 0 0 0 11.712-3.138.75.75 0 0 0-1.449-.39Zm-10.624-2.85a5.5 5.5 0 0 1 9.201-2.465l.312.31H11.75a.75.75 0 0 0 0 1.5h3.75a.75.75 0 0 0 .75-.75V3.42a.75.75 0 0 0-1.5 0v2.126l-.13-.129A7 7 0 0 0 3.239 8.555a.75.75 0 0 0 1.449.39Z"
							clip-rule="evenodd"
						/>
					</svg>
				</button>
			</Tooltip>
		</span>
	</button>

	{#if expanded}
		<div class="mt-1 space-y-0.5 max-h-[150px] overflow-y-auto">
			{#if ports.length === 0}
				<div class="text-xs text-gray-400 dark:text-gray-500 px-1 py-1">
					{$i18n.t('No servers detected')}
				</div>
			{:else}
				{#each ports as port}
					<button
						class="flex items-center w-full gap-2 px-1.5 py-1 text-xs rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition group"
						on:click={() => openPort(port.port)}
					>
						<span class="font-mono text-blue-500 dark:text-blue-400 shrink-0">
							:{port.port}
						</span>
						<span class="text-gray-500 dark:text-gray-400 truncate flex-1 text-left">
							{port.process ?? ''}
						</span>
						<span
							class="text-gray-400 dark:text-gray-500 opacity-0 group-hover:opacity-100 transition shrink-0"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="size-3"
							>
								<path
									fill-rule="evenodd"
									d="M4.25 5.5a.75.75 0 0 0-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 0 0 .75-.75v-4a.75.75 0 0 1 1.5 0v4A2.25 2.25 0 0 1 12.75 17h-8.5A2.25 2.25 0 0 1 2 14.75v-8.5A2.25 2.25 0 0 1 4.25 4h5a.75.75 0 0 1 0 1.5h-5Zm7.5-3.5a.75.75 0 0 0 0 1.5h2.69l-4.72 4.72a.75.75 0 0 0 1.06 1.06l4.72-4.72v2.69a.75.75 0 0 0 1.5 0v-5.25a.75.75 0 0 0-.75-.75h-5.25Z"
									clip-rule="evenodd"
								/>
							</svg>
						</span>
					</button>
				{/each}
			{/if}
		</div>
	{/if}
</div>

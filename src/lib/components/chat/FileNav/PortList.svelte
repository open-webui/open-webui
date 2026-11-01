<script lang="ts">
	import { onMount, onDestroy, getContext, createEventDispatcher } from 'svelte';
	import type { ListeningPort } from '$lib/apis/terminal';
	import { getListeningPorts, getPortProxyUrl, getTerminalFeatures } from '$lib/apis/terminal';
	import { watchTerminalPorts } from '$lib/apis/terminal/events';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Icon from './Icon.svelte';

	const i18n = getContext<any>('i18n');
	const dispatch = createEventDispatcher<{ previewPort: number }>();

	export let baseUrl: string;
	export let active = true;
	export let previewBaseUrl: string | null = null;
	export let apiKey: string;
	export let chatId: string | null = null;

	let ports: ListeningPort[] = [];
	let loading = false;
	let mounted = false;
	let context = '';
	let generation = 0;
	let stopWatching: (() => void) | undefined;

	const loadPorts = async () => {
		const current = generation;
		loading = true;
		const next = await getListeningPorts(baseUrl, apiKey, chatId);
		if (current !== generation) return;
		ports = next;
		loading = false;
	};

	const configure = async (key: string, enabled: boolean) => {
		const current = ++generation;
		stopWatching?.();
		stopWatching = undefined;
		if (context !== key) ports = [];
		context = key;
		loading = false;
		if (!enabled || !baseUrl) return;
		const connection = { baseUrl, key: apiKey, selector: '', system: false };
		const features = await getTerminalFeatures(connection, chatId);
		if (current !== generation) return;
		if (features.events === true) {
			loading = true;
			stopWatching = watchTerminalPorts(
				connection,
				chatId,
				(next) => {
					ports = next;
					loading = false;
				},
				() => {
					loading = false;
				}
			);
		} else {
			await loadPorts();
		}
	};

	const previewPort = (port: number) => {
		dispatch('previewPort', port);
	};

	const openPortExternal = (port: number) => {
		const url = getPortProxyUrl(previewBaseUrl ?? baseUrl, port);
		window.open(url, '_blank', 'noopener,noreferrer');
	};

	// Only discover ports while the browser start view is visible.
	$: configure(JSON.stringify([baseUrl, apiKey, chatId]), mounted && active);
	onMount(() => {
		mounted = true;
	});
	onDestroy(() => {
		++generation;
		stopWatching?.();
	});
</script>

<div>
	<div
		class="flex h-7 items-center gap-2 w-full text-xs leading-4 font-normal text-gray-500 dark:text-gray-400"
	>
		<div class="flex h-full flex-1 items-center gap-1.5">
			{$i18n.t('Ports')}
			{#if ports.length > 0}
				<span class="text-[11px] tabular-nums text-gray-400 dark:text-gray-500">
					{ports.length}
				</span>
			{/if}
		</div>
		<span class="flex items-center gap-1">
			<Tooltip content={$i18n.t('Refresh')}>
				<button
					class="flex size-6 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
					on:click|stopPropagation={loadPorts}
					disabled={loading}
					aria-label={$i18n.t('Refresh')}
				>
					<Icon name="refresh" size={11} strokeWidth={1.4} class={loading ? 'animate-spin' : ''} />
				</button>
			</Tooltip>
		</span>
	</div>

	<div class="mt-1 max-h-60 overflow-y-auto scrollbar-hidden">
		{#if ports.length === 0}
			<div class="text-xs leading-5 text-gray-400 dark:text-gray-500 py-2">
				{$i18n.t('No servers detected')}
			</div>
		{:else}
			{#each ports as port}
				<div class="flex h-8 items-center w-full gap-2 text-xs leading-4 group">
					<button
						class="flex min-w-0 flex-1 items-center gap-2 self-stretch"
						on:click={() => previewPort(port.port)}
					>
						<span
							class="w-14 font-mono text-gray-700 dark:text-gray-200 shrink-0 text-left group-hover:text-blue-500 group-focus-within:text-blue-500 transition-colors"
						>
							:{port.port}
						</span>
						<span class="text-gray-500 dark:text-gray-400 truncate flex-1 text-left">
							{port.process ?? ''}
						</span>
					</button>
					<Tooltip content={$i18n.t('Open in new tab')}>
						<button
							class="text-gray-400 dark:text-gray-500 transition shrink-0 flex size-6 items-center justify-center rounded hover:text-gray-600 dark:hover:text-gray-300"
							aria-label={$i18n.t('Open in new tab')}
							on:click={() => openPortExternal(port.port)}
						>
							<Icon name="external-link" size={12} strokeWidth={1.4} />
						</button>
					</Tooltip>
				</div>
			{/each}
		{/if}
	</div>
</div>

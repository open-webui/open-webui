<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import Plus from '$lib/components/icons/Plus.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Connection from './Terminals/Connection.svelte';
	import AddTerminalServerModal from '$lib/components/AddTerminalServerModal.svelte';

	type TerminalServerConfig = {
		url: string;
		key?: string;
		name?: string;
		path?: string;
		enabled: boolean;
		[key: string]: any;
	};

	export let servers: TerminalServerConfig[] = [];
	export let onChange: (servers: TerminalServerConfig[]) => void = () => {};

	let showAddModal = false;

	const addServer = (server: TerminalServerConfig) => {
		servers = [...servers, server];
		onChange(servers);
	};

	const enableServer = (idx: number) => {
		servers = servers.map((s, i) => ({ ...s, enabled: i === idx }));
		onChange(servers);
	};

	const disableServer = (idx: number) => {
		servers = servers.map((s, i) => (i === idx ? { ...s, enabled: false } : s));
		onChange(servers);
	};

	const updateServer = (idx: number, updated: TerminalServerConfig) => {
		servers = servers.map((s, i) => (i === idx ? updated : s));
		onChange(servers);
	};

	const deleteServer = (idx: number) => {
		servers = servers.filter((_, i) => i !== idx);
		onChange(servers);
	};
</script>

<AddTerminalServerModal
	direct
	bind:show={showAddModal}
	onSubmit={(server: TerminalServerConfig) => addServer(server)}
/>

<div>
	<div class="flex justify-between items-start gap-3 mb-3">
		<div class="min-w-0">
			<h3 id="terminal-connections-heading" class="text-xs text-gray-600 dark:text-gray-400">
				{$i18n.t('Open Terminal')}
			</h3>
			<p class="mt-1 text-[0.6875rem] leading-relaxed text-gray-400 dark:text-gray-600">
				{$i18n.t(
					'Connect to Open Terminal instances to browse files and use them as always-on tools. Only one can be active at a time.'
				)}
			</p>
		</div>
		<Tooltip content={$i18n.t('Add Connection')}>
			<button
				class="flex size-7 shrink-0 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-black/5 hover:text-gray-900 dark:text-gray-600 dark:hover:bg-white/5 dark:hover:text-white"
				on:click={() => (showAddModal = true)}
				type="button"
				aria-label={$i18n.t('Add Connection')}
			>
				<Plus />
			</button>
		</Tooltip>
	</div>

	<div class="flex flex-col gap-1.5">
		{#each servers as server, idx}
			<Connection
				bind:connection={server}
				onSubmit={(updated) => updateServer(idx, updated)}
				onDelete={() => deleteServer(idx)}
				onEnable={() => enableServer(idx)}
				onDisable={() => disableServer(idx)}
			/>
		{/each}
	</div>

	{#if servers.length === 0}
		<div class="text-[0.6875rem] leading-relaxed text-gray-400 dark:text-gray-600">
			{$i18n.t('No terminal connections configured.')}
		</div>
	{/if}
	<a
		class="mt-2 inline-block text-[0.6875rem] text-gray-500 underline decoration-gray-300 underline-offset-4 hover:text-gray-700 dark:text-gray-500 dark:decoration-gray-700 dark:hover:text-gray-300"
		href="https://github.com/open-webui/open-terminal"
		target="_blank"
		rel="noopener noreferrer">{$i18n.t('Learn more about Open Terminal')} ↗</a
	>
</div>

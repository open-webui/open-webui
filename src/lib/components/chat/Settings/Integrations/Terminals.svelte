<script lang="ts">
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Plus from '$lib/components/icons/Plus.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Connection from './Terminals/Connection.svelte';
	import Policies from './Terminals/Policies.svelte';
	import Instances from './Terminals/Instances.svelte';
	import AddTerminalServerModal from '$lib/components/AddTerminalServerModal.svelte';
	import { detectTerminalServerType } from '$lib/apis/configs';

	import { v4 as uuidv4 } from 'uuid';

	export let admin = false;
	export let servers = [];
	export let onChange: (servers: typeof servers) => void = () => {};

	let showAddModal = false;
	let activeTab: 'connections' | 'policies' | 'instances' = 'connections';

	// Show policy/instance tabs only if there's at least one orchestrator server
	$: hasOrchestrator = servers.some((s) => s.server_type === 'orchestrator' && s.id);

	// On mount, detect server_type for connections that don't have it set yet.
	// This handles connections created via API or before the server_type field existed.
	const detectServerTypes = async () => {
		let changed = false;
		for (let i = 0; i < servers.length; i++) {
			const s = servers[i];
			if (s.server_type || !s.url) continue;
			try {
				const type = await detectTerminalServerType(localStorage.token, {
					url: s.url,
					key: s.key ?? '',
					auth_type: s.auth_type ?? 'bearer'
				});
				if (type) {
					servers[i] = { ...servers[i], server_type: type };
					changed = true;
				}
			} catch {
				// Server unreachable — leave server_type unset
			}
		}
		if (changed) {
			servers = [...servers]; // trigger reactivity
			onChange(servers);
		}
	};

	onMount(() => {
		detectServerTypes();
	});

	const addServer = (server: (typeof servers)[0]) => {
		servers = [...servers, { ...server, id: server.id ?? uuidv4() }];
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

	const updateServer = (idx: number, updated: (typeof servers)[0]) => {
		servers = servers.map((s, i) => (i === idx ? updated : s));
		onChange(servers);
	};

	const deleteServer = (idx: number) => {
		servers = servers.filter((_, i) => i !== idx);
		onChange(servers);
	};
</script>

<AddTerminalServerModal {admin} bind:show={showAddModal} onSubmit={(server) => addServer(server)} />

<div>
	<div class="flex justify-between items-center mb-1">
		<div class="flex items-center gap-2">
			<div class="font-medium">{$i18n.t('Open Terminal')}</div>
			<span
				class="text-[0.65rem] font-medium uppercase px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400"
				>{$i18n.t('Experimental')}</span
			>
		</div>
		{#if activeTab === 'connections'}
			<Tooltip content={$i18n.t('Add Connection')}>
				<button
					class="px-1"
					on:click={() => (showAddModal = true)}
					type="button"
					aria-label={$i18n.t('Add Connection')}
				>
					<Plus />
				</button>
			</Tooltip>
		{/if}
	</div>

	<!-- Tabs -->
	{#if hasOrchestrator}
		<div class="flex gap-1 mb-3 border-b border-gray-100 dark:border-gray-850">
			<button
				class="px-3 py-1.5 text-xs font-medium transition {activeTab === 'connections'
					? 'border-b-2 border-black dark:border-white text-black dark:text-white'
					: 'text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}"
				type="button"
				on:click={() => (activeTab = 'connections')}
			>
				{$i18n.t('Connections')}
			</button>
			<button
				class="px-3 py-1.5 text-xs font-medium transition {activeTab === 'policies'
					? 'border-b-2 border-black dark:border-white text-black dark:text-white'
					: 'text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}"
				type="button"
				on:click={() => (activeTab = 'policies')}
			>
				{$i18n.t('Policies')}
			</button>
			<button
				class="px-3 py-1.5 text-xs font-medium transition {activeTab === 'instances'
					? 'border-b-2 border-black dark:border-white text-black dark:text-white'
					: 'text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}"
				type="button"
				on:click={() => (activeTab = 'instances')}
			>
				{$i18n.t('Active Terminals')}
			</button>
		</div>
	{/if}

	<!-- Tab content -->
	{#if activeTab === 'connections'}
		<div class="flex flex-col gap-1.5">
			{#each servers as server, idx}
				<Connection
					{admin}
					bind:connection={server}
					onSubmit={(updated) => updateServer(idx, updated)}
					onDelete={() => deleteServer(idx)}
					onEnable={() => enableServer(idx)}
					onDisable={() => disableServer(idx)}
				/>
			{/each}
		</div>

		{#if servers.length === 0}
			<div class="text-xs text-gray-400 dark:text-gray-500">
				{$i18n.t('No terminal connections configured.')}
				<a
					href="https://github.com/open-webui/open-terminal"
					target="_blank"
					rel="noopener noreferrer"
					class="underline hover:text-gray-700 dark:hover:text-gray-200"
				>
					{$i18n.t('Learn more')} ↗
				</a>
			</div>
		{/if}
	{:else if activeTab === 'policies'}
		<Policies {servers} />
	{:else if activeTab === 'instances'}
		<Instances {servers} />
	{/if}
</div>

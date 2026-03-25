<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';

	import type { TerminalInstance } from '$lib/apis/terminal';
	import { listTerminalInstances, teardownTerminalInstance } from '$lib/apis/terminal';

	export let servers: any[] = [];

	let selectedServerId = '';
	let instances: TerminalInstance[] = [];
	let loading = false;
	let refreshInterval: ReturnType<typeof setInterval> | null = null;

	let showTeardownConfirm = false;
	let teardownTarget: TerminalInstance | null = null;

	$: orchestratorServers = servers.filter(
		(s) => s.server_type === 'orchestrator' && s.id
	);

	$: if (orchestratorServers.length > 0 && !selectedServerId) {
		selectedServerId = orchestratorServers[0]?.id ?? '';
	}

	const loadInstances = async () => {
		if (!selectedServerId) return;
		loading = true;
		try {
			instances = await listTerminalInstances(localStorage.token, selectedServerId);
		} catch {
			instances = [];
		} finally {
			loading = false;
		}
	};

	$: if (selectedServerId) {
		loadInstances();
	}

	onMount(() => {
		refreshInterval = setInterval(loadInstances, 30_000);
	});

	onDestroy(() => {
		if (refreshInterval) clearInterval(refreshInterval);
	});

	const handleTeardown = async () => {
		if (!teardownTarget) return;
		const ok = await teardownTerminalInstance(
			localStorage.token,
			selectedServerId,
			teardownTarget.instance_id
		);
		if (ok) {
			toast.success($i18n.t('Terminal terminated'));
			await loadInstances();
		} else {
			toast.error($i18n.t('Failed to terminate terminal'));
		}
		teardownTarget = null;
	};

	const statusColor = (status: string) => {
		switch (status) {
			case 'running':
				return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
			case 'pending':
			case 'provisioning':
				return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
			case 'idle':
				return 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400';
			case 'error':
				return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
			default:
				return 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400';
		}
	};

	const relativeTime = (iso: string) => {
		if (!iso) return '—';
		const diff = Date.now() - new Date(iso).getTime();
		const mins = Math.floor(diff / 60_000);
		if (mins < 1) return 'just now';
		if (mins < 60) return `${mins}m ago`;
		const hrs = Math.floor(mins / 60);
		if (hrs < 24) return `${hrs}h ago`;
		return `${Math.floor(hrs / 24)}d ago`;
	};
</script>

<ConfirmDialog
	bind:show={showTeardownConfirm}
	message={$i18n.t('Are you sure you want to delete this terminal? The user will lose any unsaved work.')}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={handleTeardown}
/>

<div>
	{#if orchestratorServers.length === 0}
		<div class="text-xs text-gray-400 dark:text-gray-500 py-4">
			{$i18n.t('No orchestrator connections configured.')}
		</div>
	{:else}
		<!-- Server selector + refresh -->
		<div class="flex items-center justify-between mb-2 gap-2">
			<select
				class="dark:bg-gray-900 text-sm bg-transparent pr-5 outline-hidden max-w-[200px]"
				bind:value={selectedServerId}
			>
				{#each orchestratorServers as server}
					<option value={server.id}>{server.name || server.id}</option>
				{/each}
			</select>

			<div class="flex items-center gap-2">
				<span class="text-xs text-gray-400 dark:text-gray-500">
					{instances.length} {$i18n.t('active')}
				</span>
				<Tooltip content={$i18n.t('Refresh')}>
					<button
						class="p-1 hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
						type="button"
						on:click={loadInstances}
						aria-label={$i18n.t('Refresh')}
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
							<path fill-rule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z" clip-rule="evenodd" />
						</svg>
					</button>
				</Tooltip>
			</div>
		</div>

		<!-- Instance list -->
		{#if loading && instances.length === 0}
			<div class="text-xs text-gray-400 dark:text-gray-500 py-4 text-center">
				{$i18n.t('Loading...')}
			</div>
		{:else if instances.length === 0}
			<div class="text-xs text-gray-400 dark:text-gray-500 py-4 text-center">
				{$i18n.t('No active terminal instances.')}
			</div>
		{:else}
			<div class="overflow-x-auto">
				<table class="w-full text-sm">
					<thead>
						<tr class="text-xs text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-gray-850">
							<th class="text-left py-1.5 pr-3 font-medium">{$i18n.t('User')}</th>
							<th class="text-left py-1.5 pr-3 font-medium">{$i18n.t('Policy')}</th>
							<th class="text-left py-1.5 pr-3 font-medium">{$i18n.t('Status')}</th>
							<th class="text-left py-1.5 pr-3 font-medium">{$i18n.t('Last Activity')}</th>
							<th class="text-left py-1.5 pr-3 font-medium">{$i18n.t('Created')}</th>
							<th class="text-right py-1.5 font-medium"></th>
						</tr>
					</thead>
					<tbody>
						{#each instances as inst (inst.instance_id)}
							<tr class="border-b border-gray-50 dark:border-gray-900 hover:bg-gray-50 dark:hover:bg-gray-900 transition">
								<td class="py-1.5 pr-3">
								<span class="text-xs truncate max-w-[150px] inline-block" title={inst.user_id}>
									{inst.user_name || inst.user_id.slice(0, 8) + '…'}
									</span>
								</td>
								<td class="py-1.5 pr-3">
									<span class="font-mono text-xs">{inst.policy_id}</span>
								</td>
								<td class="py-1.5 pr-3">
									<span class="text-[0.6rem] font-medium uppercase px-1.5 py-0.5 rounded-full {statusColor(inst.status)}">
										{inst.status}
									</span>
								</td>
								<td class="py-1.5 pr-3 text-xs text-gray-400 dark:text-gray-500">
									{relativeTime(inst.last_activity)}
								</td>
								<td class="py-1.5 pr-3 text-xs text-gray-400 dark:text-gray-500">
									{relativeTime(inst.created_at)}
								</td>
								<td class="py-1.5 text-right">
								<Tooltip content={$i18n.t('Delete')}>
									<button
										class="self-center p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
										type="button"
										on:click={() => {
											teardownTarget = inst;
											showTeardownConfirm = true;
										}}
										aria-label={$i18n.t('Delete')}
									>
										<GarbageBin className="w-3.5 h-3.5" />
										</button>
									</Tooltip>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{/if}
</div>

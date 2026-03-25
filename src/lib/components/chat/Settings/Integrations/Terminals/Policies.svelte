<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Plus from '$lib/components/icons/Plus.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import PolicyEditor from './PolicyEditor.svelte';

	import type { PolicyResponse } from '$lib/apis/terminal';
	import { listPolicies, deletePolicy } from '$lib/apis/terminal';

	export let servers: any[] = [];

	let selectedServerId = '';
	let policies: PolicyResponse[] = [];
	let loading = false;
	let searchQuery = '';

	let showEditor = false;
	let editingPolicy: PolicyResponse | null = null;

	let showDeleteConfirm = false;
	let deletingPolicyId = '';

	// Filter to orchestrator-type servers only
	$: orchestratorServers = servers.filter(
		(s) => s.server_type === 'orchestrator' && s.id
	);

	$: if (orchestratorServers.length > 0 && !selectedServerId) {
		selectedServerId = orchestratorServers[0]?.id ?? '';
	}

	$: filteredPolicies = searchQuery
		? policies.filter(
				(p) =>
					p.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
					(p.data?.image ?? '').toLowerCase().includes(searchQuery.toLowerCase())
			)
		: policies;

	const loadPolicies = async () => {
		if (!selectedServerId) return;
		loading = true;
		try {
			policies = await listPolicies(localStorage.token, selectedServerId);
		} catch {
			toast.error($i18n.t('Failed to load policies'));
			policies = [];
		} finally {
			loading = false;
		}
	};

	$: if (selectedServerId) {
		loadPolicies();
	}

	const handleDelete = async () => {
		if (!deletingPolicyId) return;
		const ok = await deletePolicy(localStorage.token, selectedServerId, deletingPolicyId);
		if (ok) {
			toast.success($i18n.t('Policy deleted'));
			await loadPolicies();
		} else {
			toast.error($i18n.t('Failed to delete policy'));
		}
		deletingPolicyId = '';
	};

	const openCreate = () => {
		editingPolicy = null;
		showEditor = true;
	};

	const openEdit = (p: PolicyResponse) => {
		editingPolicy = p;
		showEditor = true;
	};

	const openClone = (p: PolicyResponse) => {
		editingPolicy = { id: `${p.id}-copy`, data: { ...p.data } };
		showEditor = true;
	};

	const statusBadge = (p: PolicyResponse) => {
		const d = p.data ?? {};
		const parts: string[] = [];
		if (d.image) parts.push(d.image.split('/').pop()?.split(':')[0] ?? '');
		if (d.cpu_limit) parts.push(`${d.cpu_limit} CPU`);
		if (d.memory_limit) parts.push(d.memory_limit);
		if (d.storage) parts.push(`💾 ${d.storage}`);
		else parts.push('ephemeral');
		return parts.filter(Boolean).join(' · ');
	};
</script>

<PolicyEditor
	bind:show={showEditor}
	edit={editingPolicy !== null && !editingPolicy.id.endsWith('-copy')}
	serverId={selectedServerId}
	policy={editingPolicy}
	onSave={loadPolicies}
/>

<ConfirmDialog
	bind:show={showDeleteConfirm}
	message={$i18n.t('Are you sure you want to delete this policy? This action cannot be undone.')}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={handleDelete}
/>

<div>
	{#if orchestratorServers.length === 0}
		<div class="text-xs text-gray-400 dark:text-gray-500 py-4">
			{$i18n.t('No orchestrator connections configured. Add a terminal server connection with an orchestrator type to manage policies.')}
		</div>
	{:else}
		<!-- Server selector + actions -->
		<div class="flex items-center justify-between mb-2 gap-2">
			<div class="flex items-center gap-2 flex-1 min-w-0">
				<select
					class="dark:bg-gray-900 text-sm bg-transparent pr-5 outline-hidden max-w-[200px]"
					bind:value={selectedServerId}
				>
					{#each orchestratorServers as server}
						<option value={server.id}>{server.name || server.id}</option>
					{/each}
				</select>

				<input
					type="text"
					class="flex-1 text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700 min-w-0"
					placeholder={$i18n.t('Search policies...')}
					bind:value={searchQuery}
				/>
			</div>

			<div class="flex items-center gap-1">
				<Tooltip content={$i18n.t('Refresh')}>
					<button
						class="p-1 hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
						type="button"
						on:click={loadPolicies}
						aria-label={$i18n.t('Refresh')}
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
							<path fill-rule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z" clip-rule="evenodd" />
						</svg>
					</button>
				</Tooltip>
				<Tooltip content={$i18n.t('Create Policy')}>
					<button
						class="p-1 hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
						type="button"
						on:click={openCreate}
						aria-label={$i18n.t('Create Policy')}
					>
						<Plus />
					</button>
				</Tooltip>
			</div>
		</div>

		<!-- Policy list -->
		{#if loading}
			<div class="text-xs text-gray-400 dark:text-gray-500 py-4 text-center">
				{$i18n.t('Loading...')}
			</div>
		{:else if filteredPolicies.length === 0}
			<div class="text-xs text-gray-400 dark:text-gray-500 py-4 text-center">
				{searchQuery ? $i18n.t('No policies match your search.') : $i18n.t('No policies configured yet.')}
			</div>
		{:else}
			<div class="flex flex-col gap-1.5">
				{#each filteredPolicies as policy (policy.id)}
					<div
						class="flex items-center justify-between rounded-lg border border-gray-100 dark:border-gray-850 px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-900 transition group"
					>
						<button
							class="flex-1 min-w-0 text-left"
							type="button"
							on:click={() => openEdit(policy)}
						>
							<div class="flex items-center gap-2">
								<span class="text-sm font-medium font-mono truncate">{policy.id}</span>
								{#if policy.data?.idle_timeout_minutes}
									<span class="text-[0.6rem] px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 shrink-0">
										{policy.data.idle_timeout_minutes}m idle
									</span>
								{/if}
							</div>
							<div class="text-xs text-gray-400 dark:text-gray-500 truncate mt-0.5">
								{statusBadge(policy)}
							</div>
						</button>

						<div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition shrink-0">
							<Tooltip content={$i18n.t('Clone')}>
								<button
									class="p-1 hover:bg-gray-200 dark:hover:bg-gray-800 rounded transition"
									type="button"
									on:click={() => openClone(policy)}
									aria-label={$i18n.t('Clone')}
								>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5">
										<path d="M7 3.5A1.5 1.5 0 018.5 2h3.879a1.5 1.5 0 011.06.44l3.122 3.12A1.5 1.5 0 0117 6.622V12.5a1.5 1.5 0 01-1.5 1.5h-1v-3.379a3 3 0 00-.879-2.121L10.5 5.379A3 3 0 008.379 4.5H7v-1z" />
										<path d="M4.5 6A1.5 1.5 0 003 7.5v9A1.5 1.5 0 004.5 18h7a1.5 1.5 0 001.5-1.5v-5.879a1.5 1.5 0 00-.44-1.06L9.44 6.439A1.5 1.5 0 008.378 6H4.5z" />
									</svg>
								</button>
							</Tooltip>
							<Tooltip content={$i18n.t('Delete')}>
								<button
									class="self-center p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
									type="button"
									on:click={() => {
										deletingPolicyId = policy.id;
										showDeleteConfirm = true;
									}}
									aria-label={$i18n.t('Delete')}
								>
									<GarbageBin className="w-3.5 h-3.5" />
								</button>
							</Tooltip>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>

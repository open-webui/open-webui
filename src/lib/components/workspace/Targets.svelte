<script lang="ts">
	import { getContext } from 'svelte';
	import { WEBUI_NAME } from '$lib/stores';
	import Search from '$lib/components/icons/Search.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import AddTargetModal from './Targets/AddTargetModal.svelte';
	import ScanProgressPanel from './Targets/ScanProgressPanel.svelte';
	import TargetCard from './Targets/TargetCard.svelte';
	import type { TargetStatus, TargetType } from './Targets/types';
	import {
		activeTargetId,
		addTarget,
		deleteTarget,
		queueTargetScan,
		setActiveTarget,
		targets,
		toggleTargetStatus
	} from '$lib/stores/targets';

	const i18n = getContext<any>('i18n');

	let showAddTargetModal = false;
	let query = '';
	let typeFilter: 'all' | TargetType = 'all';
	let statusFilter: 'all' | TargetStatus = 'all';

	const targetTypes: Array<'all' | TargetType> = ['all', 'Domain', 'IP', 'URL', 'CIDR', 'Host'];
	const statusOptions: Array<'all' | TargetStatus> = [
		'all',
		'Active',
		'Pending',
		'Paused',
		'Complete',
		'Error'
	];

	$: filteredTargets = $targets.filter((target) => {
		const lowerQuery = query.trim().toLowerCase();
		const matchesQuery =
			lowerQuery === '' ||
			target.name.toLowerCase().includes(lowerQuery) ||
			target.value.toLowerCase().includes(lowerQuery) ||
			target.description.toLowerCase().includes(lowerQuery);

		const matchesType = typeFilter === 'all' || target.type === typeFilter;
		const matchesStatus = statusFilter === 'all' || target.status === statusFilter;

		return matchesQuery && matchesType && matchesStatus;
	});
</script>

<svelte:head>
	<title>{$i18n.t('Targets')} • {$WEBUI_NAME}</title>
</svelte:head>

<AddTargetModal
	bind:show={showAddTargetModal}
	on:submit={(event) => {
		addTarget(event.detail);
	}}
/>

<div class="flex flex-col gap-1 px-1 mt-1.5 mb-3">
	<div class="flex justify-between items-center gap-3 flex-wrap">
		<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
			<div>{$i18n.t('Targets')}</div>
			<div class="text-lg font-medium text-gray-500 dark:text-gray-500">
				{filteredTargets.length}
			</div>
		</div>

		<button
			class="px-2.5 py-1.5 rounded-xl bg-sky-600 text-white hover:bg-sky-500 dark:bg-sky-500 dark:hover:bg-sky-400 transition font-medium text-sm flex items-center shadow-sm"
			on:click={() => {
				showAddTargetModal = true;
			}}
		>
			<Plus className="size-3" strokeWidth="2.5" />
			<div class="hidden md:block md:ml-1 text-xs">{$i18n.t('Add Target')}</div>
		</button>
	</div>

	<div class="text-sm text-gray-600 dark:text-gray-300 px-0.5 max-w-3xl">
		{$i18n.t(
			'Manage scan assets for VenomX. This interface uses local mock data until backend scan orchestration is available.'
		)}
	</div>
</div>

<div
	class="py-2 rounded-3xl border border-sky-100/80 dark:border-sky-900/50 bg-white/72 dark:bg-slate-950/56 backdrop-blur-md shadow-sm"
>
	<div class="px-3.5 pt-1 pb-2">
		<ScanProgressPanel targetId={$activeTargetId} title="Scan Progress" />
	</div>

	<div class="px-3.5 flex flex-col gap-2 pb-2">
		<div
			class="flex items-center w-full space-x-2 py-0.5 rounded-xl border border-sky-100/80 dark:border-sky-900/40 bg-white/70 dark:bg-slate-900/45 px-1.5"
		>
			<div class="self-center ml-1 mr-3"><Search className="size-3.5" /></div>
			<input
				class="w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent placeholder:text-gray-500 dark:placeholder:text-gray-400"
				bind:value={query}
				placeholder={$i18n.t('Search targets by name, value, or description')}
				aria-label={$i18n.t('Search Targets')}
			/>
			{#if query}
				<button
					class="p-0.5 rounded-full hover:bg-sky-100/80 dark:hover:bg-sky-900/50 transition"
					aria-label={$i18n.t('Clear search')}
					on:click={() => {
						query = '';
					}}
				>
					<XMark className="size-3" strokeWidth="2" />
				</button>
			{/if}
		</div>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-2 px-0.5">
			<div>
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Type')}</div>
				<select
					class="w-full text-sm bg-white/70 dark:bg-slate-900/45 border border-sky-100/80 dark:border-sky-900/40 outline-hidden rounded-lg px-2 py-1"
					bind:value={typeFilter}
				>
					{#each targetTypes as option}
						<option value={option}>{option === 'all' ? $i18n.t('All Types') : option}</option>
					{/each}
				</select>
			</div>
			<div>
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Status')}</div>
				<select
					class="w-full text-sm bg-white/70 dark:bg-slate-900/45 border border-sky-100/80 dark:border-sky-900/40 outline-hidden rounded-lg px-2 py-1"
					bind:value={statusFilter}
				>
					{#each statusOptions as option}
						<option value={option}>{option === 'all' ? $i18n.t('All Statuses') : option}</option>
					{/each}
				</select>
			</div>
		</div>
	</div>

	{#if filteredTargets.length > 0}
		<div class="my-2 px-3 grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3 gap-2">
			{#each filteredTargets as target (target.id)}
				<TargetCard
					{target}
					on:run={(event) => {
						setActiveTarget(event.detail);
						queueTargetScan(event.detail);
					}}
					on:toggle={(event) => {
						toggleTargetStatus(event.detail);
					}}
					on:delete={(event) => {
						deleteTarget(event.detail);
					}}
				/>
			{/each}
		</div>
	{:else}
		<div class="w-full h-full flex flex-col justify-center items-center my-16 mb-24">
			<div class="max-w-md text-center">
				<div class="text-3xl mb-3">🎯</div>
				<div class="text-lg font-medium mb-1">{$i18n.t('No targets found')}</div>
				<div class="text-gray-500 text-center text-xs">
					{$i18n.t('Try adjusting your search or filter, or add a new target asset.')}
				</div>
			</div>
		</div>
	{/if}
</div>

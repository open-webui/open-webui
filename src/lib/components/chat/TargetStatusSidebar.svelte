<script lang="ts">
	import { getContext } from 'svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import TargetStatusSidebarItem from './TargetStatusSidebarItem.svelte';
	import ScanProgressPanel from '$lib/components/workspace/Targets/ScanProgressPanel.svelte';
	import {
		activeQueueTargetId,
		activeScanCount,
		activeTargetId,
		isScanQueueRunning,
		queueTargetScan,
		scanQueue,
		setActiveTarget,
		startScanQueue,
		stopScanQueue,
		targets,
		toggleTargetStatus
	} from '$lib/stores/targets';

	const i18n = getContext<any>('i18n');
	export let onClose: () => void = () => {};

	$: queuedTargets = $scanQueue
		.map((targetId, index) => ({
			position: index + 1,
			target: $targets.find((target) => target.id === targetId)
		}))
		.filter((entry) => Boolean(entry.target));
</script>

<aside
	class="h-full w-72 max-w-[18rem] rounded-2xl border border-sky-100/80 dark:border-sky-900/55 bg-white/70 dark:bg-slate-950/55 backdrop-blur-md shadow-sm p-2.5 flex flex-col"
	aria-label={$i18n.t('Target Status Sidebar')}
>
	<div class="flex items-center justify-between gap-2 px-0.5 pb-2 border-b border-sky-100/70 dark:border-sky-900/45">
		<div>
			<div class="text-sm font-semibold">{$i18n.t('Targets')}</div>
			<div class="text-[11px] text-gray-500 dark:text-gray-400">
				{$activeScanCount} {$i18n.t('active')} • {$scanQueue.length} {$i18n.t('queued')} • {$targets.length} {$i18n.t('total')}
			</div>
		</div>
		<button
			class="p-1 rounded-lg hover:bg-sky-100/80 dark:hover:bg-sky-900/40 transition"
			aria-label={$i18n.t('Close Targets')}
			on:click={() => {
				onClose();
			}}
		>
			<XMark className="size-4" strokeWidth="2" />
		</button>
	</div>

	{#if !$isScanQueueRunning}
		<div class="mt-2 min-h-0 overflow-y-auto scrollbar-hidden pr-0.5 space-y-1.5">
			{#each $targets as target (target.id)}
				<TargetStatusSidebarItem
					{target}
					active={target.id === $activeTargetId}
					on:select={(event) => {
						setActiveTarget(event.detail);
					}}
					on:queue={(event) => {
						setActiveTarget(event.detail);
						queueTargetScan(event.detail);
					}}
					on:toggle={(event) => {
						toggleTargetStatus(event.detail);
					}}
				/>
			{/each}
		</div>
	{:else}
		<div class="mt-2 text-[11px] rounded-xl border border-sky-100/80 dark:border-sky-900/45 bg-sky-50/70 dark:bg-sky-900/20 px-2.5 py-2 text-gray-700 dark:text-gray-200">
			{$i18n.t('Targets list collapsed while queue is running.')}
		</div>
	{/if}

	<div class="mt-2 rounded-xl border border-sky-100/80 dark:border-sky-900/45 bg-white/60 dark:bg-slate-900/40 p-2">
		<div class="text-xs font-medium">{$i18n.t('Scan Queue')}</div>
		<div class="mt-1.5 space-y-1.5 max-h-28 overflow-y-auto scrollbar-hidden pr-0.5">
			{#if queuedTargets.length > 0}
				{#each queuedTargets as entry}
					<div class="flex items-center justify-between gap-2 rounded-lg border border-sky-100/70 dark:border-sky-900/40 bg-white/65 dark:bg-slate-950/35 px-2 py-1.5 text-[11px]">
						<div class="min-w-0 line-clamp-1">
							<span class="font-medium text-sky-700 dark:text-sky-300 mr-1">#{entry.position}</span>
							{entry.target?.name}
						</div>
						{#if entry.target?.id === $activeQueueTargetId}
							<div class="px-1.5 py-0.5 rounded-full bg-emerald-100/80 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 font-medium">
								{$i18n.t('Running')}
							</div>
						{/if}
					</div>
				{/each}
			{:else}
				<div class="text-[11px] text-gray-500 dark:text-gray-400">{$i18n.t('No targets queued yet.')}</div>
			{/if}
		</div>
	</div>

	<div class="mt-2 flex-1 min-h-0">
		<ScanProgressPanel targetId={$activeTargetId} title="Scan Progress" />
	</div>

	<div class="pt-2 mt-2 border-t border-sky-100/70 dark:border-sky-900/45">
		{#if !$isScanQueueRunning}
			<button
				class="w-full text-center block text-xs px-2.5 py-1.5 rounded-xl bg-sky-600 text-white hover:bg-sky-500 dark:bg-sky-500 dark:hover:bg-sky-400 transition disabled:opacity-50 disabled:cursor-not-allowed mb-1.5"
				disabled={$scanQueue.length === 0}
				on:click={() => {
					startScanQueue();
				}}
			>
				{$i18n.t('Start Queue')}
			</button>
		{:else}
			<button
				class="w-full text-center block text-xs px-2.5 py-1.5 rounded-xl bg-amber-100/90 text-amber-800 hover:bg-amber-200/90 dark:bg-amber-900/40 dark:text-amber-300 dark:hover:bg-amber-900/55 transition mb-1.5"
				on:click={() => {
					stopScanQueue();
				}}
			>
				{$i18n.t('Stop Queue')}
			</button>
		{/if}

		<a
			href="/workspace/targets"
			class="w-full text-center block text-xs px-2.5 py-1.5 rounded-xl bg-slate-100/90 hover:bg-slate-200/90 dark:bg-slate-800/80 dark:hover:bg-slate-700/80 transition"
		>
			{$i18n.t('Manage Targets')}
		</a>
	</div>
</aside>

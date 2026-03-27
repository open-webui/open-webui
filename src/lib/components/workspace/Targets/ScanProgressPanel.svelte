<script lang="ts">
	import { getContext, onDestroy } from 'svelte';

	import { scanSessions, type ScanStageStatus } from '$lib/stores/scanSessions';
	import { activeTarget } from '$lib/stores/targets';

	export let targetId: string | null = null;
	export let title = 'Scan Progress';

	const i18n = getContext<any>('i18n');

	let nowTick = Date.now();
	const timerId = setInterval(() => {
		nowTick = Date.now();
	}, 1000);

	onDestroy(() => {
		clearInterval(timerId);
	});

	$: activeSession = targetId ? $scanSessions[targetId] ?? null : null;
	$: selectedTargetName =
		activeSession?.targetName ??
		($activeTarget && targetId && $activeTarget.id === targetId ? $activeTarget.name : null);

	$: stageLabel =
		activeSession?.stages.find((stage) => stage.id === activeSession.currentStageId)?.label ??
		activeSession?.currentStageId ??
		'-';

	$: elapsedMs = activeSession
		? (activeSession.endedAt ?? nowTick) - activeSession.startedAt
		: 0;

	$: recentActivity = activeSession?.activity
		? [...activeSession.activity].reverse().slice(0, 6)
		: [];

	const statusBadgeClass = (status: ScanStageStatus) => {
		if (status === 'complete') {
			return 'text-emerald-700 dark:text-emerald-300 bg-emerald-100/80 dark:bg-emerald-900/45';
		}

		if (status === 'in_progress') {
			return 'text-sky-700 dark:text-sky-300 bg-sky-100/80 dark:bg-sky-900/45';
		}

		if (status === 'error') {
			return 'text-rose-700 dark:text-rose-300 bg-rose-100/80 dark:bg-rose-900/45';
		}

		return 'text-slate-700 dark:text-slate-300 bg-slate-100/80 dark:bg-slate-800/80';
	};

	const lifecycleLabel = (value: string) => {
		if (value === 'running') {
			return 'Running';
		}
		if (value === 'paused') {
			return 'Paused';
		}
		if (value === 'complete') {
			return 'Complete';
		}
		if (value === 'error') {
			return 'Error';
		}
		return 'Queued';
	};

	const formatElapsed = (milliseconds: number) => {
		const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
		const hours = Math.floor(totalSeconds / 3600);
		const minutes = Math.floor((totalSeconds % 3600) / 60);
		const seconds = totalSeconds % 60;
		const pad = (value: number) => value.toString().padStart(2, '0');

		if (hours > 0) {
			return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
		}

		return `${pad(minutes)}:${pad(seconds)}`;
	};

	const formatTime = (timestamp: number) => {
		const date = new Date(timestamp);
		const pad = (value: number) => value.toString().padStart(2, '0');
		return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
	};
</script>

<div class="rounded-2xl border border-sky-100/80 dark:border-sky-900/55 bg-white/70 dark:bg-slate-950/55 backdrop-blur-md shadow-sm p-3">
	<div class="flex items-start justify-between gap-2">
		<div>
			<div class="text-sm font-semibold">{$i18n.t(title)}</div>
			<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
				{selectedTargetName ?? $i18n.t('Select a target to view scan progress')}
			</div>
		</div>
		{#if activeSession}
			<div class="text-[10px] px-2 py-1 rounded-full font-medium {statusBadgeClass(activeSession.lifecycle === 'queued' ? 'pending' : activeSession.lifecycle === 'running' ? 'in_progress' : activeSession.lifecycle === 'paused' ? 'pending' : activeSession.lifecycle === 'complete' ? 'complete' : 'error')}">
				{lifecycleLabel(activeSession.lifecycle)}
			</div>
		{/if}
	</div>

	{#if activeSession}
		<div class="mt-3 space-y-3">
			<div>
				<div class="flex items-center justify-between text-[11px] text-gray-600 dark:text-gray-300 mb-1">
					<span>{$i18n.t('Overall Progress')}</span>
					<span>{activeSession.progress}%</span>
				</div>
				<div class="h-2 rounded-full bg-sky-100/90 dark:bg-sky-900/35 overflow-hidden">
					<div
						class="h-full bg-sky-600 dark:bg-sky-500 transition-all duration-500"
						style={`width: ${Math.max(0, Math.min(100, activeSession.progress))}%`}
					></div>
				</div>
			</div>

			<div class="grid grid-cols-2 gap-2 text-xs">
				<div class="rounded-xl border border-sky-100/80 dark:border-sky-900/50 bg-white/60 dark:bg-slate-900/45 p-2">
					<div class="text-gray-500 dark:text-gray-400">{$i18n.t('Current Stage')}</div>
					<div class="font-medium mt-0.5 line-clamp-1">{stageLabel}</div>
				</div>
				<div class="rounded-xl border border-sky-100/80 dark:border-sky-900/50 bg-white/60 dark:bg-slate-900/45 p-2">
					<div class="text-gray-500 dark:text-gray-400">{$i18n.t('Elapsed')}</div>
					<div class="font-medium mt-0.5">{formatElapsed(elapsedMs)}</div>
				</div>
			</div>

			<div>
				<div class="text-xs font-medium mb-1.5">{$i18n.t('Stages')}</div>
				<div class="space-y-1.5 max-h-40 overflow-y-auto scrollbar-hidden pr-1">
					{#each activeSession.stages as stage}
						<div class="flex items-center justify-between text-[11px] rounded-lg border border-sky-100/70 dark:border-sky-900/40 px-2 py-1.5 bg-white/55 dark:bg-slate-900/35">
							<div class="line-clamp-1">{stage.label}</div>
							<div class="px-1.5 py-0.5 rounded-full font-medium {statusBadgeClass(stage.status)}">
								{stage.status.replace('_', ' ')}
							</div>
						</div>
					{/each}
				</div>
			</div>

			<div>
				<div class="text-xs font-medium mb-1.5">{$i18n.t('Recent Activity')}</div>
				<div class="space-y-1.5 max-h-36 overflow-y-auto scrollbar-hidden pr-1">
					{#if recentActivity.length > 0}
						{#each recentActivity as item}
							<div class="text-[11px] rounded-lg border border-sky-100/70 dark:border-sky-900/40 px-2 py-1.5 bg-white/55 dark:bg-slate-900/35">
								<div class="text-gray-500 dark:text-gray-400">{formatTime(item.timestamp)}</div>
								<div class="mt-0.5">{item.message}</div>
							</div>
						{/each}
					{:else}
						<div class="text-[11px] text-gray-500 dark:text-gray-400">{$i18n.t('No activity recorded yet.')}</div>
					{/if}
				</div>
			</div>
		</div>
	{:else}
		<div class="mt-3 text-xs text-gray-500 dark:text-gray-400 rounded-xl border border-sky-100/70 dark:border-sky-900/45 bg-white/60 dark:bg-slate-900/35 p-2.5">
			{$i18n.t('Queue a scan from Targets or the sidebar to start a mock scan lifecycle.')}
		</div>
	{/if}
</div>

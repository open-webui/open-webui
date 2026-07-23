<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';

	import {
		getUserUsage,
		type UserUsageHeatmapEntry,
		type UserUsageResponse
	} from '$lib/apis/users';
	import { models } from '$lib/stores';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { formatNumber } from '$lib/utils';

	import UserSettingSection from './UserSettingSection.svelte';
	import UserSettingRow from './UserSettingRow.svelte';

	const i18n: Writable<any> = getContext('i18n');

	type HeatmapMode = 'daily' | 'weekly' | 'cumulative';
	type HeatmapCell = UserUsageHeatmapEntry | null;
	type MonthLabel = { label: string; column: number; span: number };

	let usage: UserUsageResponse | null = null;
	let loading = true;
	let heatmapMode: HeatmapMode = 'daily';
	let heatmapContainerWidth = 0;

	const HEATMAP_MIN_CELL_PX = 8;
	const HEATMAP_MAX_CELL_PX = 10;
	const HEATMAP_GAP_PX = 4;
	const MIN_HEATMAP_COLUMNS = 26;
	const DEFAULT_HEATMAP_COLUMNS = 26;
	const MIN_MONTH_LABEL_GAP = 6;

	$: modelNames = new Map($models.map((model) => [model.id, model.name || model.id]));
	$: dailyHeatmap = usage?.heatmap ?? [];
	$: weeklyHeatmap = new Map((usage?.weekly_heatmap ?? []).map((entry) => [entry.date, entry]));
	$: cumulativeHeatmap = new Map(
		(usage?.cumulative_heatmap ?? []).map((entry) => [entry.date, entry])
	);
	$: heatmapData = buildDisplayHeatmap(dailyHeatmap, heatmapMode, weeklyHeatmap, cumulativeHeatmap);
	$: totalHeatmapColumns = Math.max(Math.ceil(heatmapData.length / 7), 1);
	$: maxHeatmapColumns = heatmapContainerWidth
		? Math.max(
				Math.min(totalHeatmapColumns, MIN_HEATMAP_COLUMNS),
				Math.floor(
					(heatmapContainerWidth + HEATMAP_GAP_PX) / (HEATMAP_MIN_CELL_PX + HEATMAP_GAP_PX)
				)
			)
		: Math.min(totalHeatmapColumns, DEFAULT_HEATMAP_COLUMNS);
	$: visibleHeatmapColumns = Math.min(totalHeatmapColumns, maxHeatmapColumns);
	$: heatmapCells = buildHeatmapCells(heatmapData, visibleHeatmapColumns);
	$: heatmapColumns = Math.max(Math.ceil(heatmapCells.length / 7), 1);
	$: heatmapGridWidth = `${heatmapColumns * HEATMAP_MAX_CELL_PX + (heatmapColumns - 1) * HEATMAP_GAP_PX}px`;
	$: monthLabels = buildMonthLabels(heatmapCells, heatmapColumns);
	$: hasUsage = (usage?.totals.messages ?? 0) > 0 || (usage?.totals.lifetime_tokens ?? 0) > 0;

	const palettes = [
		[
			'bg-gray-100 dark:bg-gray-800',
			'bg-green-100 dark:bg-green-900/40',
			'bg-green-300 dark:bg-green-700/60',
			'bg-green-500 dark:bg-green-600/80',
			'bg-green-700 dark:bg-green-500'
		],
		[
			'bg-gray-100 dark:bg-gray-800',
			'bg-blue-100 dark:bg-blue-900/40',
			'bg-blue-300 dark:bg-blue-700/60',
			'bg-blue-500 dark:bg-blue-600/80',
			'bg-blue-700 dark:bg-blue-500'
		],
		[
			'bg-gray-100 dark:bg-gray-800',
			'bg-purple-100 dark:bg-purple-900/40',
			'bg-purple-300 dark:bg-purple-700/60',
			'bg-purple-500 dark:bg-purple-600/80',
			'bg-purple-700 dark:bg-purple-500'
		],
		[
			'bg-gray-100 dark:bg-gray-800',
			'bg-orange-100 dark:bg-orange-900/40',
			'bg-orange-300 dark:bg-orange-700/60',
			'bg-orange-500 dark:bg-orange-600/80',
			'bg-orange-700 dark:bg-orange-500'
		],
		[
			'bg-gray-100 dark:bg-gray-800',
			'bg-rose-100 dark:bg-rose-900/40',
			'bg-rose-300 dark:bg-rose-700/60',
			'bg-rose-500 dark:bg-rose-600/80',
			'bg-rose-700 dark:bg-rose-500'
		],
		[
			'bg-gray-100 dark:bg-gray-800',
			'bg-yellow-100 dark:bg-yellow-900/40',
			'bg-yellow-300 dark:bg-yellow-700/60',
			'bg-yellow-500 dark:bg-yellow-600/80',
			'bg-yellow-700 dark:bg-yellow-500'
		],
		[
			'bg-gray-100 dark:bg-gray-800',
			'bg-cyan-100 dark:bg-cyan-900/40',
			'bg-cyan-300 dark:bg-cyan-700/60',
			'bg-cyan-500 dark:bg-cyan-600/80',
			'bg-cyan-700 dark:bg-cyan-500'
		],
		[
			'bg-gray-100 dark:bg-gray-800',
			'bg-red-100 dark:bg-red-900/40',
			'bg-red-300 dark:bg-red-700/60',
			'bg-red-500 dark:bg-red-600/80',
			'bg-red-700 dark:bg-red-500'
		],
		[
			'bg-gray-100 dark:bg-gray-800',
			'bg-neutral-200 dark:bg-neutral-800',
			'bg-neutral-400 dark:bg-neutral-600',
			'bg-neutral-600 dark:bg-neutral-400',
			'bg-neutral-800 dark:bg-neutral-200'
		]
	];

	const heatmapModes: Array<{ value: HeatmapMode; label: string }> = [
		{ value: 'daily', label: 'Daily' },
		{ value: 'weekly', label: 'Weekly' },
		{ value: 'cumulative', label: 'Cumulative' }
	];

	const loadUsage = async () => {
		loading = true;
		try {
			usage = await getUserUsage(localStorage.token);
		} catch (error) {
			console.error('Usage load failed:', error);
			usage = null;
		}
		loading = false;
	};

	const weekStart = (dateString: string) => {
		const date = new Date(`${dateString}T00:00:00`);
		const daysSinceMonday = (date.getDay() + 6) % 7;
		date.setDate(date.getDate() - daysSinceMonday);
		const month = `${date.getMonth() + 1}`.padStart(2, '0');
		const day = `${date.getDate()}`.padStart(2, '0');
		return `${date.getFullYear()}-${month}-${day}`;
	};

	const buildDisplayHeatmap = (
		data: UserUsageHeatmapEntry[],
		mode: HeatmapMode,
		weekly: Map<string, UserUsageHeatmapEntry>,
		cumulative: Map<string, UserUsageHeatmapEntry>
	) => {
		if (mode === 'daily') {
			return data;
		}

		return data.map((day) => {
			const aggregate =
				mode === 'weekly' ? weekly.get(weekStart(day.date)) : cumulative.get(day.date);
			return aggregate ? { ...aggregate, date: day.date } : day;
		});
	};

	const buildHeatmapCells = (data: UserUsageHeatmapEntry[], visibleColumns: number) => {
		if (data.length === 0) {
			return [];
		}

		const cells = data.slice(-Math.max(7, visibleColumns * 7));
		const trailingBlanks = Array.from({ length: (7 - (cells.length % 7)) % 7 }, () => null);
		return [...cells, ...trailingBlanks];
	};

	const buildMonthLabels = (cells: HeatmapCell[], columns: number): MonthLabel[] => {
		const labels: MonthLabel[] = [];
		let currentMonth = '';
		let lastLabelColumn = -MIN_MONTH_LABEL_GAP;

		cells.forEach((entry, index) => {
			if (!entry) {
				return;
			}

			const month = entry.date.slice(0, 7);
			if (month === currentMonth) {
				return;
			}

			const column = Math.floor(index / 7) + 1;
			if (column - lastLabelColumn < MIN_MONTH_LABEL_GAP) {
				currentMonth = month;
				return;
			}

			labels.push({
				label: new Date(`${entry.date}T00:00:00`).toLocaleString(undefined, { month: 'short' }),
				column,
				span: Math.min(MIN_MONTH_LABEL_GAP, columns - column + 1)
			});
			lastLabelColumn = column;
			currentMonth = month;
		});

		return labels;
	};

	const topItem = (entry: UserUsageHeatmapEntry) => {
		const models = Object.entries(entry.models ?? {}).sort((a, b) => b[1] - a[1]);
		return models[0]?.[0] ?? null;
	};

	const modelPalette = (modelId: string | null) => {
		if (!modelId) {
			return palettes[0];
		}

		const charCode = modelId.toLowerCase().charCodeAt(0);
		const index = Math.max(0, charCode - 97) % palettes.length;
		return palettes[index];
	};

	const intensity = (entry: UserUsageHeatmapEntry) => {
		const count = entry.messages;
		if (count >= 20) return 4;
		if (count >= 10) return 3;
		if (count >= 5) return 2;
		if (count > 0) return 1;
		return 0;
	};

	const tooltipFor = (entry: UserUsageHeatmapEntry) => {
		const label =
			heatmapMode === 'weekly'
				? `${$i18n.t('Week of')} ${weekStart(entry.date)}`
				: heatmapMode === 'cumulative'
					? `${$i18n.t('Through')} ${entry.date}`
					: entry.date;

		const model = topItem(entry);
		const models = Object.entries(entry.models ?? {}).sort((a, b) => b[1] - a[1]);
		const modelSummary =
			models.length > 0
				? models
						.slice(0, 3)
						.map(([id, count]) => `${modelName(id)} ${count}`)
						.join(', ')
				: $i18n.t('No model data');

		return `${label}: ${formatNumber(entry.tokens)} ${$i18n.t('tokens')}, ${entry.messages.toLocaleString()} ${$i18n.t('messages')}, ${entry.chats.toLocaleString()} ${$i18n.t('chats')}${model ? ` (${modelName(model)})` : ''}. ${modelSummary}`;
	};

	const formatDuration = (seconds: number) => {
		if (!seconds) return '0m';
		const days = Math.floor(seconds / 86400);
		const hours = Math.floor((seconds % 86400) / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);

		if (days > 0) return `${days}d ${hours}h`;
		if (hours > 0) return `${hours}h ${minutes}m`;
		return `${minutes}m`;
	};

	const modelName = (id: string | null) => (id ? (modelNames.get(id) ?? id) : '-');

	onMount(loadUsage);
</script>

<div class="flex h-full min-h-0 flex-col">
	<div class="mb-4">
		<h2 class="text-sm font-medium text-gray-900 dark:text-white">{$i18n.t('Usage')}</h2>
	</div>

	{#if loading}
		<div class="flex flex-1 items-center justify-center">
			<Spinner className="size-5" />
		</div>
	{:else if !usage}
		<div class="flex flex-1 items-center justify-center text-xs text-gray-500">
			{$i18n.t('Failed to load usage')}
		</div>
	{:else}
		<div class="scrollbar-hover min-h-0 flex-1 overflow-y-auto pr-1.5">
			<UserSettingSection title={$i18n.t('Overview')} first>
				<div class="grid grid-cols-2 gap-x-6 gap-y-3 md:grid-cols-5">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{formatNumber(usage.totals.lifetime_tokens)}
						</div>
						<div class="mt-0.5 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t('Lifetime tokens')}
						</div>
					</div>
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{formatNumber(usage.totals.peak_daily_tokens)}
						</div>
						<div class="mt-0.5 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t('Peak tokens')}
						</div>
					</div>
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{formatDuration(usage.totals.longest_chat_seconds)}
						</div>
						<div class="mt-0.5 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t('Longest active chat')}
						</div>
					</div>
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{usage.totals.current_streak.toLocaleString()}
						</div>
						<div class="mt-0.5 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t('Current streak')}
						</div>
					</div>
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{usage.totals.longest_streak.toLocaleString()}
						</div>
						<div class="mt-0.5 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t('Longest streak')}
						</div>
					</div>
				</div>
			</UserSettingSection>

			<section class="mt-4 w-full">
				<div class="mb-2 flex min-w-0 items-center justify-between gap-3">
					<h3 class="min-w-0 shrink truncate text-xs text-gray-400 dark:text-gray-600">
						{$i18n.t('Token activity')}
					</h3>
					<div
						class="flex min-w-0 max-w-[70%] shrink items-center gap-3 overflow-hidden whitespace-nowrap"
					>
						{#each heatmapModes as mode}
							<button
								type="button"
								class="min-w-0 shrink truncate whitespace-nowrap text-xs transition-colors {heatmapMode ===
								mode.value
									? 'text-gray-900 dark:text-white'
									: 'text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}
								"
								on:click={() => {
									heatmapMode = mode.value;
								}}
							>
								{$i18n.t(mode.label)}
							</button>
						{/each}
					</div>
				</div>

				<div class="pb-1">
					<div class="w-full min-w-0 overflow-hidden" bind:clientWidth={heatmapContainerWidth}>
						<div
							class="mx-auto grid grid-flow-col"
							style="width: min(100%, {heatmapGridWidth}); gap: {HEATMAP_GAP_PX}px; aspect-ratio: {heatmapColumns} / 7; grid-template-columns: repeat({heatmapColumns}, minmax(0, 1fr)); grid-template-rows: repeat(7, minmax(0, 1fr));"
						>
							{#each heatmapCells as entry}
								{#if entry}
									<Tooltip content={tooltipFor(entry)}>
										<div
											class="h-full w-full rounded-[2px] {modelPalette(topItem(entry))[
												intensity(entry)
											]}"
											aria-label={tooltipFor(entry)}
										></div>
									</Tooltip>
								{:else}
									<div class="h-full w-full"></div>
								{/if}
							{/each}
						</div>

						<div
							class="mx-auto mt-2 grid text-[0.6875rem] leading-none text-gray-400 dark:text-gray-600"
							style="width: min(100%, {heatmapGridWidth}); column-gap: {HEATMAP_GAP_PX}px; grid-template-columns: repeat({heatmapColumns}, minmax(0, 1fr));"
						>
							{#each monthLabels as month}
								<div class="truncate" style="grid-column: {month.column} / span {month.span};">
									{month.label}
								</div>
							{/each}
						</div>
					</div>

					{#if usage.top_models.length > 0}
						<div
							class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[0.6875rem] text-gray-400 dark:text-gray-600"
						>
							{#each usage.top_models.slice(0, 6) as model}
								<div class="flex min-w-0 items-center gap-1.5">
									<span class="size-2 shrink-0 rounded-[2px] {modelPalette(model.model_id)[3]}"
									></span>
									<span class="max-w-28 truncate">{modelName(model.model_id)}</span>
								</div>
							{/each}
						</div>
					{/if}
				</div>
			</section>

			{#if !hasUsage}
				<UserSettingSection title={$i18n.t('Activity')}>
					<div class="text-xs text-gray-500 dark:text-gray-400">
						{$i18n.t('No usage data found')}
					</div>
				</UserSettingSection>
			{:else}
				<UserSettingSection title={$i18n.t('Activity insights')}>
					<UserSettingRow label={$i18n.t('Models')}>
						<span class="text-xs text-gray-900 dark:text-white">
							{usage.totals.models_used.toLocaleString()}
						</span>
					</UserSettingRow>
					<UserSettingRow label={$i18n.t('Average tokens per chat')}>
						<span class="text-xs text-gray-900 dark:text-white">
							{formatNumber(usage.insights.average_tokens_per_chat)}
						</span>
					</UserSettingRow>
					<UserSettingRow label={$i18n.t('Average messages per active day')}>
						<span class="text-xs text-gray-900 dark:text-white">
							{usage.insights.average_messages_per_active_day.toLocaleString()}
						</span>
					</UserSettingRow>
					<UserSettingRow label={$i18n.t('User messages')}>
						<span class="text-xs text-gray-900 dark:text-white">
							{usage.totals.user_messages.toLocaleString()} · {usage.insights.user_message_share}%
						</span>
					</UserSettingRow>
					<UserSettingRow label={$i18n.t('Assistant messages')}>
						<span class="text-xs text-gray-900 dark:text-white">
							{usage.totals.assistant_messages.toLocaleString()} · {usage.insights
								.assistant_message_share}%
						</span>
					</UserSettingRow>
					<UserSettingRow label={$i18n.t('Total chats')}>
						<span class="text-xs text-gray-900 dark:text-white">
							{usage.totals.total_chats.toLocaleString()}
						</span>
					</UserSettingRow>
				</UserSettingSection>

				<UserSettingSection title={$i18n.t('Top models')}>
					{#if usage.top_models.length === 0}
						<div class="text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t('No model usage found')}
						</div>
					{:else}
						{#each usage.top_models as model}
							<UserSettingRow label={modelName(model.model_id)}>
								<span class="text-xs text-gray-500 dark:text-gray-400">
									{model.messages.toLocaleString()}
									{$i18n.t('messages')} · {formatNumber(model.total_tokens)}
								</span>
							</UserSettingRow>
						{/each}
					{/if}
				</UserSettingSection>

				{#if usage.top_tools.length > 0}
					<UserSettingSection title={$i18n.t('Most used tools')}>
						{#each usage.top_tools as tool}
							<UserSettingRow label={tool.name}>
								<span class="text-xs text-gray-500 dark:text-gray-400">
									{tool.count.toLocaleString()}
									{$i18n.t('runs')}
								</span>
							</UserSettingRow>
						{/each}
					</UserSettingSection>
				{/if}
			{/if}

			<div class="mt-4 text-right text-[0.6875rem] text-gray-400 dark:text-gray-600">
				{$i18n.t('Token counts are estimates and may not reflect actual API usage')}
			</div>
		</div>
	{/if}
</div>

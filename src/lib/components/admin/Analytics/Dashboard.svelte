<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { models } from '$lib/stores';
	import {
		getSummary,
		getModelAnalytics,
		getUserAnalytics,
		getDailyStats,
		getTokenUsage
	} from '$lib/apis/analytics';
	import { getGroups } from '$lib/apis/groups';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';
	import Banknotes from '$lib/components/icons/Banknotes.svelte';
	import UserGroup from '$lib/components/icons/UserGroup.svelte';
	import ChartDonut from './ChartDonut.svelte';
	import ChartBar from './ChartBar.svelte';
	import StatTile from './StatTile.svelte';
	import AnalyticsModelModal from './AnalyticsModelModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { formatNumber, formatCost } from '$lib/utils';
	import { goto } from '$app/navigation';
	import dayjs from 'dayjs';

	const i18n = getContext('i18n');

	// Fixed categorical palette (CVD-validated ordering) — a model keeps its
	// slot color across every chart; the tail past 8 folds into "Other" gray.
	const CHART_COLORS = [
		'#2a78d6',
		'#1baf7a',
		'#eda100',
		'#008300',
		'#4a3aa7',
		'#e34948',
		'#e87ba4',
		'#eb6834'
	];
	const CHART_COLORS_DARK = [
		'#3987e5',
		'#199e70',
		'#c98500',
		'#008300',
		'#9085e9',
		'#e66767',
		'#d55181',
		'#d95926'
	];
	const OTHER_COLOR = '#898781';

	// Shared card shell for every dashboard panel
	const CARD =
		'rounded-2xl border border-gray-100 dark:border-gray-850 bg-gray-50/50 dark:bg-gray-850/30 p-4 min-w-0';
	const CARD_TITLE = 'text-xs font-medium text-gray-700 dark:text-gray-200';

	// Token-kind colors: input/cached share a hue (cached = lighter step of
	// the same ramp), output is distinct
	const KIND_COLORS = { input: '#2a78d6', cached: '#86b6ef', output: '#1baf7a' };

	// Composite key: one row per (workspace model, underlying base model)
	const modelKey = (modelId: string, baseModelId?: string | null) =>
		`${modelId}|${baseModelId ?? ''}`;

	// Time period - persist in localStorage
	let selectedPeriod =
		(typeof localStorage !== 'undefined' && localStorage.getItem('analyticsPeriod')) || '7d';

	// Custom date range (YYYY-MM-DD) - persist in localStorage
	let customStart =
		(typeof localStorage !== 'undefined' && localStorage.getItem('analyticsCustomStart')) || '';
	let customEnd =
		(typeof localStorage !== 'undefined' && localStorage.getItem('analyticsCustomEnd')) || '';

	$: periods = [
		{ value: '24h', label: $i18n.t('Last 24 hours') },
		{ value: '7d', label: $i18n.t('Last 7 days') },
		{ value: '30d', label: $i18n.t('Last 30 days') },
		{ value: '90d', label: $i18n.t('Last 90 days') },
		{ value: 'all', label: $i18n.t('All time') },
		{ value: 'custom', label: $i18n.t('Custom range') }
	];

	// User group filter
	let groups: Array<{ id: string; name: string }> = [];
	let selectedGroupId: string | null = null;

	const getDateRange = (period: string): { start: number | null; end: number | null } => {
		const now = Math.floor(Date.now() / 1000);
		const day = 86400;
		switch (period) {
			case '24h':
				return { start: now - day, end: now };
			case '7d':
				return { start: now - 7 * day, end: now };
			case '30d':
				return { start: now - 30 * day, end: now };
			case '90d':
				return { start: now - 90 * day, end: now };
			case 'custom': {
				// Parse YYYY-MM-DD inputs; end date is inclusive (covers the full day)
				const start = customStart ? Math.floor(new Date(customStart).getTime() / 1000) : null;
				const end = customEnd ? Math.floor(new Date(customEnd).getTime() / 1000) + day - 1 : null;
				return { start, end };
			}
			default:
				return { start: null, end: null };
		}
	};

	// Data
	let summary = { total_messages: 0, total_chats: 0, total_models: 0, total_users: 0 };
	let modelStats: Array<{
		model_id: string;
		base_model_id?: string | null;
		count: number;
		unique_users?: number;
		unique_chats?: number;
		name?: string;
	}> = [];
	let userStats: Array<{
		user_id: string;
		name?: string;
		email?: string;
		count: number;
		total_tokens?: number;
		cost?: number | null;
		models?: Array<{
			model_id: string;
			base_model_id?: string | null;
			count: number;
			unique_chats?: number;
			input_tokens?: number;
			cached_tokens?: number;
			output_tokens?: number;
			total_tokens?: number;
			cost?: number | null;
		}>;
	}> = [];
	let dailyStats: Array<{
		date: string;
		models: Record<string, number>;
		tokens?: Record<string, number>;
		costs?: Record<string, number>;
	}> = [];
	// Keyed by modelKey(model_id, base_model_id)
	let tokenStats: Record<
		string,
		{
			input_tokens: number;
			output_tokens: number;
			cached_tokens: number;
			reasoning_tokens: number;
			total_tokens: number;
			cost?: number | null;
			cost_breakdown?: {
				input?: number | null;
				cached?: number | null;
				output?: number | null;
				reasoning?: number | null;
			} | null;
		}
	> = {};
	// Raw per-(model, base) entries from /tokens, largest first
	let tokenEntries: Array<{
		model_id: string;
		base_model_id?: string | null;
		input_tokens: number;
		output_tokens: number;
		cached_tokens: number;
		reasoning_tokens: number;
		total_tokens: number;
		message_count: number;
		cost?: number | null;
		cost_breakdown?: {
			input?: number | null;
			cached?: number | null;
			output?: number | null;
			reasoning?: number | null;
		} | null;
	}> = [];
	let totalTokens = { input: 0, output: 0, cached: 0, reasoning: 0, total: 0 };
	let totalCost: number | null = null;
	let costBreakdown: {
		input?: number | null;
		cached?: number | null;
		output?: number | null;
		reasoning?: number | null;
	} | null = null;
	let costCurrency = 'USD';

	// Previous-period figures for the stat-tile deltas
	let prevSummary: {
		total_messages: number;
		total_chats: number;
		total_users: number;
	} | null = null;
	let prevTokens: { total_tokens: number; total_cost?: number | null } | null = null;

	// Metric shown in the stacked daily bar chart
	let dailyMetric: 'messages' | 'tokens' | 'cost' = 'messages';

	let loading = true;

	// Selected model for drill-down
	let selectedModel: { id: string; name: string } | null = null;
	let showModelModal = false;

	// Sorting
	let modelOrderBy = 'count';
	let modelDirection: 'asc' | 'desc' = 'desc';

	const toggleModelSort = (key: string) => {
		if (modelOrderBy === key) {
			modelDirection = modelDirection === 'asc' ? 'desc' : 'asc';
		} else {
			modelOrderBy = key;
			modelDirection = key === 'name' ? 'asc' : 'desc';
		}
	};

	const loadDashboard = async () => {
		loading = true;
		try {
			const { start, end } = getDateRange(selectedPeriod);
			const granularity = selectedPeriod === '24h' ? 'hourly' : 'daily';
			// Previous window of the same length, for stat-tile deltas
			const prevRange = start && end ? { start: start - (end - start), end: start } : null;
			const [summaryRes, modelsRes, usersRes, dailyRes, tokensRes, ...prevRes] = await Promise.all([
				getSummary(localStorage.token, start, end, selectedGroupId),
				getModelAnalytics(localStorage.token, start, end, selectedGroupId),
				getUserAnalytics(localStorage.token, start, end, 50, selectedGroupId),
				getDailyStats(localStorage.token, start, end, granularity, selectedGroupId),
				getTokenUsage(localStorage.token, start, end, selectedGroupId),
				prevRange
					? getSummary(localStorage.token, prevRange.start, prevRange.end, selectedGroupId)
					: Promise.resolve(null),
				prevRange
					? getTokenUsage(localStorage.token, prevRange.start, prevRange.end, selectedGroupId)
					: Promise.resolve(null)
			]);

			summary = summaryRes ?? summary;
			prevSummary = prevRes[0] ?? null;
			prevTokens = prevRes[1] ?? null;

			const modelsMap = new Map($models.map((m) => [m.id, m.name || m.id]));
			modelStats = (modelsRes?.models ?? []).map((entry) => ({
				...entry,
				name: modelsMap.get(entry.model_id) || entry.model_id
			}));

			userStats = usersRes?.users ?? [];
			dailyStats = dailyRes?.data ?? [];

			// Process token data
			if (tokensRes) {
				tokenStats = {};
				tokenEntries = tokensRes.models ?? [];
				for (const m of tokenEntries) {
					tokenStats[modelKey(m.model_id, m.base_model_id)] = {
						input_tokens: m.input_tokens,
						output_tokens: m.output_tokens,
						cached_tokens: m.cached_tokens ?? 0,
						reasoning_tokens: m.reasoning_tokens ?? 0,
						total_tokens: m.total_tokens,
						cost: m.cost ?? null,
						cost_breakdown: m.cost_breakdown ?? null
					};
				}
				totalTokens = {
					input: tokensRes.total_input_tokens,
					output: tokensRes.total_output_tokens,
					cached: tokensRes.total_cached_tokens ?? 0,
					reasoning: tokensRes.total_reasoning_tokens ?? 0,
					total: tokensRes.total_tokens
				};
				totalCost = tokensRes.total_cost ?? null;
				costBreakdown = tokensRes.cost_breakdown ?? null;
				costCurrency = tokensRes.currency ?? 'USD';
			}
		} catch (err) {
			console.error('Dashboard load failed:', err);
		}
		loading = false;
	};

	// Reload when the period, group, or custom range changes.
	// In custom mode, wait until both dates are set to avoid a half-specified query.
	$: if (selectedPeriod === 'custom' ? customStart && customEnd : selectedPeriod) {
		// reference customStart/customEnd so this block reruns when they change
		customStart;
		customEnd;
		selectedGroupId;
		loadDashboard();
	}

	onMount(async () => {
		// Load groups for filter
		try {
			const res = await getGroups(localStorage.token);
			groups = res ?? [];
		} catch (e) {
			console.error('Failed to load groups:', e);
		}
	});

	// Token-count columns sortable straight from tokenStats
	const TOKEN_SORT_FIELDS: Record<
		string,
		'input_tokens' | 'cached_tokens' | 'output_tokens' | 'total_tokens'
	> = {
		input: 'input_tokens',
		cached: 'cached_tokens',
		output: 'output_tokens',
		tokens: 'total_tokens'
	};

	$: sortedModels = [...modelStats].sort((a, b) => {
		if (modelOrderBy === 'name') {
			return modelDirection === 'asc' ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name);
		}
		if (modelOrderBy === 'cost') {
			const aCost = tokenStats[modelKey(a.model_id, a.base_model_id)]?.cost ?? 0;
			const bCost = tokenStats[modelKey(b.model_id, b.base_model_id)]?.cost ?? 0;
			return modelDirection === 'asc' ? aCost - bCost : bCost - aCost;
		}
		if (modelOrderBy === 'users') {
			const aUsers = a.unique_users ?? 0;
			const bUsers = b.unique_users ?? 0;
			return modelDirection === 'asc' ? aUsers - bUsers : bUsers - aUsers;
		}
		if (modelOrderBy === 'chats') {
			const aChats = a.unique_chats ?? 0;
			const bChats = b.unique_chats ?? 0;
			return modelDirection === 'asc' ? aChats - bChats : bChats - aChats;
		}
		const field = TOKEN_SORT_FIELDS[modelOrderBy];
		if (field) {
			const aVal = tokenStats[modelKey(a.model_id, a.base_model_id)]?.[field] ?? 0;
			const bVal = tokenStats[modelKey(b.model_id, b.base_model_id)]?.[field] ?? 0;
			return modelDirection === 'asc' ? aVal - bVal : bVal - aVal;
		}
		return modelDirection === 'asc' ? a.count - b.count : b.count - a.count;
	});

	// Sortable numeric columns of the Model Usage table, in display order
	$: modelColumns = [
		{ key: 'count', label: $i18n.t('Messages') },
		{ key: 'users', label: $i18n.t('Users') },
		{ key: 'chats', label: $i18n.t('Chats') },
		{ key: 'input', label: $i18n.t('Input') },
		{ key: 'cached', label: $i18n.t('Cached') },
		{ key: 'output', label: $i18n.t('Output') },
		{ key: 'tokens', label: $i18n.t('Tokens') },
		{ key: 'cost', label: $i18n.t('Cost') }
	];

	// Per-user cards, biggest spender first (message count as tiebreaker)
	$: sortedUserCards = [...userStats].sort(
		(a, b) => (b.cost ?? 0) - (a.cost ?? 0) || b.count - a.count
	);

	$: totalModelMessages = modelStats.reduce((sum, m) => sum + m.count, 0);

	// ---- Stat-tile deltas (vs the previous period of the same length) ----
	const pctDelta = (curr: number, prev: number | null | undefined): number | null => {
		if (prev == null || prev === 0) return null;
		return ((curr - prev) / prev) * 100;
	};

	$: messagesDelta = pctDelta(summary.total_messages, prevSummary?.total_messages);
	$: usersDelta = pctDelta(summary.total_users, prevSummary?.total_users);
	$: tokensDelta = pctDelta(totalTokens.total, prevTokens?.total_tokens);
	$: costDelta =
		totalCost != null && prevTokens?.total_cost != null
			? pctDelta(totalCost, prevTokens.total_cost)
			: null;

	// ---- Fixed model → color assignment (shared by every chart) ----
	// Color follows the workspace model (entity), so a base-model change
	// keeps the same color across its history entries.
	$: modelNameMap = new Map($models.map((m) => [m.id, m.name || m.id]));
	$: modelColorOrder = [...new Set(modelStats.map((m) => m.model_id))];
	$: modelColorMap = new Map(
		modelColorOrder.map((id, i) => [id, i < CHART_COLORS.length ? CHART_COLORS[i] : OTHER_COLOR])
	);
	$: modelColorMapDark = new Map(
		modelColorOrder.map((id, i) => [
			id,
			i < CHART_COLORS_DARK.length ? CHART_COLORS_DARK[i] : OTHER_COLOR
		])
	);

	// Workspace models display with their underlying model, e.g.
	// "Professeur Chen (Anthropic Opus 4.8)". Prefer the base recorded in the
	// ledger at usage time (base-model changes stay visible in history); rows
	// recorded before base tracking fall back to the model's current base.
	$: modelBaseMap = new Map($models.map((m) => [m.id, m?.info?.base_model_id ?? null]));
	$: displayModelName = (modelId: string, baseModelId?: string | null): string => {
		const name = modelNameMap.get(modelId) || modelId;
		const base = baseModelId || modelBaseMap.get(modelId);
		if (base && base !== modelId) {
			return `${name} (${modelNameMap.get(base) || base})`;
		}
		return name;
	};

	// ---- Donut: cost share by model (token share when nothing is priced) ----
	$: costDonutData = tokenEntries
		.map((m) => ({
			label: displayModelName(m.model_id, m.base_model_id),
			value: m.cost ?? 0,
			color: modelColorMap.get(m.model_id),
			colorDark: modelColorMapDark.get(m.model_id)
		}))
		.filter((d) => d.value > 0);
	$: tokenDonutData = tokenEntries
		.map((m) => ({
			label: displayModelName(m.model_id, m.base_model_id),
			value: m.total_tokens ?? 0,
			color: modelColorMap.get(m.model_id),
			colorDark: modelColorMapDark.get(m.model_id)
		}))
		.filter((d) => d.value > 0);
	$: showCostDonut = costDonutData.length > 0;

	// ---- Token breakdown per model (input/cached/output + cost each) ----
	$: breakdownModels = [...tokenEntries]
		.filter((m) => m.total_tokens > 0)
		.sort((a, b) => b.total_tokens - a.total_tokens)
		.slice(0, 6);
	$: breakdownTooltip = (m: (typeof tokenEntries)[number]): string => {
		const parts = [
			`${$i18n.t('Input (uncached)')}: ${formatNumber(Math.max(0, m.input_tokens - m.cached_tokens))}${m.cost_breakdown?.input != null ? ` (~${formatCost(m.cost_breakdown.input, costCurrency)})` : ''}`,
			`${$i18n.t('Cached input')}: ${formatNumber(m.cached_tokens)}${m.cost_breakdown?.cached != null ? ` (~${formatCost(m.cost_breakdown.cached, costCurrency)})` : ''}`,
			`${$i18n.t('Output')}: ${formatNumber(m.output_tokens)}${m.cost_breakdown?.output != null ? ` (~${formatCost(m.cost_breakdown.output, costCurrency)})` : ''}`
		];
		if (m.reasoning_tokens > 0) {
			parts.push(
				`${$i18n.t('incl. reasoning')}: ${formatNumber(m.reasoning_tokens)}${m.cost_breakdown?.reasoning != null ? ` (~${formatCost(m.cost_breakdown.reasoning, costCurrency)})` : ''}`
			);
		}
		return parts.join(' · ');
	};

	// ---- Stacked bar: daily messages / tokens / cost per model ----
	$: metricOptions = [
		{ value: 'messages' as const, label: $i18n.t('Messages') },
		{ value: 'tokens' as const, label: $i18n.t('Tokens') },
		{ value: 'cost' as const, label: $i18n.t('Cost') }
	];

	const dailyMetricValues = (
		day: {
			models: Record<string, number>;
			tokens?: Record<string, number>;
			costs?: Record<string, number>;
		},
		metric: string
	): Record<string, number> =>
		(metric === 'messages' ? day.models : metric === 'tokens' ? day.tokens : day.costs) ?? {};

	$: dailyBarLabels = dailyStats.map((d) =>
		dayjs(d.date).format(d.date.includes(':') ? 'h A' : 'M/D')
	);
	// Tooltip line for one model (or the "Other" group) on one day:
	// token count plus that day's cost
	$: dailyTooltipDetail = (
		day: { tokens?: Record<string, number>; costs?: Record<string, number> },
		ids: string[]
	): string => {
		const tokens = ids.reduce((sum, id) => sum + (day.tokens?.[id] || 0), 0);
		const priced = ids.filter((id) => day.costs?.[id] != null);
		const cost = priced.reduce((sum, id) => sum + (day.costs?.[id] || 0), 0);
		return `${formatNumber(tokens)} ${$i18n.t('tokens')}${
			priced.length ? ` · ~${formatCost(cost, costCurrency)}` : ''
		}`;
	};
	$: dailyBarDatasets = (() => {
		const totals: Record<string, number> = {};
		for (const day of dailyStats) {
			for (const [id, value] of Object.entries(dailyMetricValues(day, dailyMetric))) {
				totals[id] = (totals[id] || 0) + (value || 0);
			}
		}
		const ordered = Object.entries(totals)
			.sort((a, b) => b[1] - a[1])
			.map(([id]) => id);
		const top = ordered.slice(0, 8);
		const rest = ordered.slice(8);

		const sets = top.map((id) => ({
			label: modelNameMap.get(id) || id,
			data: dailyStats.map((day) => dailyMetricValues(day, dailyMetric)[id] || 0),
			color: modelColorMap.get(id) || OTHER_COLOR,
			colorDark: modelColorMapDark.get(id) || OTHER_COLOR,
			tooltipLabels: dailyStats.map((day) => dailyTooltipDetail(day, [id]))
		}));
		if (rest.length) {
			sets.push({
				label: $i18n.t('Other'),
				data: dailyStats.map((day) =>
					rest.reduce((sum, id) => sum + (dailyMetricValues(day, dailyMetric)[id] || 0), 0)
				),
				color: OTHER_COLOR,
				colorDark: OTHER_COLOR,
				tooltipLabels: dailyStats.map((day) => dailyTooltipDetail(day, rest))
			});
		}
		return sets;
	})();
	$: dailyValueFormatter =
		dailyMetric === 'cost'
			? (value: number) => formatCost(value, costCurrency)
			: (value: number) => formatNumber(value);

	// ---- Horizontal bar: top users by cost (tokens when nothing is priced) ----
	$: topUsersByCost = [...userStats]
		.filter((u) => (u.cost ?? 0) > 0)
		.sort((a, b) => (b.cost ?? 0) - (a.cost ?? 0))
		.slice(0, 10);
	$: topUsersMetricIsCost = topUsersByCost.length > 0;
	$: topUsersBar = topUsersMetricIsCost
		? topUsersByCost
		: [...userStats]
				.filter((u) => (u.total_tokens ?? 0) > 0)
				.sort((a, b) => (b.total_tokens ?? 0) - (a.total_tokens ?? 0))
				.slice(0, 10);
	$: topUsersLabels = topUsersBar.map((u) => u.name || u.email || u.user_id.substring(0, 8));
	$: topUsersData = topUsersBar.map((u) =>
		topUsersMetricIsCost ? (u.cost ?? 0) : (u.total_tokens ?? 0)
	);
	$: topUsersFormatter = topUsersMetricIsCost
		? (value: number) => formatCost(value, costCurrency)
		: (value: number) => formatNumber(value);

	// ---- Stat-tile sparklines (per-day totals across models) ----
	const daySum = (record: Record<string, number> | undefined) =>
		Object.values(record ?? {}).reduce((sum, v) => sum + (v || 0), 0);
	$: sparkMessages = dailyStats.length > 2 ? dailyStats.map((d) => daySum(d.models)) : [];
	$: sparkTokens = dailyStats.length > 2 ? dailyStats.map((d) => daySum(d.tokens)) : [];
	$: sparkCost = dailyStats.length > 2 ? dailyStats.map((d) => daySum(d.costs)) : [];

	// Persist period selection
	$: if (typeof localStorage !== 'undefined' && selectedPeriod) {
		localStorage.setItem('analyticsPeriod', selectedPeriod);
	}

	// Persist custom date range
	$: if (typeof localStorage !== 'undefined') {
		localStorage.setItem('analyticsCustomStart', customStart);
		localStorage.setItem('analyticsCustomEnd', customEnd);
	}
</script>

<!-- Header with title and period selector -->
<div
	class="pt-0.5 pb-1 gap-1 flex flex-row justify-between items-center sticky top-0 z-10 bg-white dark:bg-gray-900"
>
	<div class="text-lg font-medium px-0.5 shrink-0">
		{$i18n.t('Analytics')}
	</div>
	<div class="flex items-center gap-2 flex-wrap justify-end min-w-0">
		{#if groups.length > 0}
			<select
				bind:value={selectedGroupId}
				class="w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-none text-right"
			>
				<option value={null}>{$i18n.t('All Users')}</option>
				{#each groups as group}
					<option value={group.id}>{group.name}</option>
				{/each}
			</select>
		{/if}
		{#if selectedPeriod === 'custom'}
			<input
				type="date"
				bind:value={customStart}
				max={customEnd || undefined}
				class="w-fit rounded-sm px-2 text-xs bg-transparent outline-none"
			/>
			<span class="text-xs text-gray-400">–</span>
			<input
				type="date"
				bind:value={customEnd}
				min={customStart || undefined}
				class="w-fit rounded-sm px-2 text-xs bg-transparent outline-none"
			/>
		{/if}
		<select
			bind:value={selectedPeriod}
			class="w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-none text-right"
		>
			{#each periods as period}
				<option value={period.value}>{period.label}</option>
			{/each}
		</select>
	</div>
</div>

<!-- Model Details Modal -->
<AnalyticsModelModal
	bind:show={showModelModal}
	model={selectedModel}
	startDate={getDateRange(selectedPeriod).start}
	endDate={getDateRange(selectedPeriod).end}
/>

{#if loading}
	<div class="my-10 flex justify-center">
		<Spinner className="size-5" />
	</div>
{:else}
	<div class="flex flex-col gap-3 pb-12">
		<!-- Summary stat tiles -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
			<StatTile
				label={$i18n.t('Users')}
				value={summary.total_users.toLocaleString()}
				delta={usersDelta}
				accent="#4a3aa7"
			>
				<UserGroup slot="icon" className="size-3.5" />
			</StatTile>
			<StatTile
				label={$i18n.t('Messages')}
				value={summary.total_messages.toLocaleString()}
				delta={messagesDelta}
				accent="#2a78d6"
				trend={sparkMessages}
			>
				<ChatBubble slot="icon" className="size-3.5" />
			</StatTile>
			<StatTile
				label={$i18n.t('Tokens')}
				value={formatNumber(totalTokens.total)}
				delta={tokensDelta}
				tooltip={$i18n.t('Token counts are estimates and may not reflect actual API usage')}
				accent="#1baf7a"
				trend={sparkTokens}
			>
				<Cube slot="icon" className="size-3.5" />
			</StatTile>
			<StatTile
				label={$i18n.t('Cost')}
				value={totalCost != null ? `~${formatCost(totalCost, costCurrency)}` : '—'}
				delta={costDelta}
				tooltip={$i18n.t('Costs are estimates based on current model pricing')}
				accent="#eda100"
				trend={sparkCost}
			>
				<Banknotes slot="icon" className="size-3.5" />
			</StatTile>
		</div>

		<!-- Token breakdown, cost share, top users -->
		<div class="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
			<div class={CARD}>
				<div class="flex items-center justify-between gap-2 mb-3">
					<div class={CARD_TITLE}>{$i18n.t('Token Breakdown')}</div>
					<div class="flex gap-2.5 text-[10px] text-gray-400">
						<span class="flex items-center gap-1">
							<span class="size-1.5 rounded-full" style="background-color: {KIND_COLORS.input}"
							></span>{$i18n.t('Input')}
						</span>
						<span class="flex items-center gap-1">
							<span class="size-1.5 rounded-full" style="background-color: {KIND_COLORS.cached}"
							></span>{$i18n.t('Cached')}
						</span>
						<span class="flex items-center gap-1">
							<span class="size-1.5 rounded-full" style="background-color: {KIND_COLORS.output}"
							></span>{$i18n.t('Output')}
						</span>
					</div>
				</div>
				{#if breakdownModels.length > 0}
					<div class="flex flex-col gap-2.5">
						{#each breakdownModels as m (modelKey(m.model_id, m.base_model_id))}
							{@const uncached = Math.max(0, m.input_tokens - m.cached_tokens)}
							{@const kindTotal = Math.max(1, uncached + m.cached_tokens + m.output_tokens)}
							<div class="min-w-0">
								<div class="flex items-center gap-2 text-xs mb-1 min-w-0">
									<span
										class="size-1.5 rounded-full shrink-0"
										style="background-color: {modelColorMap.get(m.model_id) || OTHER_COLOR}"
									></span>
									<span class="truncate text-gray-600 dark:text-gray-300"
										>{displayModelName(m.model_id, m.base_model_id)}</span
									>
									<span class="ml-auto shrink-0 tabular-nums text-gray-900 dark:text-white">
										{formatNumber(m.total_tokens)}
									</span>
								</div>
								<Tooltip content={breakdownTooltip(m)} className="w-full">
									<div class="flex h-1.5 rounded-full overflow-hidden gap-[2px] cursor-help">
										{#if uncached > 0}
											<div
												class="h-full rounded-full"
												style="width: {(uncached / kindTotal) *
													100}%; background-color: {KIND_COLORS.input}"
											></div>
										{/if}
										{#if m.cached_tokens > 0}
											<div
												class="h-full rounded-full"
												style="width: {(m.cached_tokens / kindTotal) *
													100}%; background-color: {KIND_COLORS.cached}"
											></div>
										{/if}
										{#if m.output_tokens > 0}
											<div
												class="h-full rounded-full"
												style="width: {(m.output_tokens / kindTotal) *
													100}%; background-color: {KIND_COLORS.output}"
											></div>
										{/if}
									</div>
								</Tooltip>
							</div>
						{/each}
					</div>
				{:else}
					<div class="flex items-center justify-center h-32 text-gray-400 text-xs">
						{$i18n.t('No data')}
					</div>
				{/if}
			</div>

			<div class={CARD}>
				<div class="{CARD_TITLE} mb-3">
					{showCostDonut ? $i18n.t('Cost by Model') : $i18n.t('Tokens by Model')}
				</div>
				<ChartDonut
					data={showCostDonut ? costDonutData : tokenDonutData}
					otherLabel={$i18n.t('Other')}
					centerValue={showCostDonut && totalCost != null
						? `~${formatCost(totalCost, costCurrency)}`
						: formatNumber(totalTokens.total)}
					centerLabel={showCostDonut ? $i18n.t('cost') : $i18n.t('tokens')}
					valueFormatter={showCostDonut
						? (value) => `~${formatCost(value, costCurrency)}`
						: (value) => formatNumber(value)}
				/>
			</div>

			<div class="{CARD} md:col-span-2 xl:col-span-1">
				<div class="{CARD_TITLE} mb-3">
					{topUsersMetricIsCost ? $i18n.t('Top Users by Cost') : $i18n.t('Top Users by Tokens')}
				</div>
				<ChartBar
					horizontal
					labels={topUsersLabels}
					datasets={[
						{
							label: topUsersMetricIsCost ? $i18n.t('Cost') : $i18n.t('Tokens'),
							data: topUsersData,
							color: '#2a78d6',
							colorDark: '#3987e5'
						}
					]}
					height={topUsersBar.length > 0 ? Math.max(120, topUsersBar.length * 22) : 150}
					valueFormatter={topUsersFormatter}
					showLegend={false}
				/>
			</div>
		</div>

		<!-- Time series -->
		{#if dailyStats.length > 1}
			<div class={CARD}>
				<div class="flex items-center justify-between mb-3">
					<div class={CARD_TITLE}>
						{selectedPeriod === '24h' ? $i18n.t('Hourly Usage') : $i18n.t('Daily Usage')}
					</div>
					<div class="flex gap-0.5 p-0.5 rounded-full bg-gray-100 dark:bg-gray-850 text-[10px]">
						{#each metricOptions as option}
							<button
								class="px-2.5 py-1 rounded-full transition font-medium {dailyMetric === option.value
									? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
									: 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}"
								on:click={() => (dailyMetric = option.value)}
							>
								{option.label}
							</button>
						{/each}
					</div>
				</div>
				<ChartBar
					labels={dailyBarLabels}
					datasets={dailyBarDatasets}
					stacked
					height={190}
					valueFormatter={dailyValueFormatter}
				/>
			</div>
		{/if}

		<!-- Model Usage Table -->
		<div class={CARD}>
			<div class="{CARD_TITLE} mb-2">
				{$i18n.t('Model Usage')}
			</div>
			<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full">
				<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto">
					<thead class="text-xs text-gray-800 uppercase bg-transparent dark:text-gray-200">
						<tr class="border-b-[1.5px] border-gray-50 dark:border-gray-850/30">
							<th scope="col" class="px-2.5 py-2 w-8">#</th>
							<th
								scope="col"
								class="px-2.5 py-2 cursor-pointer select-none"
								on:click={() => toggleModelSort('name')}
							>
								<div class="flex gap-1.5 items-center">
									{$i18n.t('Model')}
									{#if modelOrderBy === 'name'}
										<span class="font-normal">
											{#if modelDirection === 'asc'}<ChevronUp
													className="size-2"
												/>{:else}<ChevronDown className="size-2" />{/if}
										</span>
									{:else}
										<span class="invisible"><ChevronUp className="size-2" /></span>
									{/if}
								</div>
							</th>
							{#each modelColumns as column (column.key)}
								<th
									scope="col"
									class="px-2.5 py-2 cursor-pointer select-none text-right"
									on:click={() => toggleModelSort(column.key)}
								>
									<div class="flex gap-1.5 items-center justify-end">
										{column.label}
										{#if modelOrderBy === column.key}
											<span class="font-normal">
												{#if modelDirection === 'asc'}<ChevronUp
														className="size-2"
													/>{:else}<ChevronDown className="size-2" />{/if}
											</span>
										{:else}
											<span class="invisible"><ChevronUp className="size-2" /></span>
										{/if}
									</div>
								</th>
							{/each}
							<th
								scope="col"
								class="px-2.5 py-2 cursor-pointer select-none text-right w-16"
								on:click={() => toggleModelSort('percentage')}
							>
								<div class="flex gap-1.5 items-center justify-end">
									%
									{#if modelOrderBy === 'percentage'}
										<span class="font-normal">
											{#if modelDirection === 'asc'}<ChevronUp
													className="size-2"
												/>{:else}<ChevronDown className="size-2" />{/if}
										</span>
									{:else}
										<span class="invisible"><ChevronUp className="size-2" /></span>
									{/if}
								</div>
							</th>
						</tr>
					</thead>
					<tbody>
						{#each sortedModels as model, idx (modelKey(model.model_id, model.base_model_id))}
							{@const pct = totalModelMessages > 0 ? (model.count / totalModelMessages) * 100 : 0}
							{@const modelTokens = tokenStats[modelKey(model.model_id, model.base_model_id)]}
							<tr
								class="text-xs cursor-pointer hover:bg-gray-100/60 dark:hover:bg-gray-850/60 transition-colors"
								on:click={() => {
									selectedModel = { id: model.model_id, name: model.name };
									showModelModal = true;
								}}
							>
								<td class="px-3 py-1.5 text-gray-400">{idx + 1}</td>
								<td class="px-3 py-1.5 font-medium text-gray-900 dark:text-white">
									<div class="flex items-center gap-2">
										<span
											class="size-1.5 rounded-full shrink-0"
											style="background-color: {modelColorMap.get(model.model_id) || OTHER_COLOR}"
										></span>
										<img
											src="{WEBUI_API_BASE_URL}/models/model/profile/image?id={model.model_id}"
											alt={model.name}
											class="size-5 rounded-full object-cover shrink-0"
											on:error={(e) => {
												e.target.src = '/favicon.png';
											}}
										/>
										<span class="truncate max-w-[240px]"
											>{displayModelName(model.model_id, model.base_model_id)}</span
										>
									</div>
								</td>
								<td class="px-3 py-1.5 text-right tabular-nums">{model.count.toLocaleString()}</td>
								<td class="px-3 py-1.5 text-right tabular-nums"
									>{(model.unique_users ?? 0).toLocaleString()}</td
								>
								<td class="px-3 py-1.5 text-right tabular-nums"
									>{(model.unique_chats ?? 0).toLocaleString()}</td
								>
								<td class="px-3 py-1.5 text-right tabular-nums">
									<div>{formatNumber(modelTokens?.input_tokens ?? 0)}</div>
									{#if modelTokens?.cost_breakdown?.input != null}
										<div class="text-[10px] text-gray-400">
											~{formatCost(modelTokens.cost_breakdown.input, costCurrency)}
										</div>
									{/if}
								</td>
								<td class="px-3 py-1.5 text-right tabular-nums">
									<div>{formatNumber(modelTokens?.cached_tokens ?? 0)}</div>
									{#if modelTokens?.cost_breakdown?.cached != null}
										<div class="text-[10px] text-gray-400">
											~{formatCost(modelTokens.cost_breakdown.cached, costCurrency)}
										</div>
									{/if}
								</td>
								<td class="px-3 py-1.5 text-right tabular-nums">
									<div>{formatNumber(modelTokens?.output_tokens ?? 0)}</div>
									{#if modelTokens?.cost_breakdown?.output != null}
										<div class="text-[10px] text-gray-400">
											~{formatCost(modelTokens.cost_breakdown.output, costCurrency)}
										</div>
									{/if}
								</td>
								<td class="px-3 py-1.5 text-right tabular-nums"
									>{formatNumber(modelTokens?.total_tokens ?? 0)}</td
								>
								<td class="px-3 py-1.5 text-right tabular-nums">
									{modelTokens?.cost != null
										? `~${formatCost(modelTokens.cost, costCurrency)}`
										: '—'}
								</td>
								<td class="px-3 py-1.5 text-right">
									<div class="flex items-center justify-end gap-1.5">
										<div
											class="w-10 h-1 rounded-full bg-gray-200/70 dark:bg-gray-800 overflow-hidden shrink-0"
										>
											<div
												class="h-full rounded-full"
												style="width: {pct}%; background-color: {modelColorMap.get(
													model.model_id
												) || OTHER_COLOR}"
											></div>
										</div>
										<span class="w-11 text-right shrink-0 text-gray-400 tabular-nums"
											>{pct.toFixed(1)}%</span
										>
									</div>
								</td>
							</tr>
						{/each}
						{#if sortedModels.length === 0}
							<tr
								><td colspan="11" class="px-3 py-2 text-center text-gray-400"
									>{$i18n.t('No data')}</td
								></tr
							>
						{/if}
					</tbody>
				</table>
			</div>
		</div>

		<!-- Per-user usage cards -->
		<div>
			<div class="{CARD_TITLE} mb-2 px-0.5">
				{$i18n.t('User Activity')}
			</div>
			{#if sortedUserCards.length > 0}
				<!-- Full-width cards: the per-model table needs the room -->
				<div class="flex flex-col gap-3">
					{#each sortedUserCards as user (user.user_id)}
						<div class={CARD}>
							<div class="flex items-center gap-2.5">
								<img
									src="{WEBUI_API_BASE_URL}/users/{user.user_id}/profile/image"
									alt={user.name || 'User'}
									class="size-8 rounded-full object-cover shrink-0"
									on:error={(e) => {
										e.target.src = '/user.png';
									}}
								/>
								<div class="min-w-0 flex-1">
									<div class="text-sm font-medium text-gray-900 dark:text-white truncate">
										{user.name || user.email || user.user_id.substring(0, 8)}
									</div>
									<div class="text-[11px] text-gray-400 truncate">
										{user.count.toLocaleString()}
										{$i18n.t('messages')} · {formatNumber(user.total_tokens ?? 0)}
										{$i18n.t('tokens')}
									</div>
								</div>
								<div class="text-right shrink-0">
									<div class="text-sm font-semibold text-gray-900 dark:text-white tabular-nums">
										{user.cost != null ? `~${formatCost(user.cost, costCurrency)}` : '—'}
									</div>
									<div class="text-[10px] text-gray-400">{$i18n.t('cost')}</div>
								</div>
							</div>
							{#if (user.models ?? []).length > 0}
								<div class="overflow-x-auto scrollbar-hidden">
									<div class="min-w-[640px]">
										<div
											class="flex items-center gap-2 text-[10px] uppercase whitespace-nowrap text-gray-400 mt-2.5 pb-1 border-b border-gray-100 dark:border-gray-850"
										>
											<span class="flex-1">{$i18n.t('Model')}</span>
											<span class="w-12 text-right shrink-0">{$i18n.t('Chats')}</span>
											<span class="w-16 text-right shrink-0">{$i18n.t('Messages')}</span>
											<span class="w-14 text-right shrink-0">{$i18n.t('Input')}</span>
											<span class="w-14 text-right shrink-0">{$i18n.t('Cached')}</span>
											<span class="w-14 text-right shrink-0">{$i18n.t('Output')}</span>
											<span class="w-14 text-right shrink-0">{$i18n.t('Tokens')}</span>
											<span class="w-16 text-right shrink-0">{$i18n.t('Cost')}</span>
											<span class="w-11 text-right shrink-0">%</span>
										</div>
										<div class="flex flex-col">
											{#each user.models ?? [] as m (modelKey(m.model_id, m.base_model_id))}
												{@const pct = user.count > 0 ? (m.count / user.count) * 100 : 0}
												<div
													class="flex items-center gap-2 text-xs py-1 border-b border-gray-100/60 dark:border-gray-850/60 last:border-0 min-w-0"
												>
													<span
														class="size-1.5 rounded-full shrink-0"
														style="background-color: {modelColorMap.get(m.model_id) || OTHER_COLOR}"
													></span>
													<span class="flex-1 truncate text-gray-600 dark:text-gray-300">
														{displayModelName(m.model_id, m.base_model_id)}
													</span>
													<span
														class="w-12 text-right tabular-nums text-gray-500 dark:text-gray-400 shrink-0"
													>
														{(m.unique_chats ?? 0).toLocaleString()}
													</span>
													<span
														class="w-16 text-right tabular-nums text-gray-500 dark:text-gray-400 shrink-0"
													>
														{m.count.toLocaleString()}
													</span>
													<span
														class="w-14 text-right tabular-nums text-gray-500 dark:text-gray-400 shrink-0"
													>
														{formatNumber(m.input_tokens ?? 0)}
													</span>
													<span
														class="w-14 text-right tabular-nums text-gray-500 dark:text-gray-400 shrink-0"
													>
														{formatNumber(m.cached_tokens ?? 0)}
													</span>
													<span
														class="w-14 text-right tabular-nums text-gray-500 dark:text-gray-400 shrink-0"
													>
														{formatNumber(m.output_tokens ?? 0)}
													</span>
													<span
														class="w-14 text-right tabular-nums text-gray-500 dark:text-gray-400 shrink-0"
													>
														{formatNumber(m.total_tokens ?? 0)}
													</span>
													<span
														class="w-16 text-right tabular-nums text-gray-900 dark:text-white shrink-0"
													>
														{m.cost != null ? `~${formatCost(m.cost, costCurrency)}` : '—'}
													</span>
													<span class="w-11 text-right tabular-nums text-gray-400 shrink-0">
														{pct.toFixed(1)}%
													</span>
												</div>
											{/each}
										</div>
									</div>
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{:else}
				<div class="{CARD} flex items-center justify-center h-24 text-gray-400 text-xs">
					{$i18n.t('No data')}
				</div>
			{/if}
		</div>
	</div>
{/if}

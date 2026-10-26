<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import dayjs from 'dayjs';
	import { models, config } from '$lib/stores';
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
	import UsageChart, {
		usageShare,
		modelColor,
		defaultInterval,
		type UsageBucket,
		type UsageInterval
	} from './UsageChart.svelte';
	import AnalyticsModelModal from './AnalyticsModelModal.svelte';
	import SessionExplorer from './SessionExplorer.svelte';
	import ProfilePreview from '$lib/components/channel/Messages/Message/ProfilePreview.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { formatNumber } from '$lib/utils';

	const i18n = getContext<any>('i18n');

	// Time period - persist in localStorage
	let selectedPeriod =
		(typeof localStorage !== 'undefined' && localStorage.getItem('analyticsPeriod')) || '7d';
	let granularity: UsageInterval;
	$: granularity = defaultInterval(selectedPeriod);
	let selectedMetric: 'messages' | 'tokens' = 'tokens';
	let chartModel: string | null = null;
	let chartView: 'volume' | 'activity' = 'volume';
	let compare = false;
	$: comparing = compare && chartView === 'volume' && selectedPeriod !== 'all' && validRange;
	$: modelNames = Object.fromEntries([
		...$models.map((model) => [model.id, model.name || model.id]),
		...modelStats.map((model) => [model.model_id, model.name])
	]);

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
		{ value: 'ytd', label: $i18n.t('Year to date') },
		{ value: '1y', label: $i18n.t('Last 12 months') },
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
			case 'ytd':
				return {
					start: dayjs(now * 1000)
						.startOf('year')
						.unix(),
					end: now
				};
			case '1y':
				return {
					start: dayjs(now * 1000)
						.subtract(1, 'year')
						.unix(),
					end: now
				};
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

	type TokenUsage = { input_tokens: number; output_tokens: number; total_tokens: number };
	$: tokenColumns = [
		// $i18n.t('Input Tokens')
		{ key: 'input_tokens', label: $i18n.t('Input') },
		// $i18n.t('Output Tokens')
		{ key: 'output_tokens', label: $i18n.t('Output') },
		// $i18n.t('Total Tokens')
		{ key: 'total_tokens', label: $i18n.t('Total') }
	] as const;
	let selectedLeaderboard = 'models';
	let analyticsView: 'overview' | 'sessions' = 'overview';
	let dateRange: { start: number | null; end: number | null };
	$: {
		selectedPeriod;
		customStart;
		customEnd;
		dateRange = getDateRange(selectedPeriod);
	}
	$: sessionScope = {
		startDate: dateRange.start,
		endDate: dateRange.end,
		groupId: selectedGroupId
	};

	// Data
	let summary = { total_messages: 0, total_chats: 0, total_models: 0, total_users: 0 };
	let modelStats: Array<{
		model_id: string;
		count: number;
		unique_users?: number;
		unique_chats?: number;
		name: string;
	}> = [];
	let userStats: Array<
		{ user_id: string; name?: string; email?: string; count: number } & Partial<TokenUsage>
	> = [];
	let dailyStats: UsageBucket[] = [];
	let tokenStats: Record<string, TokenUsage> = {};
	let totalTokens = { input: 0, output: 0, total: 0 };
	$: metricTotal = selectedMetric === 'tokens' ? totalTokens.total : summary.total_messages;

	let loading = true;
	let mounted = false;
	let loadError = false;
	let loadId = 0;
	$: validRange =
		selectedPeriod !== 'custom' || Boolean(customStart && customEnd && customStart <= customEnd);

	// Selected model for drill-down
	let selectedModel: { id: string; name: string } | null = null;
	let showModelModal = false;

	// Sorting
	let modelOrderBy = 'total_tokens';
	let modelDirection: 'asc' | 'desc' = 'desc';
	let userOrderBy = 'total_tokens';
	let userDirection: 'asc' | 'desc' = 'desc';

	const toggleModelSort = (key: string) => {
		if (modelOrderBy === key) {
			modelDirection = modelDirection === 'asc' ? 'desc' : 'asc';
		} else {
			modelOrderBy = key;
			modelDirection = key === 'name' ? 'asc' : 'desc';
		}
	};

	const toggleUserSort = (key: string) => {
		if (userOrderBy === key) {
			userDirection = userDirection === 'asc' ? 'desc' : 'asc';
		} else {
			userOrderBy = key;
			userDirection = key === 'user_id' ? 'asc' : 'desc';
		}
	};

	const loadDashboard = async () => {
		const id = ++loadId;
		loading = true;
		loadError = false;
		try {
			const { start, end } = getDateRange(selectedPeriod);
			const [summaryRes, modelsRes, usersRes, dailyRes, tokensRes] = await Promise.all([
				getSummary(localStorage.token, start, end, selectedGroupId),
				getModelAnalytics(localStorage.token, start, end, selectedGroupId),
				getUserAnalytics(localStorage.token, start, end, 50, selectedGroupId, selectedMetric),
				getDailyStats(
					localStorage.token,
					start,
					end,
					granularity,
					selectedGroupId,
					selectedMetric,
					comparing
				),
				getTokenUsage(localStorage.token, start, end, selectedGroupId)
			]);

			if (id !== loadId) return;
			if (!summaryRes || !modelsRes || !usersRes || !dailyRes || !tokensRes) {
				throw new Error('Incomplete analytics response');
			}
			if (comparing && dailyRes.data.some((bucket: UsageBucket) => !bucket.previous)) {
				throw new Error('Incomplete comparison response');
			}
			summary = summaryRes;

			const modelsMap = new Map($models.map((m) => [m.id, m.name || m.id]));
			modelStats = (modelsRes?.models ?? []).map(
				(entry: Omit<(typeof modelStats)[number], 'name'>) => ({
					...entry,
					name: modelsMap.get(entry.model_id) || entry.model_id
				})
			);

			userStats = usersRes?.users ?? [];
			dailyStats = dailyRes?.data ?? [];

			// Process token data
			if (tokensRes) {
				tokenStats = {};
				for (const m of tokensRes.models) {
					tokenStats[m.model_id] = {
						input_tokens: m.input_tokens,
						output_tokens: m.output_tokens,
						total_tokens: m.total_tokens
					};
				}
				totalTokens = {
					input: tokensRes.total_input_tokens,
					output: tokensRes.total_output_tokens,
					total: tokensRes.total_tokens
				};
			}
		} catch (err) {
			console.error('Dashboard load failed:', err);
			if (id === loadId) loadError = true;
		} finally {
			if (id === loadId) loading = false;
		}
	};

	$: if (mounted && analyticsView === 'overview') {
		selectedPeriod;
		customStart;
		customEnd;
		selectedGroupId;
		selectedMetric;
		granularity;
		comparing;
		if (validRange) loadDashboard();
		else {
			++loadId;
			loading = false;
		}
	}

	onMount(async () => {
		mounted = true;
		// Load groups for filter
		try {
			const res = await getGroups(localStorage.token);
			groups = res ?? [];
		} catch (e) {
			console.error('Failed to load groups:', e);
		}
	});

	$: sortedModels = [...modelStats].sort((a, b) => {
		if (modelOrderBy === 'name') {
			return modelDirection === 'asc' ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name);
		}
		if (modelOrderBy === 'percentage') {
			const value = (m: (typeof modelStats)[number]) =>
				selectedMetric === 'tokens' ? (tokenStats[m.model_id]?.total_tokens ?? 0) : m.count;
			return modelDirection === 'asc' ? value(a) - value(b) : value(b) - value(a);
		}
		if (
			modelOrderBy === 'input_tokens' ||
			modelOrderBy === 'output_tokens' ||
			modelOrderBy === 'total_tokens'
		) {
			const aTokens = tokenStats[a.model_id]?.[modelOrderBy] ?? 0;
			const bTokens = tokenStats[b.model_id]?.[modelOrderBy] ?? 0;
			return modelDirection === 'asc' ? aTokens - bTokens : bTokens - aTokens;
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
		return modelDirection === 'asc' ? a.count - b.count : b.count - a.count;
	});

	$: sortedUsers = [...userStats].sort((a, b) => {
		if (userOrderBy === 'name') {
			const nameA = a.name || a.user_id;
			const nameB = b.name || b.user_id;
			return userDirection === 'asc' ? nameA.localeCompare(nameB) : nameB.localeCompare(nameA);
		}
		if (userOrderBy === 'percentage') {
			const aValue = selectedMetric === 'tokens' ? (a.total_tokens ?? 0) : a.count;
			const bValue = selectedMetric === 'tokens' ? (b.total_tokens ?? 0) : b.count;
			return userDirection === 'asc' ? aValue - bValue : bValue - aValue;
		}
		if (
			userOrderBy === 'input_tokens' ||
			userOrderBy === 'output_tokens' ||
			userOrderBy === 'total_tokens'
		) {
			const aTokens = a[userOrderBy] ?? 0;
			const bTokens = b[userOrderBy] ?? 0;
			return userDirection === 'asc' ? aTokens - bTokens : bTokens - aTokens;
		}
		return userDirection === 'asc' ? a.count - b.count : b.count - a.count;
	});

	$: metricLabel = selectedMetric === 'tokens' ? $i18n.t('Tokens') : $i18n.t('Messages');
	const selectMetric = (metric: 'tokens' | 'messages') => {
		selectedMetric = metric;
		modelOrderBy = userOrderBy = metric === 'tokens' ? 'total_tokens' : 'count';
		modelDirection = userDirection = 'desc';
	};

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

<div class="flex flex-wrap items-center justify-between mb-3 gap-x-4 gap-y-2">
	<h2 class="text-sm font-normal text-gray-900 dark:text-white shrink-0">
		{$i18n.t('Analytics')}
	</h2>
	<div class="flex items-center gap-2 flex-wrap justify-end min-w-0">
		{#if groups.length > 0}
			<select
				bind:value={selectedGroupId}
				aria-label={$i18n.t('User group')}
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
				aria-label={$i18n.t('Start date')}
				max={customEnd || undefined}
				class="w-fit rounded-sm px-2 text-xs bg-transparent outline-none dark:scheme-dark"
			/>
			<span class="text-xs text-gray-400">–</span>
			<input
				type="date"
				bind:value={customEnd}
				aria-label={$i18n.t('End date')}
				min={customStart || undefined}
				class="w-fit rounded-sm px-2 text-xs bg-transparent outline-none dark:scheme-dark"
			/>
		{/if}
		<select
			bind:value={selectedPeriod}
			aria-label={$i18n.t('Date range')}
			class="w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-none text-right"
		>
			{#each periods as period}
				<option value={period.value}>{period.label}</option>
			{/each}
		</select>
	</div>
</div>

<div class="flex items-center gap-4 mb-2.5" aria-label={$i18n.t('Analytics view')}>
	<button
		type="button"
		class="analytics-tab"
		class:tab-selected={analyticsView === 'overview'}
		aria-pressed={analyticsView === 'overview'}
		on:click={() => (analyticsView = 'overview')}>{$i18n.t('Overview')}</button
	>
	{#if $config?.features?.enable_admin_chat_access}
		<button
			type="button"
			class="analytics-tab"
			class:tab-selected={analyticsView === 'sessions'}
			aria-pressed={analyticsView === 'sessions'}
			on:click={() => (analyticsView = 'sessions')}>{$i18n.t('Sessions')}</button
		>
	{/if}
</div>

{#if analyticsView === 'sessions'}
	{#if validRange && $config?.features?.enable_admin_chat_access}
		<SessionExplorer scope={sessionScope} {modelNames} />
	{:else if !validRange}<p class="py-10 text-center text-xs text-gray-500">
			{$i18n.t('Choose a valid start and end date.')}
		</p>{/if}
{:else}
	<!-- Model Details Modal -->
	<AnalyticsModelModal
		bind:show={showModelModal}
		model={selectedModel}
		startDate={dateRange.start}
		endDate={dateRange.end}
		groupId={selectedGroupId}
	/>

	{#if !loading && !loadError && validRange}
		<dl
			class="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400"
		>
			{#each [{ label: $i18n.t('Tokens'), value: formatNumber(totalTokens.total), exact: totalTokens.total }, { label: $i18n.t('Input'), value: formatNumber(totalTokens.input), exact: totalTokens.input }, { label: $i18n.t('Output'), value: formatNumber(totalTokens.output), exact: totalTokens.output }, { label: $i18n.t('Messages'), value: summary.total_messages.toLocaleString(), exact: summary.total_messages }, { label: $i18n.t('Chats'), value: summary.total_chats.toLocaleString(), exact: summary.total_chats }, { label: $i18n.t('Users'), value: summary.total_users.toLocaleString(), exact: summary.total_users }] as metric}
				<div class="flex items-baseline gap-1.5 whitespace-nowrap">
					<dt>{metric.label}</dt>
					<dd
						class="tabular-nums text-gray-900 dark:text-gray-200"
						title={metric.exact.toLocaleString()}
					>
						{metric.value}
					</dd>
				</div>
			{/each}
		</dl>
		<section class="mt-3 min-w-0" aria-label={$i18n.t('Usage over time')}>
			<div class="mb-2 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 text-xs">
				<!-- Previous selector labels retained for i18n extraction: {$i18n.t('Chart metric')} -->
				<!-- {$i18n.t('10-Minute Messages')} {$i18n.t('Hourly Messages')} {$i18n.t('Daily Messages')} -->
				<!-- {$i18n.t('10-Minute Tokens')} {$i18n.t('Hourly Tokens')} {$i18n.t('Daily Tokens')} -->
				<div class="flex items-center gap-3" aria-label={$i18n.t('Usage metric')}>
					{#each [{ key: 'tokens', label: $i18n.t('Tokens') }, { key: 'messages', label: $i18n.t('Messages') }] as metric}
						<button
							type="button"
							class="analytics-tab"
							class:tab-selected={selectedMetric === metric.key}
							aria-pressed={selectedMetric === metric.key}
							on:click={() => selectMetric(metric.key as 'tokens' | 'messages')}
							>{metric.label}</button
						>
					{/each}
				</div>
				<div class="flex flex-wrap items-center gap-x-4 gap-y-1">
					{#if chartView === 'volume'}
						<button
							type="button"
							class="analytics-tab disabled:opacity-40 disabled:cursor-default"
							class:tab-selected={comparing}
							aria-pressed={comparing}
							disabled={selectedPeriod === 'all'}
							title={selectedPeriod === 'all'
								? $i18n.t('Choose a date range to compare')
								: $i18n.t('Compare to previous period')}
							on:click={() => (compare = !compare)}>{$i18n.t('Compare')}</button
						>
					{/if}
					<div class="flex items-center gap-3" aria-label={$i18n.t('Chart view')}>
						{#each [{ key: 'volume', label: $i18n.t('Volume') }, { key: 'activity', label: $i18n.t('Activity') }] as view}
							<button
								type="button"
								class="analytics-tab"
								class:tab-selected={chartView === view.key}
								aria-pressed={chartView === view.key}
								on:click={() => (chartView = view.key as 'volume' | 'activity')}
								>{view.label}</button
							>
						{/each}
					</div>
					<select
						bind:value={granularity}
						aria-label={$i18n.t('Chart interval')}
						class="w-fit pr-5 py-1 text-xs bg-transparent outline-none text-gray-500 dark:text-gray-400"
					>
						{#if selectedPeriod === '24h'}<option value="10m">{$i18n.t('10 min')}</option>{/if}
						{#if ['24h', '7d', '30d'].includes(selectedPeriod)}<option value="hourly"
								>{$i18n.t('Hourly')}</option
							>{/if}
						{#if selectedPeriod === '30d'}
							<option value="3h">{$i18n.t('3 hours')}</option>
							<option value="6h">{$i18n.t('6 hours')}</option>
						{/if}
						<option value="daily">{$i18n.t('Daily')}</option>
					</select>
				</div>
			</div>
			{#if dailyStats.length && (summary.total_messages > 0 || comparing)}
				<UsageChart
					data={dailyStats}
					compare={comparing}
					{granularity}
					{metricLabel}
					{modelNames}
					bind:selectedModel={chartModel}
					view={chartView}
				/>
			{:else}<div
					class="h-40 flex items-center justify-center text-xs text-gray-500 dark:text-gray-400"
				>
					{$i18n.t('No activity in this period')}
				</div>{/if}
		</section>
	{/if}

	{#if !validRange}
		<div class="my-10 text-center text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t('Choose a valid start and end date.')}
		</div>
	{:else if loadError}
		<div role="alert" class="my-10 text-center text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t('Unable to load analytics. Please try again.')}
			<button class="ml-2 underline underline-offset-2" on:click={loadDashboard}
				>{$i18n.t('Retry')}</button
			>
		</div>
	{:else if loading}
		<div class="my-10 flex justify-center">
			<Spinner className="size-5" />
		</div>
	{:else}
		<div class="mt-4 min-w-0">
			<div class="mb-2 flex items-center gap-3">
				<div class="flex items-center gap-3">
					{#each [{ key: 'models', label: $i18n.t('Models') }, { key: 'users', label: $i18n.t('Users') }] as tab}
						<button
							type="button"
							class="analytics-tab"
							class:tab-selected={selectedLeaderboard === tab.key}
							aria-pressed={selectedLeaderboard === tab.key}
							on:click={() => (selectedLeaderboard = tab.key)}>{tab.label}</button
						>
					{/each}
				</div>
			</div>
			<div class="min-w-0">
				{#if selectedLeaderboard === 'models'}
					<!-- Model Usage Table -->
					<!-- {$i18n.t('Model Usage')} -->
					<div>
						<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full">
							<table
								class="w-full text-xs tabular-nums text-left text-gray-500 dark:text-gray-400 table-auto"
							>
								<thead
									class="text-[0.6875rem] font-normal text-gray-500 bg-transparent dark:text-gray-400"
								>
									<tr>
										<th scope="col" class="font-normal px-2.5 py-1.5 w-8">#</th>
										<th
											scope="col"
											class="font-normal px-2.5 py-1.5 cursor-pointer select-none"
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
										<th
											scope="col"
											class="font-normal px-2.5 py-1.5 cursor-pointer select-none text-right"
											on:click={() => toggleModelSort('count')}
										>
											<div class="flex gap-1.5 items-center justify-end">
												{$i18n.t('Messages')}
												{#if modelOrderBy === 'count'}
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
										<th
											scope="col"
											class="font-normal px-2.5 py-1.5 cursor-pointer select-none text-right"
											on:click={() => toggleModelSort('users')}
										>
											<div class="flex gap-1.5 items-center justify-end">
												{$i18n.t('Users')}
												{#if modelOrderBy === 'users'}
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
										<th
											scope="col"
											class="font-normal px-2.5 py-1.5 cursor-pointer select-none text-right"
											on:click={() => toggleModelSort('chats')}
										>
											<div class="flex gap-1.5 items-center justify-end">
												{$i18n.t('Chats')}
												{#if modelOrderBy === 'chats'}
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
										<!-- {$i18n.t('Tokens')} -->
										{#each tokenColumns as column}
											<th
												scope="col"
												title={`${column.label} ${$i18n.t('tokens')}`}
												class="font-normal px-2.5 py-1.5 cursor-pointer select-none text-right"
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
											class="font-normal px-2.5 py-1.5 cursor-pointer select-none text-right w-16"
											on:click={() => toggleModelSort('percentage')}
										>
											<div class="flex gap-1.5 items-center justify-end">
												{selectedMetric === 'tokens'
													? $i18n.t('Token share')
													: $i18n.t('Message share')}
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
									{#each sortedModels as model, idx (model.model_id)}
										{@const value =
											selectedMetric === 'tokens'
												? (tokenStats[model.model_id]?.total_tokens ?? 0)
												: model.count}
										<tr
											class="text-xs cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
											on:click={() => {
												selectedModel = { id: model.model_id, name: model.name };
												showModelModal = true;
											}}
										>
											<td class="font-normal px-3 py-1.5 text-gray-400">{idx + 1}</td>
											<td class="font-normal px-3 py-1.5 text-gray-900 dark:text-white">
												<div class="flex items-center gap-2">
													<img
														src="{WEBUI_API_BASE_URL}/models/model/profile/image?id={model.model_id}"
														alt={model.name}
														class="size-5 rounded-full object-cover shrink-0"
														on:error={(e) => {
															// LICENSE covers this Open WebUI fallback logo.
															// Do not alter, remove, obscure, or replace it except as LICENSE permits:
															// https://docs.openwebui.com/license.
															const image = e.currentTarget as HTMLImageElement;
															if (!image.src.endsWith('/favicon.png')) image.src = '/favicon.png';
														}}
													/>
													<span class="truncate max-w-[9.375rem]">{model.name}</span>
												</div>
											</td>
											<td class="font-normal px-3 py-1.5 text-right"
												>{model.count.toLocaleString()}</td
											>
											<td class="font-normal px-3 py-1.5 text-right"
												>{(model.unique_users ?? 0).toLocaleString()}</td
											>
											<td class="font-normal px-3 py-1.5 text-right"
												>{(model.unique_chats ?? 0).toLocaleString()}</td
											>
											{#each tokenColumns as column}
												<td class="font-normal px-3 py-1.5 text-right"
													>{formatNumber(tokenStats[model.model_id]?.[column.key] ?? 0)}</td
												>
											{/each}
											<td class="font-normal px-3 py-1.5 text-right text-gray-400">
												<div class="flex items-center justify-end gap-2 tabular-nums">
													<div
														class="h-1 w-16 bg-gray-100 dark:bg-gray-800 overflow-hidden"
														aria-hidden="true"
													>
														<div
															class="h-full"
															style:background-color={modelColor(model.model_id)}
															style:width={`${metricTotal > 0 ? (value / metricTotal) * 100 : 0}%`}
														></div>
													</div>
													<span class="w-12">{usageShare(value, metricTotal)}</span>
												</div>
											</td>
										</tr>
									{/each}
									{#if sortedModels.length === 0}
										<tr
											><td colspan="9" class="font-normal px-3 py-1.5 text-center text-gray-400"
												>{$i18n.t('No data')}</td
											></tr
										>
									{/if}
								</tbody>
							</table>
						</div>
					</div>
				{:else}
					<!-- User Activity Table -->
					<!-- {$i18n.t('User Activity')} -->
					<div>
						<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full">
							<table
								class="w-full text-xs tabular-nums text-left text-gray-500 dark:text-gray-400 table-auto"
							>
								<thead
									class="text-[0.6875rem] font-normal text-gray-500 bg-transparent dark:text-gray-400"
								>
									<tr>
										<th scope="col" class="font-normal px-2.5 py-1.5 w-8">#</th>
										<th
											scope="col"
											class="font-normal px-2.5 py-1.5 cursor-pointer select-none"
											on:click={() => toggleUserSort('name')}
										>
											<div class="flex gap-1.5 items-center">
												{$i18n.t('User')}
												{#if userOrderBy === 'name'}
													<span class="font-normal">
														{#if userDirection === 'asc'}<ChevronUp
																className="size-2"
															/>{:else}<ChevronDown className="size-2" />{/if}
													</span>
												{:else}
													<span class="invisible"><ChevronUp className="size-2" /></span>
												{/if}
											</div>
										</th>
										<th
											scope="col"
											class="font-normal px-2.5 py-1.5 cursor-pointer select-none text-right"
											on:click={() => toggleUserSort('count')}
										>
											<div class="flex gap-1.5 items-center justify-end">
												{$i18n.t('Messages')}
												{#if userOrderBy === 'count'}
													<span class="font-normal">
														{#if userDirection === 'asc'}<ChevronUp
																className="size-2"
															/>{:else}<ChevronDown className="size-2" />{/if}
													</span>
												{:else}
													<span class="invisible"><ChevronUp className="size-2" /></span>
												{/if}
											</div>
										</th>
										<!-- {$i18n.t('Tokens')} -->
										{#each tokenColumns as column}
											<th
												scope="col"
												title={`${column.label} ${$i18n.t('tokens')}`}
												class="font-normal px-2.5 py-1.5 cursor-pointer select-none text-right"
												on:click={() => toggleUserSort(column.key)}
											>
												<div class="flex gap-1.5 items-center justify-end">
													{column.label}
													{#if userOrderBy === column.key}
														<span class="font-normal">
															{#if userDirection === 'asc'}<ChevronUp
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
											class="font-normal px-2.5 py-1.5 cursor-pointer select-none text-right w-16"
											on:click={() => toggleUserSort('percentage')}
										>
											<div class="flex gap-1.5 items-center justify-end">
												{selectedMetric === 'tokens'
													? $i18n.t('Token share')
													: $i18n.t('Message share')}
												{#if userOrderBy === 'percentage'}
													<span class="font-normal">
														{#if userDirection === 'asc'}<ChevronUp
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
									{#each sortedUsers as user, idx (user.user_id)}
										{@const value =
											selectedMetric === 'tokens' ? (user.total_tokens ?? 0) : user.count}
										<tr class="text-xs">
											<td class="font-normal px-3 py-1.5 text-gray-400">{idx + 1}</td>
											<td class="font-normal px-3 py-1.5 text-gray-900 dark:text-white">
												<div class="flex items-center gap-2">
													<ProfilePreview
														user={{ id: user.user_id, name: user.name || user.email }}
														side="right"
														align="center"
														sideOffset={6}
													>
														<img
															src="{WEBUI_API_BASE_URL}/users/{user.user_id}/profile/image"
															alt={user.name || 'User'}
															class="size-5 rounded-full object-cover shrink-0"
															on:error={(e) => {
																const image = e.currentTarget as HTMLImageElement;
																if (!image.src.endsWith('/user.png')) image.src = '/user.png';
															}}
														/>
													</ProfilePreview>
													<span class="truncate max-w-[9.375rem]"
														>{user.name || user.email || user.user_id.substring(0, 8)}</span
													>
												</div>
											</td>
											<td class="font-normal px-3 py-1.5 text-right"
												>{user.count.toLocaleString()}</td
											>
											{#each tokenColumns as column}
												<td class="font-normal px-3 py-1.5 text-right"
													>{formatNumber(user[column.key] ?? 0)}</td
												>
											{/each}

											<td class="font-normal px-3 py-1.5 text-right text-gray-400">
												<div class="flex items-center justify-end gap-2 tabular-nums">
													<div
														class="h-1 w-16 bg-gray-100 dark:bg-gray-800 overflow-hidden"
														aria-hidden="true"
													>
														<div
															class="h-full bg-gray-400"
															style:width={`${metricTotal > 0 ? (value / metricTotal) * 100 : 0}%`}
														></div>
													</div>
													<span class="w-12">{usageShare(value, metricTotal)}</span>
												</div>
											</td>
										</tr>
									{/each}
									{#if sortedUsers.length === 0}
										<tr
											><td colspan="7" class="font-normal px-3 py-1.5 text-center text-gray-400"
												>{$i18n.t('No data')}</td
											></tr
										>
									{/if}
								</tbody>
							</table>
						</div>
					</div>
				{/if}
			</div>
		</div>
		<div class="mt-2 text-[0.6875rem] text-gray-400 dark:text-gray-500">
			{$i18n.t('Message counts are based on assistant responses.')}
			{$i18n.t('Token counts are estimates and may not reflect actual API usage')}
		</div>
	{/if}
{/if}

<style>
	.analytics-tab {
		padding-block: 0.25rem;
		font-size: 0.75rem;
		font-weight: 400;
		color: var(--color-gray-500);
	}
	.analytics-tab:hover,
	.tab-selected {
		color: var(--color-gray-900);
	}
	:global(.dark) .analytics-tab {
		color: var(--color-gray-400);
	}
	:global(.dark) .analytics-tab:hover,
	:global(.dark) .tab-selected {
		color: var(--color-gray-100);
	}
</style>

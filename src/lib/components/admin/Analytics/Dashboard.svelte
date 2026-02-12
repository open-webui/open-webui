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
	import ChartLine from './ChartLine.svelte';
	import AnalyticsModelModal from './AnalyticsModelModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { formatNumber } from '$lib/utils';
	import { goto } from '$app/navigation';

	const i18n = getContext('i18n');

	// Time period - persist in localStorage
	let selectedPeriod =
		(typeof localStorage !== 'undefined' && localStorage.getItem('analyticsPeriod')) || '7d';
	const periods = [
		{ value: '24h', label: 'Last 24 hours' },
		{ value: '7d', label: 'Last 7 days' },
		{ value: '30d', label: 'Last 30 days' },
		{ value: '90d', label: 'Last 90 days' },
		{ value: 'all', label: 'All time' }
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
			default:
				return { start: null, end: null };
		}
	};

	// Data
	let summary = { total_messages: 0, total_chats: 0, total_models: 0, total_users: 0 };
	let modelStats: Array<{ model_id: string; count: number; name?: string }> = [];
	let userStats: Array<{ user_id: string; name?: string; email?: string; count: number }> = [];
	let dailyStats: Array<{ date: string; models: Record<string, number> }> = [];
	let tokenStats: Record<
		string,
		{ input_tokens: number; output_tokens: number; total_tokens: number }
	> = {};
	let totalTokens = { input: 0, output: 0, total: 0 };

	let loading = true;

	// Selected model for drill-down
	let selectedModel: { id: string; name: string } | null = null;
	let showModelModal = false;

	// Sorting
	let modelOrderBy = 'count';
	let modelDirection: 'asc' | 'desc' = 'desc';
	let userOrderBy = 'count';
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
		loading = true;
		try {
			const { start, end } = getDateRange(selectedPeriod);
			const granularity = selectedPeriod === '24h' ? 'hourly' : 'daily';
			const [summaryRes, modelsRes, usersRes, dailyRes, tokensRes] = await Promise.all([
				getSummary(localStorage.token, start, end, selectedGroupId),
				getModelAnalytics(localStorage.token, start, end, selectedGroupId),
				getUserAnalytics(localStorage.token, start, end, 50, selectedGroupId),
				getDailyStats(localStorage.token, start, end, granularity, selectedGroupId),
				getTokenUsage(localStorage.token, start, end, selectedGroupId)
			]);

			summary = summaryRes ?? summary;

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
		}
		loading = false;
	};

	$: if (selectedPeriod || selectedGroupId !== undefined) {
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

	$: sortedModels = [...modelStats].sort((a, b) => {
		if (modelOrderBy === 'name') {
			return modelDirection === 'asc' ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name);
		}
		return modelDirection === 'asc' ? a.count - b.count : b.count - a.count;
	});

	$: sortedUsers = [...userStats].sort((a, b) => {
		if (userOrderBy === 'name') {
			const nameA = a.name || a.user_id;
			const nameB = b.name || b.user_id;
			return userDirection === 'asc' ? nameA.localeCompare(nameB) : nameB.localeCompare(nameA);
		}
		return userDirection === 'asc' ? a.count - b.count : b.count - a.count;
	});

	$: totalModelMessages = modelStats.reduce((sum, m) => sum + m.count, 0);

	// Persist period selection
	$: if (typeof localStorage !== 'undefined' && selectedPeriod) {
		localStorage.setItem('analyticsPeriod', selectedPeriod);
	}

	onMount(loadDashboard);
</script>

<!-- Header with title and period selector -->
<div
	class="pt-0.5 pb-1 gap-1 flex flex-row justify-between items-center sticky top-0 z-10 bg-white dark:bg-gray-900"
>
	<div class="text-lg font-medium px-0.5">
		{$i18n.t('Analytics')}
	</div>
	<div class="flex items-center gap-2">
		{#if groups.length > 0}
			<select
				bind:value={selectedGroupId}
				class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-none text-right"
			>
				<option value={null}>{$i18n.t('All Users')}</option>
				{#each groups as group}
					<option value={group.id}>{group.name}</option>
				{/each}
			</select>
		{/if}
		<select
			bind:value={selectedPeriod}
			class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-none text-right"
		>
			{#each periods as period}
				<option value={period.value}>{$i18n.t(period.label)}</option>
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

<!-- Summary stats -->
{#if !loading}
	<div class="flex gap-3 text-xs text-gray-500 dark:text-gray-400 px-0.5 pb-2">
		<span
			><span class="font-medium text-gray-900 dark:text-gray-300"
				>{summary.total_messages.toLocaleString()}</span
			>
			{$i18n.t('messages')}</span
		>
		<Tooltip content={$i18n.t('Token counts are estimates and may not reflect actual API usage')}>
			<span class="cursor-help"
				><span class="font-medium text-gray-900 dark:text-gray-300"
					>{formatNumber(totalTokens.total)}</span
				>
				{$i18n.t('tokens')}</span
			>
		</Tooltip>
		<span
			><span class="font-medium text-gray-900 dark:text-gray-300"
				>{summary.total_chats.toLocaleString()}</span
			>
			{$i18n.t('chats')}</span
		>
		<span
			><span class="font-medium text-gray-900 dark:text-gray-300">{summary.total_users}</span>
			{$i18n.t('users')}</span
		>
	</div>

	<!-- Daily usage chart -->
	{#if dailyStats.length > 1}
		{@const allModels = [...new Set(dailyStats.flatMap((d) => Object.keys(d.models || {})))]}
		{@const topModels = allModels.slice(0, 8)}
		{@const chartColors = [
			'#3b82f6',
			'#10b981',
			'#f59e0b',
			'#ef4444',
			'#8b5cf6',
			'#ec4899',
			'#06b6d4',
			'#84cc16'
		]}
		{@const periodMap = { '24h': 'hour', '7d': 'week', '30d': 'month', '90d': 'year', all: 'all' }}
		<div class="mb-4">
			<div class="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2 px-0.5">
				{$i18n.t(selectedPeriod === '24h' ? 'Hourly Messages' : 'Daily Messages')}
			</div>
			<ChartLine
				data={dailyStats}
				models={topModels}
				colors={chartColors}
				height={200}
				period={periodMap[selectedPeriod] || 'week'}
			/>
		</div>
	{/if}
{/if}

{#if loading}
	<div class="my-10 flex justify-center">
		<Spinner className="size-5" />
	</div>
{:else}
	<div class="grid md:grid-cols-2 gap-4">
		<!-- Model Usage Table -->
		<div>
			<div class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 px-0.5">
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
							<th
								scope="col"
								class="px-2.5 py-2 cursor-pointer select-none text-right"
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
							<th scope="col" class="px-2.5 py-2 text-right">{$i18n.t('Tokens')}</th>
							<th scope="col" class="px-2.5 py-2 text-right w-16">%</th>
						</tr>
					</thead>
					<tbody>
						{#each sortedModels as model, idx (model.model_id)}
							<tr
								class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
								on:click={() => {
									selectedModel = { id: model.model_id, name: model.name };
									showModelModal = true;
								}}
							>
								<td class="px-3 py-1 text-gray-400">{idx + 1}</td>
								<td class="px-3 py-1 font-medium text-gray-900 dark:text-white">
									<div class="flex items-center gap-2">
										<img
											src="{WEBUI_API_BASE_URL}/models/model/profile/image?id={model.model_id}"
											alt={model.name}
											class="size-5 rounded-full object-cover shrink-0"
										/>
										<span class="truncate max-w-[150px]">{model.name}</span>
									</div>
								</td>
								<td class="px-3 py-1 text-right">{model.count.toLocaleString()}</td>
								<td class="px-3 py-1 text-right"
									>{formatNumber(tokenStats[model.model_id]?.total_tokens ?? 0)}</td
								>
								<td class="px-3 py-1 text-right text-gray-400">
									{totalModelMessages > 0
										? ((model.count / totalModelMessages) * 100).toFixed(1)
										: 0}%
								</td>
							</tr>
						{/each}
						{#if sortedModels.length === 0}
							<tr
								><td colspan="5" class="px-3 py-2 text-center text-gray-400"
									>{$i18n.t('No data')}</td
								></tr
							>
						{/if}
					</tbody>
				</table>
			</div>
		</div>

		<!-- User Activity Table -->
		<div>
			<div class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 px-0.5">
				{$i18n.t('User Activity')}
			</div>
			<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full">
				<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto">
					<thead class="text-xs text-gray-800 uppercase bg-transparent dark:text-gray-200">
						<tr class="border-b-[1.5px] border-gray-50 dark:border-gray-850/30">
							<th scope="col" class="px-2.5 py-2 w-8">#</th>
							<th
								scope="col"
								class="px-2.5 py-2 cursor-pointer select-none"
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
								class="px-2.5 py-2 cursor-pointer select-none text-right"
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
							<th scope="col" class="px-2.5 py-2 text-right">{$i18n.t('Tokens')}</th>
						</tr>
					</thead>
					<tbody>
						{#each sortedUsers as user, idx (user.user_id)}
							<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs">
								<td class="px-3 py-1 text-gray-400">{idx + 1}</td>
								<td class="px-3 py-1 font-medium text-gray-900 dark:text-white">
									<div class="flex items-center gap-2">
										<img
											src="{WEBUI_API_BASE_URL}/users/{user.user_id}/profile/image"
											alt={user.name || 'User'}
											class="size-5 rounded-full object-cover shrink-0"
										/>
										<span class="truncate max-w-[150px]"
											>{user.name || user.email || user.user_id.substring(0, 8)}</span
										>
									</div>
								</td>
								<td class="px-3 py-1 text-right">{user.count.toLocaleString()}</td>
								<td class="px-3 py-1 text-right">{formatNumber(user.total_tokens ?? 0)}</td>
							</tr>
						{/each}
						{#if sortedUsers.length === 0}
							<tr
								><td colspan="4" class="px-3 py-2 text-center text-gray-400"
									>{$i18n.t('No data')}</td
								></tr
							>
						{/if}
					</tbody>
				</table>
			</div>
		</div>
	</div>

	<div class="text-gray-500 text-xs mt-1.5 text-right">
		ⓘ {$i18n.t('Message counts are based on assistant responses.')}
	</div>
{/if}

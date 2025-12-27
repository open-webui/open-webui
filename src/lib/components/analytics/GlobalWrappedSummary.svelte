<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getGlobalWrapped, getGlobalModelUsage, formatTokenCount, type GlobalWrappedSummary, type ModelUsage } from '$lib/apis/analytics';

	const i18n = getContext('i18n');

	export let year: number | undefined = undefined;

	let loading = true;
	let error: string | null = null;
	let wrapped: GlobalWrappedSummary | null = null;
	let modelUsage: ModelUsage[] = [];

	// Colors for model leaderboard
	const MEDAL_COLORS = ['🥇', '🥈', '🥉'];

	onMount(async () => {
		await loadGlobalData();
	});

	async function loadGlobalData() {
		loading = true;
		error = null;

		try {
			const token = localStorage.getItem('token');
			if (!token) {
				error = 'Not authenticated';
				loading = false;
				return;
			}

			const [wrappedData, modelData] = await Promise.all([
				getGlobalWrapped(token, year),
				getGlobalModelUsage(token, 10)
			]);

			wrapped = wrappedData;
			modelUsage = modelData;
		} catch (e) {
			error = 'Error loading global data';
			console.error(e);
		}

		loading = false;
	}

	function getModelDisplayName(modelId: string): string {
		const parts = modelId.split('/');
		return parts[parts.length - 1] || modelId;
	}

	$: if (year !== undefined) {
		loadGlobalData();
	}
</script>

<div class="w-full">
	{#if loading}
		<div class="flex items-center justify-center py-16">
			<div class="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-500"></div>
		</div>
	{:else if error}
		<div class="text-center py-12 text-gray-500 dark:text-gray-400">
			{error}
		</div>
	{:else if wrapped}
		<!-- Hero Stats -->
		<div class="text-center mb-8">
			<h1 class="text-4xl md:text-5xl font-bold text-gray-900 dark:text-gray-100 mb-2">
				🌍 {wrapped.year} {$i18n.t('Global Wrapped')}
			</h1>
			<p class="text-gray-500 dark:text-gray-400">
				{$i18n.t("Site-wide AI usage statistics")}
			</p>
		</div>

		<!-- Main stats grid -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
			<!-- Total Tokens -->
			<div class="bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-2xl p-6 text-white">
				<div class="text-3xl md:text-4xl font-bold mb-1">
					{formatTokenCount(wrapped.total_tokens)}
				</div>
				<div class="text-emerald-100 text-sm">
					{$i18n.t('Total Tokens')}
				</div>
			</div>

			<!-- Active Users -->
			<div class="bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl p-6 text-white">
				<div class="text-3xl md:text-4xl font-bold mb-1">
					{wrapped.total_users_active.toLocaleString()}
				</div>
				<div class="text-blue-100 text-sm">
					{$i18n.t('Active Users')}
				</div>
			</div>

			<!-- Conversations -->
			<div class="bg-gradient-to-br from-violet-500 to-violet-600 rounded-2xl p-6 text-white">
				<div class="text-3xl md:text-4xl font-bold mb-1">
					{wrapped.total_conversations.toLocaleString()}
				</div>
				<div class="text-violet-100 text-sm">
					{$i18n.t('Conversations')}
				</div>
			</div>

			<!-- Messages -->
			<div class="bg-gradient-to-br from-pink-500 to-pink-600 rounded-2xl p-6 text-white">
				<div class="text-3xl md:text-4xl font-bold mb-1">
					{wrapped.total_messages.toLocaleString()}
				</div>
				<div class="text-pink-100 text-sm">
					{$i18n.t('Messages')}
				</div>
			</div>
		</div>

		<!-- Busiest Day -->
		{#if wrapped.busiest_day}
			<div class="bg-gray-50 dark:bg-gray-850 rounded-2xl p-6 mb-8">
				<div class="flex items-center gap-3 mb-3">
					<div class="p-2 bg-orange-100 dark:bg-orange-900 rounded-lg">
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="size-6 text-orange-600 dark:text-orange-400">
							<path fill-rule="evenodd" d="M12.963 2.286a.75.75 0 0 0-1.071-.136 9.742 9.742 0 0 0-3.539 6.176 7.547 7.547 0 0 1-1.705-1.715.75.75 0 0 0-1.152-.082A9 9 0 1 0 15.68 4.534a7.46 7.46 0 0 1-2.717-2.248ZM15.75 14.25a3.75 3.75 0 1 1-7.313-1.172c.628.465 1.35.81 2.133 1a5.99 5.99 0 0 1 1.925-3.546 3.75 3.75 0 0 1 3.255 3.718Z" clip-rule="evenodd" />
						</svg>
					</div>
					<div>
						<h4 class="font-semibold text-gray-900 dark:text-gray-100">
							{$i18n.t('Busiest Day')}
						</h4>
						<p class="text-sm text-gray-500 dark:text-gray-400">
							{wrapped.busiest_day.day_of_week}
						</p>
					</div>
				</div>
				<div class="text-2xl font-bold text-orange-600 dark:text-orange-400">
					{formatTokenCount(wrapped.busiest_day.tokens)} {$i18n.t('tokens')}
				</div>
				<div class="text-sm text-gray-500 dark:text-gray-400">
					{new Date(wrapped.busiest_day.date).toLocaleDateString(undefined, { 
						year: 'numeric',
						month: 'long', 
						day: 'numeric' 
					})}
				</div>
			</div>
		{/if}

		<!-- Model Leaderboard -->
		{#if modelUsage.length > 0}
			<div class="bg-gray-50 dark:bg-gray-850 rounded-2xl p-6">
				<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
					🏆 {$i18n.t('Model Leaderboard')}
				</h3>
				<div class="space-y-3">
					{#each modelUsage as model, index}
						<div class="flex items-center gap-4 p-3 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700">
							<div class="text-2xl flex-shrink-0 w-8 text-center">
								{#if index < 3}
									{MEDAL_COLORS[index]}
								{:else}
									<span class="text-gray-400 text-lg">#{index + 1}</span>
								{/if}
							</div>
							<div class="flex-1 min-w-0">
								<div class="font-medium text-gray-900 dark:text-gray-100 truncate">
									{getModelDisplayName(model.model_id)}
								</div>
								<div class="text-sm text-gray-500 dark:text-gray-400">
									{model.conversation_count.toLocaleString()} {$i18n.t('conversations')}
								</div>
							</div>
							<div class="text-right flex-shrink-0">
								<div class="font-bold text-emerald-600 dark:text-emerald-400">
									{formatTokenCount(model.total_tokens)}
								</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">
									{model.percentage.toFixed(1)}%
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Top Models from wrapped -->
		{#if wrapped.top_models && wrapped.top_models.length > 0}
			<!-- Already showing model leaderboard above -->
		{/if}
	{:else}
		<div class="text-center py-12 text-gray-500 dark:text-gray-400">
			{$i18n.t('No global data available')}
		</div>
	{/if}
</div>

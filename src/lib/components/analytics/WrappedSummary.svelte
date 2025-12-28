<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getUserWrapped, formatTokenCount, type WrappedSummary } from '$lib/apis/analytics';

	const i18n = getContext('i18n');

	export let year: number | undefined = undefined;

	let loading = true;
	let error: string | null = null;
	let wrapped: WrappedSummary | null = null;

	onMount(async () => {
		await loadWrappedData();
	});

	async function loadWrappedData() {
		loading = true;
		error = null;

		try {
			const token = localStorage.getItem('token');
			if (!token) {
				error = 'Not authenticated';
				loading = false;
				return;
			}

			wrapped = await getUserWrapped(token, year);
		} catch (e) {
			error = 'Error loading wrapped data';
			console.error(e);
		}

		loading = false;
	}

	function getTimeOfDay(date: string): string {
		// Just return the day of week for now since we track by day
		return '';
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
				{wrapped.year} {$i18n.t('Wrapped')}
			</h1>
			<p class="text-gray-500 dark:text-gray-400">
				{$i18n.t("Your AI conversation statistics")}
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

			<!-- Conversations -->
			<div class="bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl p-6 text-white">
				<div class="text-3xl md:text-4xl font-bold mb-1">
					{wrapped.total_conversations.toLocaleString()}
				</div>
				<div class="text-blue-100 text-sm">
					{$i18n.t('Conversations')}
				</div>
			</div>

			<!-- Messages -->
			<div class="bg-gradient-to-br from-violet-500 to-violet-600 rounded-2xl p-6 text-white">
				<div class="text-3xl md:text-4xl font-bold mb-1">
					{wrapped.total_messages.toLocaleString()}
				</div>
				<div class="text-violet-100 text-sm">
					{$i18n.t('Messages')}
				</div>
			</div>

			<!-- Days Active -->
			<div class="bg-gradient-to-br from-amber-500 to-amber-600 rounded-2xl p-6 text-white">
				<div class="text-3xl md:text-4xl font-bold mb-1">
					{wrapped.days_active}
				</div>
				<div class="text-amber-100 text-sm">
					{$i18n.t('Days Active')}
				</div>
			</div>
		</div>

		<!-- Input/Output breakdown -->
		<div class="bg-gray-50 dark:bg-gray-850 rounded-2xl p-6 mb-8">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
				{$i18n.t('Token Breakdown')}
			</h3>
			<div class="flex items-center gap-4">
				<!-- Input bar -->
				<div class="flex-1">
					<div class="flex items-center justify-between mb-2">
						<span class="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-1">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4 text-blue-500">
								<path fill-rule="evenodd" d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z" clip-rule="evenodd" />
							</svg>
							{$i18n.t('Input')}
						</span>
						<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
							{formatTokenCount(wrapped.total_input_tokens)}
						</span>
					</div>
					<div class="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
						<div 
							class="h-full bg-blue-500 rounded-full transition-all duration-500"
							style="width: {wrapped.total_tokens > 0 ? (wrapped.total_input_tokens / wrapped.total_tokens * 100) : 0}%"
						></div>
					</div>
				</div>
				
				<!-- Output bar -->
				<div class="flex-1">
					<div class="flex items-center justify-between mb-2">
						<span class="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-1">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4 text-green-500">
								<path fill-rule="evenodd" d="M8 2a.75.75 0 0 1 .75.75v8.69l3.22-3.22a.75.75 0 1 1 1.06 1.06l-4.5 4.5a.75.75 0 0 1-1.06 0l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.22 3.22V2.75A.75.75 0 0 1 8 2Z" clip-rule="evenodd" />
							</svg>
							{$i18n.t('Output')}
						</span>
						<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
							{formatTokenCount(wrapped.total_output_tokens)}
						</span>
					</div>
					<div class="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
						<div 
							class="h-full bg-green-500 rounded-full transition-all duration-500"
							style="width: {wrapped.total_tokens > 0 ? (wrapped.total_output_tokens / wrapped.total_tokens * 100) : 0}%"
						></div>
					</div>
				</div>
			</div>
		</div>

		<!-- Highlights -->
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
			<!-- Most Active Day -->
			{#if wrapped.most_active_day}
				<div class="bg-gray-50 dark:bg-gray-850 rounded-2xl p-6">
					<div class="flex items-center gap-3 mb-3">
						<div class="p-2 bg-orange-100 dark:bg-orange-900 rounded-lg">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="size-6 text-orange-600 dark:text-orange-400">
								<path fill-rule="evenodd" d="M12.963 2.286a.75.75 0 0 0-1.071-.136 9.742 9.742 0 0 0-3.539 6.176 7.547 7.547 0 0 1-1.705-1.715.75.75 0 0 0-1.152-.082A9 9 0 1 0 15.68 4.534a7.46 7.46 0 0 1-2.717-2.248ZM15.75 14.25a3.75 3.75 0 1 1-7.313-1.172c.628.465 1.35.81 2.133 1a5.99 5.99 0 0 1 1.925-3.546 3.75 3.75 0 0 1 3.255 3.718Z" clip-rule="evenodd" />
							</svg>
						</div>
						<div>
							<h4 class="font-semibold text-gray-900 dark:text-gray-100">
								{$i18n.t('Most Active Day')}
							</h4>
							<p class="text-sm text-gray-500 dark:text-gray-400">
								{wrapped.most_active_day.day_of_week}
							</p>
						</div>
					</div>
					<div class="text-2xl font-bold text-orange-600 dark:text-orange-400">
						{formatTokenCount(wrapped.most_active_day.tokens)} {$i18n.t('tokens')}
					</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">
						{new Date(wrapped.most_active_day.date).toLocaleDateString(undefined, { 
							year: 'numeric',
							month: 'long', 
							day: 'numeric' 
						})}
					</div>
				</div>
			{/if}

			<!-- Favorite Model -->
			{#if wrapped.favorite_model}
				<div class="bg-gray-50 dark:bg-gray-850 rounded-2xl p-6">
					<div class="flex items-center gap-3 mb-3">
						<div class="p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="size-6 text-purple-600 dark:text-purple-400">
								<path fill-rule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z" clip-rule="evenodd" />
							</svg>
						</div>
						<div>
							<h4 class="font-semibold text-gray-900 dark:text-gray-100">
								{$i18n.t('Favorite Model')}
							</h4>
							<p class="text-sm text-gray-500 dark:text-gray-400">
								{wrapped.favorite_model.percentage.toFixed(1)}% {$i18n.t('of usage')}
							</p>
						</div>
					</div>
					<div class="text-lg font-bold text-purple-600 dark:text-purple-400 truncate">
						{wrapped.favorite_model.model_id.split('/').pop() || wrapped.favorite_model.model_id}
					</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">
						{formatTokenCount(wrapped.favorite_model.total_tokens)} {$i18n.t('tokens')}
					</div>
				</div>
			{/if}
		</div>
	{:else}
		<div class="text-center py-12 text-gray-500 dark:text-gray-400">
			{$i18n.t('No data available')}
		</div>
	{/if}
</div>

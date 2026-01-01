<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';

	import GlobalWrappedSummary from '$lib/components/analytics/GlobalWrappedSummary.svelte';
	import GlobalActivityHeatmap from '$lib/components/analytics/GlobalActivityHeatmap.svelte';

	const i18n = getContext('i18n');

	// Get current year by default
	let selectedYear: number = new Date().getFullYear();
	
	// Generate available years
	const currentYear = new Date().getFullYear();
	const availableYears = Array.from({ length: 5 }, (_, i) => currentYear - i);

	onMount(() => {
		// Redirect if not admin
		if (!$user || $user.role !== 'admin') {
			goto('/');
		}
	});
</script>

<svelte:head>
	<title>Global {selectedYear} Wrapped | Admin | Open WebUI</title>
</svelte:head>

<div class="min-h-screen bg-white dark:bg-gray-900">
	<!-- Header with gradient -->
	<div class="bg-gradient-to-br from-purple-600 via-indigo-600 to-blue-600 pt-8 pb-12 px-4">
		<div class="max-w-5xl mx-auto">
			<div class="flex items-center justify-between mb-6">
				<button
					class="flex items-center gap-2 text-white/80 hover:text-white transition-colors"
					on:click={() => goto('/admin')}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-5">
						<path fill-rule="evenodd" d="M17 10a.75.75 0 0 1-.75.75H5.612l4.158 3.96a.75.75 0 1 1-1.04 1.08l-5.5-5.25a.75.75 0 0 1 0-1.08l5.5-5.25a.75.75 0 1 1 1.04 1.08L5.612 9.25H16.25A.75.75 0 0 1 17 10Z" clip-rule="evenodd" />
					</svg>
					{$i18n.t('Back to Admin')}
				</button>

				<!-- Year Selector -->
				<div class="flex items-center gap-2">
					<label for="year-select" class="text-sm text-white/80">
						{$i18n.t('Year')}:
					</label>
					<select
						id="year-select"
						bind:value={selectedYear}
						class="bg-white/20 text-white border border-white/30 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-white/50 cursor-pointer"
					>
						{#each availableYears as year}
							<option value={year} class="text-gray-900">{year}</option>
						{/each}
					</select>
				</div>
			</div>

			<div class="flex items-center justify-center gap-2 mb-2">
				<span class="px-3 py-1 bg-white/20 text-white text-xs font-medium rounded-full">
					{$i18n.t('Admin Only')}
				</span>
			</div>

			<h1 class="text-4xl md:text-5xl font-bold text-white text-center mb-2">
				🌍 {$i18n.t('Global')} {selectedYear} {$i18n.t('Wrapped')}
			</h1>
			<p class="text-white/80 text-center">
				{$i18n.t('Site-wide AI usage statistics across all users')}
			</p>
		</div>
	</div>

	<!-- Main content -->
	<div class="max-w-5xl mx-auto px-4 -mt-6">
		<div class="bg-white dark:bg-gray-900 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-800 p-6 md:p-8">
			{#key selectedYear}
				<!-- Global Wrapped Summary -->
				<GlobalWrappedSummary year={selectedYear} />

				<!-- Global Activity Heatmap -->
				<div class="mt-10 pt-8 border-t border-gray-200 dark:border-gray-800">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
						📊 {$i18n.t('Global Activity Heatmap')}
					</h2>
					<GlobalActivityHeatmap year={selectedYear} />
				</div>
			{/key}
		</div>

		<!-- Footer -->
		<div class="text-center py-8">
			<p class="text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('Powered by')} Open WebUI Token Analytics
			</p>
			<button
				class="mt-2 text-sm text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 underline transition-colors"
				on:click={() => goto('/wrapped')}
			>
				← {$i18n.t('View Your Personal Wrapped')}
			</button>
		</div>
	</div>
</div>

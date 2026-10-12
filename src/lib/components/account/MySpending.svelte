<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { user } from '$lib/stores';

	const i18n = getContext('i18n');

	let loading = true;
	let error: string | null = null;
	let mySpending: any = null;
	let modelCosts: any = null;

	async function fetchMySpending() {
		loading = true;
		error = null;
		try {
			const res = await fetch('/api/v1/spending/me', {
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});
			if (!res.ok) {
				const text = await res.text();
				throw new Error(text || `HTTP ${res.status}`);
			}
			mySpending = await res.json();
		} catch (e: any) {
			error = e.message || 'Failed to load spending data';
			toast.error(error);
		} finally {
			loading = false;
		}
	}

	async function fetchModelCosts() {
		try {
			const res = await fetch('/api/v1/spending/models', {
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});
			if (!res.ok) {
				const text = await res.text();
				throw new Error(text || `HTTP ${res.status}`);
			}
			modelCosts = await res.json();
		} catch (e: any) {
			console.error('Failed to load model costs:', e.message || e);
			// Don't toast here — non-critical, don't block the main spending view
		}
	}

	function loadData() {
		fetchMySpending();
		fetchModelCosts();
	}

	onMount(() => {
		loadData();
	});

	function getUsagePercentColor(percent: number) {
		if (percent >= 100) return 'text-red-600 dark:text-red-400';
		if (percent >= 80) return 'text-yellow-600 dark:text-yellow-400';
		return 'text-green-600 dark:text-green-400';
	}

	function getBarColor(percent: number) {
		if (percent >= 100) return 'bg-red-500';
		if (percent >= 80) return 'bg-yellow-500';
		return 'bg-green-500';
	}

	function safePercent(val: any): number {
		const n = typeof val === 'number' ? val : parseFloat(val);
		return isNaN(n) ? 0 : n;
	}
</script>

<div class="flex flex-col w-full h-full px-4 py-4">
	<h1 class="text-xl font-semibold dark:text-white mb-4">My Spending</h1>

	{#if loading}
		<div class="flex items-center justify-center h-40">
			<div
				class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"
			></div>
		</div>
	{:else if error}
		<!-- Error State -->
		<div class="flex flex-col items-center justify-center h-64 text-center">
			<div class="text-red-500 mb-2">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="size-10 mx-auto"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
					/>
				</svg>
			</div>
			<p class="text-gray-600 dark:text-gray-300 mb-4">{error}</p>
			<button
				class="px-4 py-2 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-lg hover:opacity-90 transition"
				on:click={loadData}
			>
				Retry
			</button>
		</div>
	{:else if mySpending}
		{@const pct = safePercent(mySpending.usage_percent)}
		<!-- Summary Cards -->
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
			<div
				class="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700"
			>
				<div class="text-sm text-gray-500 dark:text-gray-400">Spent This Month</div>
				<div class="text-2xl font-bold text-gray-900 dark:text-white">
					${mySpending.spent?.toFixed(2) ?? '0.00'}
				</div>
			</div>
			<div
				class="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700"
			>
				<div class="text-sm text-gray-500 dark:text-gray-400">Monthly Limit</div>
				<div class="text-2xl font-bold text-gray-900 dark:text-white">
					${mySpending.limit?.toFixed(2) ?? '0.00'}
				</div>
			</div>
			<div
				class="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700"
			>
				<div class="text-sm text-gray-500 dark:text-gray-400">Remaining</div>
				<div class="text-2xl font-bold {getUsagePercentColor(pct)}">
					${mySpending.remaining?.toFixed(2) ?? '0.00'}
				</div>
			</div>
		</div>

		<!-- Progress Bar -->
		<div
			class="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 mb-6"
		>
			<div class="flex justify-between text-sm mb-2">
				<span class="text-gray-600 dark:text-gray-400">Usage</span>
				<span class="{getUsagePercentColor(pct)} font-medium">{pct.toFixed(1)}%</span>
			</div>
			<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
				<div
					class="h-2.5 rounded-full transition-all {getBarColor(pct)}"
					style="width: {Math.min(pct, 100)}%"
				></div>
			</div>
			{#if pct >= 100}
				<div class="mt-2 text-sm text-red-600 dark:text-red-400">
					Your monthly budget has been exceeded. Contact your admin for assistance.
				</div>
			{:else if pct >= 80}
				<div class="mt-2 text-sm text-yellow-600 dark:text-yellow-400">
					Warning: You're approaching your monthly budget limit.
				</div>
			{/if}
		</div>

		<!-- Period Info -->
		<div class="text-sm text-gray-500 dark:text-gray-400 mb-6">
			Billing period: {mySpending.month ?? '—'} (IST timezone)
		</div>
	{:else}
		<!-- Empty / Unexpected State -->
		<div class="flex flex-col items-center justify-center h-40 text-center">
			<p class="text-gray-500 dark:text-gray-400 mb-4">No spending data available.</p>
			<button
				class="px-4 py-2 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-lg hover:opacity-90 transition"
				on:click={loadData}
			>
				Refresh
			</button>
		</div>
	{/if}

	<!-- Model Pricing -->
	{#if modelCosts && modelCosts.models && modelCosts.models.length > 0}
		<div
			class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
		>
			<div
				class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 font-medium dark:text-white"
			>
				Model Pricing
			</div>
			<div class="overflow-x-auto">
				<table class="w-full text-sm">
					<thead>
						<tr class="bg-gray-50 dark:bg-gray-700/50 text-left">
							<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Model</th>
							<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Tier</th>
							<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Price</th>
						</tr>
					</thead>
					<tbody>
						{#each modelCosts.models.slice(0, 15) as m}
							<tr class="border-t border-gray-100 dark:border-gray-700/50">
								<td class="px-4 py-2 dark:text-gray-200 font-medium">{m.model_id ?? '—'}</td>
								<td class="px-4 py-2">
									<span
										class="px-2 py-0.5 rounded-full text-xs font-medium"
										style="background-color: {m.color ?? '#6b7280'}20; color: {m.color ??
											'#6b7280'}"
									>
										{m.tier ?? 'Unknown'}
									</span>
								</td>
								<td class="px-4 py-2 dark:text-gray-200 text-sm">
									{#if m.input_price_per_1m !== undefined && m.input_price_per_1m !== null}
										${m.input_price_per_1m}/1M in + ${m.output_price_per_1m ?? '?'}/1M out
									{:else if m.price_per_image}
										${m.price_per_image}/image
									{:else if m.price_per_1m_chars}
										${m.price_per_1m_chars}/1M chars
									{:else if m.price_per_minute}
										${m.price_per_minute}/min
									{:else}
										—
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{:else if !loading && !error}
		<div class="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
			Model pricing data unavailable.
		</div>
	{/if}
</div>

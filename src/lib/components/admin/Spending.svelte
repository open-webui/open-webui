<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let loading = true;
	let error: string | null = null;
	let spendingData: any = null;
	let modelCosts: any = null;
	let trendData: any = null;
	let selectedMonth = '';
	let editUserId: string | null = null;
	let newLimit = 0;
	let trendMonths = 6;

	const months: string[] = [];
	const now = new Date();
	for (let i = 0; i < 12; i++) {
		const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
		months.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
	}
	selectedMonth = months[0];

	async function fetchSpending() {
		loading = true;
		error = null;
		try {
			const res = await fetch(`/api/v1/spending?month=${selectedMonth}`, {
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});
			if (!res.ok) {
				const text = await res.text();
				throw new Error(text || `HTTP ${res.status}`);
			}
			spendingData = await res.json();
		} catch (e: any) {
			error = e.message || 'Failed to load spending';
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
		}
	}

	async function fetchTrends() {
		try {
			const res = await fetch(`/api/v1/spending/trends?months=${trendMonths}`, {
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});
			if (!res.ok) {
				const text = await res.text();
				throw new Error(text || `HTTP ${res.status}`);
			}
			trendData = await res.json();
		} catch (e: any) {
			console.error('Failed to load trends:', e.message || e);
		}
	}

	async function updateLimit(userId: string) {
		try {
			const res = await fetch(`/api/v1/spending/${userId}`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({ monthly_limit_usd: newLimit })
			});
			if (!res.ok) {
				const text = await res.text();
				throw new Error(text || `HTTP ${res.status}`);
			}
			const data = await res.json();
			toast.success(data.message);
			editUserId = null;
			await fetchSpending();
		} catch (e: any) {
			toast.error(e.message || 'Failed to update limit');
		}
	}

	function loadData() {
		fetchSpending();
		fetchModelCosts();
		fetchTrends();
	}

	onMount(() => {
		loadData();
	});

	// Chart helpers
	function getChartBars() {
		if (!trendData?.totals) return [];
		const maxVal = Math.max(...trendData.totals.map((t: any) => t.total_spent || 0), 1);
		return trendData.totals.map((t: any) => ({
			month: t.month.slice(5), // Show MM only
			spent: t.total_spent || 0,
			limit: t.total_limit || 0,
			height: Math.max((t.total_spent / maxVal) * 100, 4),
			color: (t.total_spent / (t.total_limit || 1)) >= 0.8 ? '#ef4444' : '#3b82f6'
		}));
	}
</script>

<div class="flex flex-col w-full h-full px-4 py-4">
	<div class="flex items-center justify-between mb-4">
		<h1 class="text-xl font-semibold dark:text-white">Spending Dashboard</h1>
		<select
			bind:value={selectedMonth}
			on:change={fetchSpending}
			class="px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-800 dark:text-white border border-gray-200 dark:border-gray-700"
		>
			{#each months as m}
				<option value={m}>{m}</option>
			{/each}
		</select>
	</div>

	{#if loading}
		<div class="flex items-center justify-center h-40">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"></div>
		</div>
	{:else if error}
		<div class="flex flex-col items-center justify-center h-64 text-center">
			<div class="text-red-500 mb-2">
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-10 mx-auto">
					<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
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
	{:else if spendingData}
		<!-- Summary Cards -->
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
			<div class="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
				<div class="text-sm text-gray-500 dark:text-gray-400">Total Spent</div>
				<div class="text-2xl font-bold text-gray-900 dark:text-white">${spendingData.total_spent?.toFixed(2) || '0.00'}</div>
			</div>
			<div class="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
				<div class="text-sm text-gray-500 dark:text-gray-400">Active Users</div>
				<div class="text-2xl font-bold text-gray-900 dark:text-white">{spendingData.users?.length || 0}</div>
			</div>
			<div class="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
				<div class="text-sm text-gray-500 dark:text-gray-400">Period</div>
				<div class="text-2xl font-bold text-gray-900 dark:text-white">{spendingData.month}</div>
			</div>
		</div>

		<!-- Spending Trends Chart -->
		{#if trendData}
			<div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 mb-6">
				<div class="flex items-center justify-between mb-4">
					<h2 class="font-medium dark:text-white">Spending Trends (Last {trendMonths} Months)</h2>
					<select
						bind:value={trendMonths}
						on:change={fetchTrends}
						class="px-2 py-1 text-sm rounded bg-gray-100 dark:bg-gray-700 dark:text-white border border-gray-200 dark:border-gray-600"
					>
						<option value={3}>3 months</option>
						<option value={6}>6 months</option>
						<option value={12}>12 months</option>
					</select>
				</div>
				<div class="h-48 flex items-end gap-2 px-2">
					{#each getChartBars() as bar}
						<div class="flex-1 flex flex-col items-center gap-1">
							<div class="text-xs text-gray-500 dark:text-gray-400">${bar.spent.toFixed(0)}</div>
							<div
								class="w-full rounded-t transition-all hover:opacity-80"
								style="height: {bar.height}%; background-color: {bar.color}; min-height: 4px;"
								title="{bar.month}: ${bar.spent.toFixed(2)} / ${bar.limit.toFixed(2)}"
							></div>
							<div class="text-xs text-gray-500 dark:text-gray-400">{bar.month}</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Users Table -->
		<div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
			<div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 font-medium dark:text-white">
				User Spending Details
			</div>
			<div class="overflow-x-auto">
				<table class="w-full text-sm">
					<thead>
						<tr class="bg-gray-50 dark:bg-gray-700/50 text-left">
							<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">User</th>
							<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Role</th>
							<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Spent</th>
							<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Limit</th>
							<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Remaining</th>
							<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Actions</th>
						</tr>
					</thead>
					<tbody>
						{#each spendingData.users || [] as u}
							<tr class="border-t border-gray-100 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30">
								<td class="px-4 py-2 dark:text-gray-200">
									<div class="font-medium">{u.name || 'Unknown'}</div>
									<div class="text-xs text-gray-500">{u.email || u.user_id}</div>
								</td>
								<td class="px-4 py-2">
									<span class="px-2 py-0.5 rounded-full text-xs font-medium {u.role === 'admin' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300' : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'}">
										{u.role || 'user'}
									</span>
								</td>
								<td class="px-4 py-2 dark:text-gray-200">${u.spent?.toFixed(2) ?? '0.00'}</td>
								<td class="px-4 py-2 dark:text-gray-200">${u.limit?.toFixed(2) ?? '0.00'}</td>
								<td class="px-4 py-2">
									<span class="{(u.remaining ?? 0) < 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}">
										${u.remaining?.toFixed(2) ?? '0.00'}
									</span>
								</td>
								<td class="px-4 py-2">
									{#if editUserId === u.user_id}
										<div class="flex gap-1">
											<input
												type="number"
												bind:value={newLimit}
												class="w-20 px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
												placeholder="Limit"
											/>
											<button
												on:click={() => updateLimit(u.user_id)}
												class="px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
											>
												Save
											</button>
											<button
												on:click={() => { editUserId = null; }}
												class="px-2 py-1 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200 text-xs rounded"
											>
												Cancel
											</button>
										</div>
									{:else}
										<button
											on:click={() => { editUserId = u.user_id; newLimit = u.limit; }}
											class="text-blue-600 dark:text-blue-400 text-xs hover:underline"
										>
											Edit Limit
										</button>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}

	<!-- Model Pricing -->
	{#if modelCosts && modelCosts.models}
		<div class="mt-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
			<div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 font-medium dark:text-white">
				Model Pricing Catalogue
			</div>
			<div class="overflow-x-auto">
				<table class="w-full text-sm">
					<thead>
						<tr class="bg-gray-50 dark:bg-gray-700/50 text-left">
							<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Model</th>
							<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Tier</th>
							<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Type</th>
							<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Price</th>
						</tr>
					</thead>
					<tbody>
						{#each modelCosts.models.slice(0, 20) as m}
							<tr class="border-t border-gray-100 dark:border-gray-700/50">
								<td class="px-4 py-2 dark:text-gray-200 font-medium">{m.model_id ?? '—'}</td>
								<td class="px-4 py-2">
									<span class="px-2 py-0.5 rounded-full text-xs font-medium" style="background-color: {m.color ?? '#6b7280'}20; color: {m.color ?? '#6b7280'}">
										{m.tier ?? 'Unknown'}
									</span>
								</td>
								<td class="px-4 py-2 text-gray-500 dark:text-gray-400">{m.price_type ?? '—'}</td>
								<td class="px-4 py-2 dark:text-gray-200">
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
	{/if}
</div>

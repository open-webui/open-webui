<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';

	export let planName = '';
	export let planDescription = '';

	async function handleUpgrade() {
		const res = await fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/billing/checkout`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ plan: 'pro' })
		});
		const data = await res.json();
		if (data.url) window.location.href = data.url;
	}

	async function handleBuyTokens() {
		const res = await fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/billing/token-addon`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ amount: 100000 })
		});
		const data = await res.json();
		if (data.url) window.location.href = data.url;
	}
</script>

<div class="p-5 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
	<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">Plan actual</h3>

	<div class="mb-3">
		<span
			class="inline-flex px-2.5 py-1 rounded-lg bg-claw-100 dark:bg-claw-900/30 text-claw-700 dark:text-claw-400 text-sm font-semibold"
		>
			{planName || 'Free'}
		</span>
	</div>

	{#if planDescription}
		<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">{planDescription}</p>
	{/if}

	<div class="flex gap-2">
		<button
			class="flex-1 px-3 py-2 rounded-lg bg-claw-500 hover:bg-claw-600 text-white text-sm font-medium transition"
			on:click={handleUpgrade}
		>
			Upgrade
		</button>
		<button
			class="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 text-sm font-medium transition"
			on:click={handleBuyTokens}
		>
			Comprar tokens
		</button>
	</div>
</div>

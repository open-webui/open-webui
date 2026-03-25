<script lang="ts">
	import { onMount } from 'svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME } from '$lib/stores';

	import TokenUsageCard from '$lib/components/dashboard/TokenUsageCard.svelte';
	import PlanCard from '$lib/components/dashboard/PlanCard.svelte';
	import TeamCard from '$lib/components/dashboard/TeamCard.svelte';
	import IntegrationsCard from '$lib/components/dashboard/IntegrationsCard.svelte';

	let tokenUsage = { used: 0, total: 0, reset_date: '' };
	let plan = { name: '', description: '' };
	let members: { email: string; role: string }[] = [];
	let integrations: { provider: string; connected: boolean }[] = [];
	let loading = true;

	async function fetchData() {
		loading = true;
		try {
			const [tokensRes, planRes, membersRes, integrationsRes] = await Promise.all([
				fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/tokens/usage`),
				fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/billing/plan`),
				fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/team/members`),
				fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/integrations/status`)
			]);

			if (tokensRes.ok) tokenUsage = await tokensRes.json();
			if (planRes.ok) plan = await planRes.json();
			if (membersRes.ok) members = await membersRes.json();
			if (integrationsRes.ok) {
				const data = await integrationsRes.json();
				integrations = data.integrations || [];
			}
		} catch {
			// API not available - show empty state
		}
		loading = false;
	}

	onMount(fetchData);
</script>

<svelte:head>
	<title>Dashboard | {$WEBUI_NAME}</title>
</svelte:head>

<div class="flex-1 w-full max-w-4xl mx-auto px-4 py-8">
	<h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Dashboard</h1>

	{#if loading}
		<div class="flex justify-center py-16">
			<div class="size-8 border-4 border-claw-500 border-t-transparent rounded-full animate-spin" />
		</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
			<TokenUsageCard
				used={tokenUsage.used}
				total={tokenUsage.total}
				resetDate={tokenUsage.reset_date}
			/>
			<PlanCard planName={plan.name} planDescription={plan.description} />
			<TeamCard {members} />
			<IntegrationsCard {integrations} />
		</div>
	{/if}
</div>

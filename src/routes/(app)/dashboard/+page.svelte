<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import TenantDashboard from '$lib/components/admin/Dashboard/TenantDashboard.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let token = '';

	onMount(async () => {
		token = localStorage.getItem('token') || '';

		if (!token) {
			await goto('/auth');
			return;
		}

		loaded = true;
	});
</script>

<svelte:head>
	<title>{$i18n.t('Quality Dashboard')}</title>
</svelte:head>

{#if loaded}
	<div class="w-full h-full">
		<TenantDashboard {token} />
	</div>
{:else}
	<div class="flex items-center justify-center h-full">
		<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[#5CC9D3]"></div>
	</div>
{/if}


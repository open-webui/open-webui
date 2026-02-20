<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { config } from '$lib/stores';
	import Analytics from '$lib/components/admin/Analytics.svelte';

	onMount(() => {
		if (!($config?.features?.enable_analytics_dashboard ?? true)) {
			goto('/admin');
		}
	});
</script>

{#if $config?.features?.enable_analytics_dashboard ?? true}
	<Analytics />
{/if}

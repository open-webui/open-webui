<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { config } from '$lib/stores';
	import Analytics from '$lib/components/admin/Analytics.svelte';

	onMount(() => {
		if (!($config?.features.enable_admin_analytics ?? true)) {
			goto('/admin');
		}
	});
</script>

{#if $config?.features.enable_admin_analytics ?? true}
	<Analytics />
{/if}

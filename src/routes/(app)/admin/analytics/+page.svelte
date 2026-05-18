<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { config, user } from '$lib/stores';
	import { hasAdminAccess } from '$lib/utils/admin';
	import Analytics from '$lib/components/admin/Analytics.svelte';

	onMount(() => {
		if (!($config?.features.enable_admin_analytics ?? true)) {
			goto(hasAdminAccess($user) ? '/admin' : '/');
		}
	});
</script>

{#if $config?.features.enable_admin_analytics ?? true}
	<Analytics />
{/if}

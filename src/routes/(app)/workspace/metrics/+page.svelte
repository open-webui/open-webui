<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import Metrics from '$lib/components/workspace/Metrics.svelte';

	// Check if user has metrics access based on role
	$: hasMetricsAccess =
		$user?.role === 'admin' || $user?.role === 'analyst' || $user?.role === 'global_analyst';

	onMount(async () => {
		// Wait for user data to be loaded before making navigation decisions
		if (!$user) {
			// If no user data, wait a bit and try again or redirect to login
			setTimeout(() => {
				if (!$user || !hasMetricsAccess) {
					goto('/');
				}
			}, 100);
			return;
		}

		// Redirect to home if user doesn't have metrics access
		if (!hasMetricsAccess) {
			await goto('/');
		}
	});
</script>

{#if hasMetricsAccess}
	<Metrics />
{/if}

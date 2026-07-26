<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { config } from '$lib/stores';

	onMount(() => {
		if (!($config?.features.enable_admin_analytics ?? true)) {
			goto('/admin');
		} else {
			goto('/?settings=admin%3Aanalytics', { replaceState: true });
		}
	});
</script>

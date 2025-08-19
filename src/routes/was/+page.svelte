<!-- PATCH REDIRECT TO WAS -->
<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { config } from '$lib/stores';

	onMount(async () => {
		const WAS_REDIRECT_URL = $config?.extended_features?.was_redirect_url || false;
		if (WAS_REDIRECT_URL) window.open(JSON.parse(WAS_REDIRECT_URL), '_blank');
		goto('/');
	});
</script>
<!-- /PATCH REDIRECT TO WAS -->

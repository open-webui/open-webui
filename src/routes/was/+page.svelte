<!-- PATCH REDIRECT TO WAS -->
<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { config } from '$lib/stores';

	onMount(async () => {
		const WAS_REDIRECT = $config?.extended_features?.was_redirect || false;
		if (WAS_REDIRECT) window.open(JSON.parse(WAS_REDIRECT), '_blank');
		goto('/');
	});
</script>
<!-- /PATCH REDIRECT TO WAS -->

<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';

	onMount(() => {
		// Get the current URL search parameters
		const params = new URLSearchParams(window.location.search);

		// Check if 'v' parameter exists
		if (params.has('v')) {
			// Get the value of 'v' parameter
			const videoId = params.get('v');

			// Redirect to root with 'youtube' parameter

			goto(`${base}/?youtube=${encodeURIComponent(videoId)}`);
		} else {
			// Redirect to root if 'v' parameter doesn't exist
			goto(`${base}/`);
		}
	});
</script>

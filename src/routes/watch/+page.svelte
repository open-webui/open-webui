<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { WEBUI_BASE_PATH } from '$lib/constants';

	onMount(() => {
		// Get the current URL search parameters
		const params = new URLSearchParams(window.location.search);

		// Check if 'v' parameter exists
		if (params.has('v')) {
			// Get the value of 'v' parameter
			const videoId = params.get('v');

			// Redirect to root with 'youtube' parameter
			goto(`${WEBUI_BASE_PATH}/?youtube=${encodeURIComponent(videoId)}`);
		} else {
			// Redirect to root if 'v' parameter doesn't exist
			goto(`${WEBUI_BASE_PATH}/`);
		}
	});
</script>

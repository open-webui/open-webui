<script lang="ts">
	import { onMount } from 'svelte';
	import { discoverLocalMcpoTools } from '$lib/utils/localMcpoToolDiscoverer';

	onMount(async () => {
		// Automatically discover local MCPO tools when the component is mounted.
		// This typically happens once when the main layout loads.
		// Errors and notifications are handled within discoverLocalMcpoTools.
		await discoverLocalMcpoTools();
	});

	// This component does not render any UI itself.
	// It's used purely for its onMount lifecycle logic to initialize local MCPO tools.
</script>

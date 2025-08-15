<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';

	let serverId = '';
	let countdown = 10;

	onMount(() => {
		// Get server ID from URL parameters
		serverId = $page.url.searchParams.get('server_id') || 'Unknown';

		console.log('OAuth success page loaded for server:', serverId);

		// Start countdown to auto-close
		const timer = setInterval(() => {
			countdown--;
			if (countdown <= 0) {
				clearInterval(timer);
				window.close();
			}
		}, 1000);

		// Try to close immediately if possible
		setTimeout(() => {
			window.close();
		}, 100);

		return () => clearInterval(timer);
	});
</script>

<svelte:head>
	<title>OAuth Success - Open Web UI</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
	<div class="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 text-center">
		<!-- Success Icon -->
		<div
			class="mx-auto w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mb-6"
		>
			<svg
				class="w-8 h-8 text-green-600 dark:text-green-400"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"
				></path>
			</svg>
		</div>

		<!-- Success Message -->
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">MCP Server Connected!</h1>

		<p class="text-gray-600 dark:text-gray-300 mb-6">
			Your MCP server has been successfully authenticated and connected.
		</p>

		{#if serverId && serverId !== 'Unknown'}
			<div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 mb-6">
				<p class="text-sm text-gray-600 dark:text-gray-400">Server ID:</p>
				<p class="font-mono text-sm text-gray-900 dark:text-white break-all">{serverId}</p>
			</div>
		{/if}

		<!-- Close Instructions -->
		<div class="space-y-4">
			<p class="text-gray-700 dark:text-gray-300">
				You can now close this window to continue using Open Web UI.
			</p>

			<button
				on:click={() => window.close()}
				class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
			>
				Close Window
			</button>

			<p class="text-sm text-gray-500 dark:text-gray-400">
				This window will close automatically in {countdown} seconds.
			</p>
		</div>
	</div>
</div>

<style>
	/* Ensure the page is styled consistently */
	:global(body) {
		margin: 0;
		padding: 0;
	}
</style>

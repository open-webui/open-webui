<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';

	let error = '';
	let errorDescription = '';
	let countdown = 10; // Longer countdown for error case so user can read

	onMount(() => {
		// Get error details from URL parameters
		error = $page.url.searchParams.get('error') || 'Unknown error';
		errorDescription = $page.url.searchParams.get('error_description') || '';

		console.log('OAuth error page loaded:', error, errorDescription);

		// Start countdown to auto-close
		const timer = setInterval(() => {
			countdown--;
			if (countdown <= 0) {
				clearInterval(timer);
				window.close();
			}
		}, 1000);

		return () => clearInterval(timer);
	});
</script>

<svelte:head>
	<title>OAuth Error - Open Web UI</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
	<div class="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 text-center">
		<!-- Error Icon -->
		<div
			class="mx-auto w-16 h-16 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center mb-6"
		>
			<svg
				class="w-8 h-8 text-red-600 dark:text-red-400"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M6 18L18 6M6 6l12 12"
				></path>
			</svg>
		</div>

		<!-- Error Message -->
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">
			OAuth Authentication Failed
		</h1>

		<p class="text-gray-600 dark:text-gray-300 mb-6">
			There was an issue authenticating your MCP server connection.
		</p>

		<!-- Error Details -->
		<div
			class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6"
		>
			<p class="text-sm font-medium text-red-800 dark:text-red-400 mb-2">Error Details:</p>
			<p class="text-sm text-red-700 dark:text-red-300 font-mono break-all">{error}</p>
			{#if errorDescription}
				<p class="text-sm text-red-600 dark:text-red-400 mt-2">{errorDescription}</p>
			{/if}
		</div>

		<!-- Close Instructions -->
		<div class="space-y-4">
			<p class="text-gray-700 dark:text-gray-300">
				Please close this window and try again, or configure the server manually.
			</p>

			<button
				on:click={() => window.close()}
				class="w-full bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
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

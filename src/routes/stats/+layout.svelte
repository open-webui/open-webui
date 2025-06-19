<script lang="ts">
	import '../../app.css';
	import 'tippy.js/dist/tippy.css';

	import { onMount, setContext } from 'svelte';
	import { writable } from 'svelte/store';

	import { theme } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import i18n, { initI18n, getLanguages } from '$lib/i18n';
	import { Toaster } from 'svelte-sonner';

	let loaded = false;

	const initializeSettings = async () => {
		// Initialize theme
		theme.set(localStorage.theme ?? 'system');

		// Initialize i18n
		await initI18n();

		loaded = true;
	};

	onMount(async () => {
		await initializeSettings();
	});

	setContext('i18n', i18n);
</script>

<svelte:head>
	<title>Statistiques | Assistant IA</title>
	<link rel="icon" type="image/png" href="{WEBUI_BASE_URL}/static/favicon.png" />
	<meta name="viewport" content="width=device-width, initial-scale=1.0" />
	<meta name="apple-mobile-web-app-capable" content="yes" />
	<meta name="mobile-web-app-capable" content="yes" />
</svelte:head>

{#if loaded}
	<div class="stats-container min-h-screen w-full overflow-y-auto">
		<slot />
	</div>

	<Toaster richColors position="top-center" />
{:else}
	<div class="flex flex-col min-h-screen">
		<div class="flex-1 flex items-center justify-center">
			<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
		</div>
	</div>
{/if}

<style>
:global(html, body) {
	height: 100%;
	margin: 0;
	padding: 0;
	overflow-y: auto;
}

:global(body) {
	min-height: 100vh;
	width: 100%;
}

.stats-container {
	display: flex;
	flex-direction: column;
}
</style>

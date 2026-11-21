<script lang="ts">
	import { page } from '$app/stores';
	import { WEBUI_NAME } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';
</script>

<svelte:head>
	<title>{$page.status} · {$WEBUI_NAME}</title>
</svelte:head>

<div class="min-h-dvh bg-base-0 text-base-1000 dark:bg-base-1000 dark:text-base-0 relative">
	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region"></div>
	<main
		id="main-content"
		tabindex="-1"
		class="min-h-dvh w-full p-6 flex items-center justify-center text-center"
	>
		<h1 class="text-xl font-normal text-balance dark:text-base-100">
			{$page.status}{#if $page.error?.message}: {$page.error.message}{/if}
		</h1>
	</main>

	<div class="fixed top-0 left-0 m-10 z-50">
		<img
			crossorigin="anonymous"
			src="{WEBUI_BASE_URL}/static/favicon.png"
			class="w-6 rounded-full"
			alt="{$WEBUI_NAME} logo"
		/>
	</div>
</div>

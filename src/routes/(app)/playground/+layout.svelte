<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, showSidebar, functions } from '$lib/stores';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { page } from '$app/stores';

	const i18n = getContext('i18n');

	onMount(async () => {});
</script>

<svelte:head>
	<title>
		{$i18n.t('Playground')} | {$WEBUI_NAME}
	</title>
</svelte:head>

<div
	class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} max-w-full"
>
	<nav class="px-6 py-3 w-full drag-region border-b border-gray-200 dark:border-gray-800">
		<div class="flex items-center justify-between">
			<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
				<button
					id="sidebar-toggle-button"
					class="cursor-pointer p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 transition-colors"
					on:click={() => {
						showSidebar.set(!$showSidebar);
					}}
					aria-label="Toggle Sidebar"
				>
					<MenuLines />
				</button>
			</div>

			<div class="flex gap-2">
				<a
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors {['/playground', '/playground/'].includes(
						$page.url.pathname
					)
						? 'bg-orange-500 text-white'
						: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
					href="/playground"
				>
					Chat
				</a>

				<a
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors {$page.url.pathname.includes(
						'/playground/completions'
					)
						? 'bg-orange-500 text-white'
						: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
					href="/playground/completions"
				>
					Completions
				</a>
			</div>
		</div>
	</nav>

	<div class=" flex-1 max-h-full overflow-y-auto">
		<slot />
	</div>
</div>

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
	class=" flex flex-col w-full h-screen max-h-[100dvh] {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''}"
>
	<div class=" px-3.5 py-2">
		<div class=" flex items-center gap-1">
			<div class="{$showSidebar ? 'md:hidden' : ''} mr-1 flex flex-none items-center">
				<button
					id="sidebar-toggle-button"
					class="cursor-pointer p-1.5 flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
					on:click={() => {
						showSidebar.set(!$showSidebar);
					}}
					aria-label="Toggle Sidebar"
				>
					<div class=" m-auto self-center">
						<MenuLines />
					</div>
				</button>
			</div>
			<!-- <div class="flex items-center text-xl font-semibold">{$i18n.t('Admin Panel')}</div> -->

			<div class=" flex w-full">
				<div
					class="flex scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent/10 p-1"
				>
					<a
						class="min-w-fit rounded-full p-1.5 px-3 {['/playground', '/playground/'].includes(
							$page.url.pathname
						)
							? 'bg-gray-50 dark:bg-gray-850'
							: ''} transition"
						href="/playground">{$i18n.t('Chat')}</a
					>

					<a
						class="min-w-fit rounded-full p-1.5 px-3 {$page.url.pathname.includes(
							'/playground/notes'
						)
							? 'bg-gray-50 dark:bg-gray-850'
							: ''} transition"
						href="/playground/notes">{$i18n.t('Notes')}</a
					>

					<a
						class="min-w-fit rounded-full p-1.5 px-3 {$page.url.pathname.includes(
							'/playground/completions'
						)
							? 'bg-gray-50 dark:bg-gray-850'
							: ''} transition"
						href="/playground/completions">{$i18n.t('Completions')}</a
					>
				</div>
			</div>
		</div>
	</div>

	<div class=" flex-1 max-h-full overflow-y-auto">
		<slot />
	</div>
</div>

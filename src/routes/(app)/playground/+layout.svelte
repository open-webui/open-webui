<script lang="ts">
	import { getContext } from 'svelte';
	import { WEBUI_NAME, showSidebar, mobile } from '$lib/stores';
	import { page } from '$app/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	const i18n = getContext('i18n');
</script>

<svelte:head>
	<title>
		{$i18n.t('Playground')} • {$WEBUI_NAME}
	</title>
</svelte:head>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	<nav class="pb-1 px-2.5 pt-2 backdrop-blur-xl drag-region select-none">
		<div class="flex items-center gap-0.5 md:gap-1">
			{#if $mobile}
				<div class="{$showSidebar ? 'md:hidden' : ''} self-center flex flex-none items-center">
					<Tooltip
						content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						interactive={true}
					>
						<button
							id="sidebar-toggle-button"
							class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
							aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							on:click={() => {
								showSidebar.set(!$showSidebar);
							}}
						>
							<div class=" self-center p-1.5">
								<Sidebar className="size-4" />
							</div>
						</button>
					</Tooltip>
				</div>
			{/if}

			<div class="flex w-full items-center">
				<div
					class="flex min-w-0 items-center gap-0.5 md:gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-normal rounded-full bg-transparent py-1 touch-auto pointer-events-auto"
				>
					<a
						draggable="false"
						class="min-w-fit px-1 text-sm {['/playground', '/playground/'].includes(
							$page.url.pathname
						)
							? ''
							: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition select-none"
						href="/playground">{$i18n.t('Chat')}</a
					>

					<!-- <a
						class="min-w-fit p-1.5 {$page.url.pathname.includes('/playground/notes')
							? ''
							: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
						href="/playground/notes">{$i18n.t('Notes')}</a
					> -->

					<a
						draggable="false"
						class="min-w-fit px-1 text-sm {$page.url.pathname.includes('/playground/completions')
							? ''
							: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition select-none"
						href="/playground/completions">{$i18n.t('Completions')}</a
					>

					<a
						draggable="false"
						class="min-w-fit px-1 text-sm {$page.url.pathname.includes('/playground/images')
							? ''
							: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition select-none"
						href="/playground/images">{$i18n.t('Images')}</a
					>
				</div>
			</div>
		</div>
	</nav>

	<div class=" flex-1 max-h-full overflow-y-auto">
		<slot />
	</div>
</div>

<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { WEBUI_NAME, showSidebar, user } from '$lib/stores';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { page } from '$app/stores';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Admin Panel')} | {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div
		class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-260px)]'
			: ''} max-w-full"
	>
		<nav class="sticky top-0 z-10 px-3 py-2 backdrop-blur-xl bg-white/80 dark:bg-gray-900/80 border-b border-gray-100 dark:border-gray-800 drag-region">
			<div class="flex items-center gap-3">
				<div class="{$showSidebar ? 'md:hidden' : ''} flex-none">
					<button
						id="sidebar-toggle-button"
						class="p-2 flex items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
						on:click={() => {
							showSidebar.set(!$showSidebar);
						}}
						aria-label="Toggle Sidebar"
					>
						<MenuLines />
					</button>
				</div>

				<div class="flex-1 overflow-hidden">
					<div
						class="flex gap-1.5 scrollbar-none overflow-x-auto text-sm font-medium bg-gray-50 dark:bg-gray-850 rounded-lg p-1"
					>
						<a
							class="min-w-fit px-4 py-2 rounded-md transition-all {['/admin', '/admin/users'].includes($page.url.pathname)
								? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
								: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-100/50 dark:hover:bg-gray-800/50'}"
							href="/admin"
						>
							{$i18n.t('Users')}
						</a>

						<a
							class="min-w-fit px-4 py-2 rounded-md transition-all {$page.url.pathname.includes('/admin/evaluations')
								? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
								: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-100/50 dark:hover:bg-gray-800/50'}"
							href="/admin/evaluations"
						>
							{$i18n.t('Evaluations')}
						</a>

						<a
							class="min-w-fit px-4 py-2 rounded-md transition-all {$page.url.pathname.includes('/admin/functions')
								? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
								: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-100/50 dark:hover:bg-gray-800/50'}"
							href="/admin/functions"
						>
							{$i18n.t('Functions')}
						</a>

						<a
							class="min-w-fit px-4 py-2 rounded-md transition-all {$page.url.pathname.includes('/admin/settings')
								? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
								: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-100/50 dark:hover:bg-gray-800/50'}"
							href="/admin/settings"
						>
							{$i18n.t('Settings')}
						</a>
					</div>
				</div>
			</div>
		</nav>

		<div class="flex-1 px-5 py-4 overflow-y-auto">
			<slot />
		</div>
	</div>
{/if}
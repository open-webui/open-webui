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
		{$i18n.t('Admin Panel')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div
		class="p-4 flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out   {$showSidebar
			? 'md:max-w-[calc(100%-300px)]'
			: 'md:max-w-[calc(100%-80px)]'} max-w-full"
			
	>
		<div class="bg-white h-[calc(100vh-2rem)] max-h-[100dvh] dark:bg-gray-900">
			<nav class="px-2.5 pt-1 backdrop-blur-xl drag-region">
				<div class=" flex items-center gap-1">
					<!-- <div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center self-end">
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
					</div> -->

					<div class=" flex w-full tabs-nav">
						<div
							class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent pt-1"
						>
							<a
								class="min-w-fit rounded-full p-1.5 {$page.url.pathname.includes('/admin/users')
									? 'active'
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
								href="/admin">{$i18n.t('Users')}</a
							>

							<a
								class="min-w-fit rounded-full p-1.5 {$page.url.pathname.includes('/admin/evaluations')
									? 'active'
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
								href="/admin/evaluations">{$i18n.t('Evaluations')}</a
							>

							<a
								class="min-w-fit rounded-full p-1.5 {$page.url.pathname.includes('/admin/functions')
									? 'active'
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
								href="/admin/functions">{$i18n.t('Functions')}</a
							>

							<a
								class="min-w-fit rounded-full p-1.5 {$page.url.pathname.includes('/admin/settings')
									? 'active'
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
								href="/admin/settings">{$i18n.t('Settings')}</a
							>
						</div>
					</div>
				</div>
			</nav>

			<div class="p-[16px] flex-1 max-h-full overflow-y-auto">
				<slot />
			</div>
		</div>
	</div>
{/if}

<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { WEBUI_NAME, mobile, showSidebar, user } from '$lib/stores';
	import { page } from '$app/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import Sidebar from '$lib/components/icons/Sidebar.svelte';

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
		class=" flex flex-col h-screen max-h-[100dvh] flex-1 transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ' md:max-w-[calc(100%-49px)]'}  w-full max-w-full"
	>
		<nav class="   px-2.5 pt-1.5 backdrop-blur-xl drag-region">
			<div class=" flex items-center gap-1">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center self-end">
						<Tooltip
							content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							interactive={true}
						>
							<button
								id="sidebar-toggle-button"
								class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
								on:click={() => {
									showSidebar.set(!$showSidebar);
								}}
							>
								<div class=" self-center p-1.5">
									<Sidebar />
								</div>
							</button>
						</Tooltip>
					</div>
				{/if}

				<div class=" flex w-full">
					<div
						class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent pt-1"
					>
						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/users')
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/admin">{$i18n.t('Users')}</a
						>

						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/analytics')
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/admin/analytics">{$i18n.t('Analytics')}</a
						>

						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/evaluations')
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/admin/evaluations">{$i18n.t('Evaluations')}</a
						>

						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/functions')
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/admin/functions">{$i18n.t('Functions')}</a
						>

						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/settings')
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/admin/settings">{$i18n.t('Settings')}</a
						>
					</div>
				</div>
			</div>
		</nav>

		<div class="  pb-1 flex-1 max-h-full overflow-y-auto">
			<slot />
		</div>
	</div>
{/if}

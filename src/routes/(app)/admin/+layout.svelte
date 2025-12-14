<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { WEBUI_NAME, mobile, showSidebar, user } from '$lib/stores';
	import { page } from '$app/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import { getManagedGroups } from '$lib/apis/groups';

	const i18n = getContext('i18n');

	let loaded = false;
	let isGroupManager = false;

	// Reactive statement to keep isAdmin in sync with user store
	$: isAdmin = $user?.role === 'admin';

	onMount(async () => {
		if (!isAdmin) {
			// Check if user is a group manager
			const managedGroups = await getManagedGroups(localStorage.token).catch(() => []);
			isGroupManager = managedGroups && managedGroups.length > 0;
			
			if (isGroupManager) {
				// Group managers can only access /admin/users/groups
				if (!$page.url.pathname.includes('/admin/users/groups')) {
					await goto('/admin/users/groups');
					return;
				}
			} else {
				// Neither admin nor group manager - redirect to home
				await goto('/');
				return;
			}
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
			? 'md:max-w-[calc(100%-260px)]'
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
						{#if isAdmin || isGroupManager}
							<a
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/users')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
								href={isGroupManager && !isAdmin ? '/admin/users/groups' : '/admin'}>{isGroupManager && !isAdmin ? $i18n.t('Groups') : $i18n.t('Users')}</a
							>
						{/if}

						<!-- <a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/analytics')
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/admin/analytics">{$i18n.t('Analytics')}</a
						> -->

						{#if isAdmin}
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
						{/if}
					</div>
				</div>
			</div>
		</nav>

		<div class="  pb-1 flex-1 max-h-full overflow-y-auto">
			<slot />
		</div>
	</div>
{/if}

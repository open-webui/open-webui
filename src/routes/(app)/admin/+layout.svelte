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
		class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-260px)]'
			: ''} max-w-full"
	>
		<nav class="   px-2.5 pt-1 backdrop-blur-xl drag-region">
			<div class=" flex items-center gap-1">
				<div
					class="{$showSidebar ? 'md:hidden' : ''} self-center flex flex-none items-center"
					draggable="false"
				>
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

				<div class="" draggable="false">
					<div
						class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent py-1 touch-auto pointer-events-auto"
					>
						<a
							class="min-w-fit rounded-full p-1.5 {['/admin/users/overview'].includes(
								$page.url.pathname
							)
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/admin/users/overview"
							draggable="false"
							onselectstart="return false;">{$i18n.t('Users')}</a
						>

						<a
							class="min-w-fit rounded-full p-1.5 {$page.url.pathname.includes(
								'/admin/evaluations/leaderboard'
							)
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/admin/evaluations/leaderboard"
							draggable="false"
							onselectstart="return false;">{$i18n.t('Evaluations')}</a
						>

						<a
							class="min-w-fit rounded-full p-1.5 {$page.url.pathname.includes('/admin/functions')
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/admin/functions"
							draggable="false"
							onselectstart="return false;">{$i18n.t('Functions')}</a
						>

						<a
							class="min-w-fit rounded-full p-1.5 {$page.url.pathname.includes(
								'/admin/settings/general'
							)
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/admin/settings/general"
							draggable="false"
							onselectstart="return false;">{$i18n.t('Settings')}</a
						>
					</div>
				</div>
			</div>
		</nav>

		<div class="  pb-1 px-[16px] flex-1 max-h-full overflow-y-auto" draggable="false">
			<slot />
		</div>
	</div>
{/if}

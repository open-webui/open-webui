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
		class=" flex flex-col w-full min-h-screen max-h-screen {$showSidebar
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
							class="min-w-fit rounded-full p-1.5 px-3 {['/admin', '/admin/'].includes(
								$page.url.pathname
							)
								? 'bg-gray-50 dark:bg-gray-850'
								: ''} transition"
							href="/admin">{$i18n.t('Dashboard')}</a
						>

						<a
							class="min-w-fit rounded-full p-1.5 px-3 {$page.url.pathname.includes(
								'/admin/evaluations'
							)
								? 'bg-gray-50 dark:bg-gray-850'
								: ''} transition"
							href="/admin/evaluations">{$i18n.t('Evaluations')}</a
						>

						<a
							class="min-w-fit rounded-full p-1.5 px-3 {$page.url.pathname.includes(
								'/admin/settings'
							)
								? 'bg-gray-50 dark:bg-gray-850'
								: ''} transition"
							href="/admin/settings">{$i18n.t('Settings')}</a
						>
					</div>
				</div>
			</div>
		</div>

		<div class=" pb-1 px-[18px] flex-1 max-h-full overflow-y-auto">
			<slot />
		</div>
	</div>
{/if}

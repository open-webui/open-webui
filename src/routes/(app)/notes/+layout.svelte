<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import {
		WEBUI_NAME,
		showSidebar,
		functions,
		config,
		user,
		showArchivedChats,
		mobile
	} from '$lib/stores';
	import { goto } from '$app/navigation';

	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Newlogo from '$lib/components/icons/Newlogo.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if (
			!(
				($config?.features?.enable_notes ?? false) &&
				($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true))
			)
		) {
			// If the feature is not enabled, redirect to the home page
			goto('/');
		}

		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Notes')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div
		class="relative background-gradient-bg flex  w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-300px)]'
			: ''} max-w-full"
	>{#if !$mobile}
		<nav
			class=" p-[24px] pb-[72px]">

				<Newlogo />


			<!--<div class=" flex items-center">
				<!-- <div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
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

				<div class="ml-2 py-0.5 self-center flex items-center justify-between w-full">

					<img src="/logo-dark.png" alt="GovGPT Logo" class="w-[132px] h-[40px]"/>

					<div class=" self-center flex items-center gap-1">
						{#if $user !== undefined && $user !== null}
							<UserMenu
								className="max-w-[240px]"
								role={$user?.role}
								help={true}
								on:show={(e) => {
									if (e.detail === 'archived-chat') {
										showArchivedChats.set(true);
									}
								}}
							>
								<button
									class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
									aria-label="User Menu"
								>
									<div class=" self-center">
										<img
											src={$user?.profile_image_url}
											class="size-6 object-cover rounded-full"
											alt="User profile"
											draggable="false"
										/>
									</div>
								</button>
							</UserMenu>
						{/if}
					</div>
				</div>
			</div>-->
		</nav>
{/if}
		<div class="max-w-[800px] flex-1 max-h-full @container p-20">
			<slot />
		</div>

		<div
				class="{$mobile ?'fixed right-0 bg-neutrals-50 w-full h-[60px] px-[16px] flex justify-end items-center':'p-[24px] pb-[72px] '} font-bold text-[22px] leading-[30px] text-neutrals-800 touch-auto pointer-events-auto"
			>
				<a class="min-w-fit transition" href="/notes">
					{$i18n.t('Notes')}
				</a>
			</div>
	</div>
{/if}

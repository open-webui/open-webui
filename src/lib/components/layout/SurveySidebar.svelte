<script lang="ts">
	import { page } from '$app/stores';
	import { showSidebar, user, mobile, WEBUI_NAME } from '$lib/stores';
	import { getContext } from 'svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');
</script>

{#if $showSidebar}
	<div
		class="{$mobile
			? 'fixed z-40 top-0 right-0 left-0 bottom-0 bg-black/60 w-full min-h-screen h-screen flex justify-center overflow-hidden overscroll-contain'
			: ''} fixed md:hidden z-40 top-0 right-0 left-0 bottom-0 bg-black/60 w-full min-h-screen h-screen flex justify-center overflow-hidden overscroll-contain"
		on:mousedown={() => {
			showSidebar.set(!$showSidebar);
		}}
	/>
{/if}

{#if !$mobile && !$showSidebar}
	<div
		class="pt-[7px] pb-2 px-2 flex flex-col justify-between text-black dark:text-white hover:bg-gray-50/30 dark:hover:bg-gray-950/30 h-full z-10 transition-all border-e-[0.5px] border-gray-50 dark:border-gray-850/30"
		id="survey-sidebar"
	>
		<button
			class="flex items-center justify-center w-8 h-8 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition"
			on:click={() => {
				showSidebar.set(true);
			}}
			aria-label="Show Sidebar"
		>
			<svg
				class="w-5 h-5"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M4 6h16M4 12h16M4 18h16"
				></path>
			</svg>
		</button>
	</div>
{/if}

{#if $showSidebar}
	<nav
		class="flex flex-col justify-between text-black dark:text-white bg-white dark:bg-gray-900 border-e border-gray-200 dark:border-gray-800 h-full z-50 transition-all {$mobile
			? 'fixed w-[260px]'
			: 'relative'} {$showSidebar ? 'w-[260px]' : 'w-0'} overflow-hidden"
		id="survey-sidebar-nav"
	>
		<div class="flex flex-col flex-1 overflow-y-auto">
			<!-- Header -->
			<div
				class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800"
			>
				<div class="flex items-center gap-2">
					<h2 class="text-lg font-semibold">{$WEBUI_NAME}</h2>
				</div>
				{#if $mobile}
					<button
						class="flex items-center justify-center w-8 h-8 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition"
						on:click={() => {
							showSidebar.set(false);
						}}
						aria-label="Hide Sidebar"
					>
						<svg
							class="w-5 h-5"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							xmlns="http://www.w3.org/2000/svg"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							></path>
						</svg>
					</button>
				{/if}
			</div>

			<!-- Navigation Items -->
			<div class="flex-1 p-4">
				<div class="space-y-2">
					<div
						class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4"
					>
						{$i18n.t('Survey Navigation')}
					</div>
					<!-- Survey navigation items can be added here if needed -->
				</div>
			</div>
		</div>

		<!-- User Menu -->
		{#if $user}
			<div class="p-4 border-t border-gray-200 dark:border-gray-800">
				<UserMenu
					show={false}
					role={$user?.role || ''}
					profile={true}
					help={false}
					showActiveUsers={false}
				>
					<div
						class="flex items-center rounded-2xl py-2 px-1.5 w-full hover:bg-gray-100/50 dark:hover:bg-gray-900/50 transition"
					>
						<div class="self-center mr-3 relative">
							<img
								src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
								class="size-7 object-cover rounded-full"
								alt={$i18n.t('Open User Profile Menu')}
								aria-label={$i18n.t('Open User Profile Menu')}
							/>
						</div>
						<div class="self-center font-medium">{$user?.name}</div>
					</div>
				</UserMenu>
			</div>
		{/if}
	</nav>
{/if}

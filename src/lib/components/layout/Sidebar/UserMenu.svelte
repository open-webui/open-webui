<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';
	import { goto } from '$app/navigation';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import { showSettings, showCompanySettings, activeUserIds, USAGE_POOL, mobile, showSidebar } from '$lib/stores';
	import { fade, slide } from 'svelte/transition';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { userSignOut } from '$lib/apis/auths';
	import SettingsIcon from '$lib/components/icons/SettingsIcon.svelte';
	import SignOutIcon from '$lib/components/icons/SignOutIcon.svelte';
	import CompanySettingsIcon from '$lib/components/icons/CompanySettingsIcon.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let role = '';
	export let className = 'max-w-[240px]';

	const dispatch = createEventDispatcher();
</script>

<DropdownMenu.Root
	bind:open={show}
	onOpenChange={(state) => {
		dispatch('change', state);
	}}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			class="w-full {className} text-sm rounded-lg border border-lightGray-400 dark:border-customGray-700 px-1 py-1.5 z-50 bg-gray-50 dark:bg-customGray-900 dark:text-white shadow-lg font-primary"
			sideOffset={8}
			side="bottom"
			align="start"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<button
				class="font-medium flex rounded-md text-sm text-lightGray-100 dark:text-customGray-100 py-2 px-3 w-full hover:bg-lightGray-700 dark:hover:text-white dark:hover:bg-customGray-950 transition"
				on:click={async () => {
					await showSettings.set(true);
					show = false;

					if ($mobile) {
						showSidebar.set(false);
					}
				}}
			>
				<div class=" self-center mr-3">
					<SettingsIcon/>	
				</div>
				<div class=" self-center truncate">{$i18n.t('Account Settings')}</div>
			</button>
			{#if role === 'admin'}
				<button
					class="font-medium flex rounded-md text-sm text-lightGray-100 dark:text-customGray-100 py-2 px-3 w-full hover:bg-lightGray-700 dark:hover:text-white dark:hover:bg-customGray-950 transition"
					on:click={async () => {
						// showCompanySettings.set(true);
						const url = new URL(window.location.href);
						url.searchParams.set('modal', 'company-settings');
						url.searchParams.set('tab', 'general-settings');
						goto(`${url.pathname}${url.search}`, { keepfocus: true, replaceState: false });
	
						show = false;

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
				>
					<div class=" self-center mr-3">
						<CompanySettingsIcon/>	
					</div>
					<div class=" self-center truncate">{$i18n.t('Company Settings')}</div>
				</button>
			{/if}

			<!-- <button
				class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={() => {
					dispatch('show', 'archived-chat');
					show = false;

					if ($mobile) {
						showSidebar.set(false);
					}
				}}
			>
				<div class=" self-center mr-3">
					<ArchiveBox className="size-5" strokeWidth="1.5" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Archived Chats')}</div>
			</button> -->

			<!-- {#if role === 'admin'}
				<a
					class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
					href="/playground"
					on:click={() => {
						show = false;

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
				>
					<div class=" self-center mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M14.25 9.75 16.5 12l-2.25 2.25m-4.5 0L7.5 12l2.25-2.25M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z"
							/>
						</svg>
					</div>
					<div class=" self-center truncate">{$i18n.t('Playground')}</div>
				</a>

				<a
					class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
					href="/admin"
					on:click={() => {
						show = false;

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
				>
					<div class=" self-center mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-5 h-5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M17.982 18.725A7.488 7.488 0 0012 15.75a7.488 7.488 0 00-5.982 2.975m11.963 0a9 9 0 10-11.963 0m11.963 0A8.966 8.966 0 0112 21a8.966 8.966 0 01-5.982-2.275M15 9.75a3 3 0 11-6 0 3 3 0 016 0z"
							/>
						</svg>
					</div>
					<div class=" self-center truncate">{$i18n.t('Admin Panel')}</div>
				</a>
			{/if} -->

			<hr class=" border-lightGray-400 dark:border-gray-850 my-1 p-0" />

			<button
				class="font-medium flex rounded-md text-sm text-lightGray-100 dark:text-customGray-100 py-2 px-3 w-full hover:bg-lightGray-700 dark:hover:text-white dark:hover:bg-customGray-950 transition"
				on:click={async () => {
					await userSignOut();
					localStorage.removeItem('token');
					location.href = '/login';
					show = false;
				}}
			>
				<div class=" self-center mr-3">
					<SignOutIcon/>		
				</div>
				<div class=" self-center truncate">{$i18n.t('Sign Out')}</div>
			</button>

			<!-- {#if $activeUserIds?.length > 0}
				<hr class=" border-gray-50 dark:border-gray-850 my-1 p-0" />

				<Tooltip
					content={$USAGE_POOL && $USAGE_POOL.length > 0
						? `${$i18n.t('Running')}: ${$USAGE_POOL.join(', ')} ✨`
						: ''}
				>
					<div class="flex rounded-md py-1.5 px-3 text-xs gap-2.5 items-center">
						<div class=" flex items-center">
							<span class="relative flex size-2">
								<span
									class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
								/>
								<span class="relative inline-flex rounded-full size-2 bg-green-500" />
							</span>
						</div>

						<div class=" ">
							<span class="">
								{$i18n.t('Active Users')}:
							</span>
							<span class=" font-semibold">
								{$activeUserIds?.length}
							</span>
						</div>
					</div>
				</Tooltip>
			{/if} -->

			<!-- <DropdownMenu.Item class="flex items-center px-3 py-2 text-sm ">
				<div class="flex items-center">Profile</div>
			</DropdownMenu.Item> -->
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>

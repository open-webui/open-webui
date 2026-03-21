<script lang="ts">
	import { getContext } from 'svelte';

	import { mobile, showArchivedChats, showSidebar, user } from '$lib/stores';

	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '../../common/Tooltip.svelte';
	import Sidebar from '../../icons/Sidebar.svelte';
	import Hashtag from '../../icons/Hashtag.svelte';
	import Lock from '../../icons/Lock.svelte';

	const i18n = getContext('i18n');

	export let channel = null;
</script>

<nav class="sticky top-0 z-30 w-full px-1.5 py-1 -mb-8 flex items-center drag-region flex flex-col">
	<div
		id="navbar-bg-gradient-to-b"
		class=" bg-linear-to-b via-50% from-white via-white to-transparent dark:from-gray-900 dark:via-gray-900 dark:to-transparent pointer-events-none absolute inset-0 -bottom-7 z-[-1]"
	></div>

	<div class="flex max-w-full w-full mx-auto px-1 pt-0.5 bg-transparent">
		<div class="flex items-center w-full max-w-full">
			{#if $mobile}
				<div
					class="{$showSidebar
						? 'md:hidden'
						: ''} mr-1.5 mt-0.5 self-start flex flex-none items-center text-gray-600 dark:text-gray-400"
				>
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

			<div
				class="flex-1 overflow-hidden max-w-full py-0.5 flex items-center
			{$showSidebar ? 'ml-1' : ''}
			"
			>
				<div class="flex items-center gap-0.5 shrink-0">
					<div class="size-4.5 justify-center flex items-center">
						{#if channel?.access_control?.group === 'private'}
							<Lock className="size-5" strokeWidth="2" />
						{:else}
							<Hashtag className="size-3.5" strokeWidth="2.5" />
						{/if}
					</div>

					<div class=" text-left self-center overflow-hidden w-full line-clamp-1 flex-1">
						{#if channel?.name}
							{channel.name}
						{:else}
							Call
						{/if}
					</div>
				</div>
			</div>

			<div class="self-start flex flex-none items-center text-gray-600 dark:text-gray-400 gap-1">
				<div
					class="flex-1 overflow-hidden max-w-full py-0.5 flex items-center
				{$showSidebar ? 'ml-1' : ''}
				"
				>
					{#if $user !== undefined}
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
										src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
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
		</div>
	</div>
</nav>

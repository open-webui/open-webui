<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { mobile, showArchivedChats, showSidebar, user } from '$lib/stores';

	import { slide } from 'svelte/transition';
	import { page } from '$app/stores';

	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Sidebar from '../icons/Sidebar.svelte';
	import Hashtag from '../icons/Hashtag.svelte';
	import Lock from '../icons/Lock.svelte';
	import UserAlt from '../icons/UserAlt.svelte';
	import ChannelInfoModal from './ChannelInfoModal.svelte';

	const i18n = getContext('i18n');

	let showChannelInfoModal = false;

	export let channel;
</script>

<ChannelInfoModal bind:show={showChannelInfoModal} {channel} />
<nav class="sticky top-0 z-30 w-full px-1.5 py-1 -mb-8 flex items-center drag-region">
	<div
		id="navbar-bg-gradient-to-b"
		class=" bg-linear-to-b via-50% from-white via-white to-transparent dark:from-gray-900 dark:via-gray-900 dark:to-transparent pointer-events-none absolute inset-0 -bottom-7 z-[-1]"
	></div>

	<div class=" flex max-w-full w-full mx-auto px-1 pt-0.5 bg-transparent">
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
				class="flex-1 overflow-hidden max-w-full py-0.5
			{$showSidebar ? 'ml-1' : ''}
			"
			>
				{#if channel}
					<div class="flex items-center gap-0.5 shrink-0">
						<div class=" size-4 justify-center flex items-center">
							{#if channel?.access_control === null}
								<Hashtag className="size-3" strokeWidth="2.5" />
							{:else}
								<Lock className="size-5" strokeWidth="2" />
							{/if}
						</div>

						<div
							class=" text-left self-center overflow-hidden w-full line-clamp-1 capitalize flex-1"
						>
							{channel.name}
						</div>
					</div>
				{/if}
			</div>

			<div class="self-start flex flex-none items-center text-gray-600 dark:text-gray-400 gap-1">
				{#if channel?.user_count !== undefined}
					<Tooltip content={$i18n.t('Users')}>
						<button
							class=" flex cursor-pointer py-1 px-1.5 border dark:border-gray-850 border-gray-50 rounded-xl text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
							aria-label="User Count"
							type="button"
							on:click={() => {
								showChannelInfoModal = true;
							}}
						>
							<div class=" flex items-center gap-0.5 m-auto self-center">
								<UserAlt className=" size-4" strokeWidth="1.5" />

								<div class="text-sm">
									{channel.user_count}
								</div>
							</div>
						</button>
					</Tooltip>
				{/if}

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
</nav>

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
	import Users from '../icons/Users.svelte';
	import Pin from '../icons/Pin.svelte';
	import PinnedMessagesModal from './PinnedMessagesModal.svelte';

	const i18n = getContext('i18n');

	let showChannelPinnedMessagesModal = false;
	let showChannelInfoModal = false;

	const hasPublicReadGrant = (grants: any) =>
		Array.isArray(grants) &&
		grants.some(
			(grant) =>
				grant?.principal_type === 'user' &&
				grant?.principal_id === '*' &&
				grant?.permission === 'read'
		);

	const isPublicChannel = (channel: any): boolean => {
		if (channel?.type === 'group') {
			if (typeof channel?.is_private === 'boolean') {
				return !channel.is_private;
			}
			return hasPublicReadGrant(channel?.access_grants);
		}
		return hasPublicReadGrant(channel?.access_grants);
	};

	export let channel;

	export let onPin = (messageId, pinned) => {};
	export let onUpdate = () => {};
</script>

<PinnedMessagesModal bind:show={showChannelPinnedMessagesModal} {channel} {onPin} />
<ChannelInfoModal bind:show={showChannelInfoModal} {channel} {onUpdate} />
<nav class="sticky top-0 z-30 w-full px-1.5 py-1 -mb-8 flex items-center drag-region flex flex-col">
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
				class="flex-1 overflow-hidden max-w-full py-0.5 flex items-center
			{$showSidebar ? 'ml-1' : ''}
			"
			>
				{#if channel}
					<div class="flex items-center gap-0.5 shrink-0">
						{#if channel?.type === 'dm'}
							{#if channel?.users}
								{@const channelMembers = channel.users.filter((u) => u.id !== $user?.id)}
								<div class="flex mr-1.5 relative">
									{#each channelMembers.slice(0, 2) as u, index}
										<img
											src={`${WEBUI_API_BASE_URL}/users/${u.id}/profile/image`}
											alt={u.name}
											class=" size-6.5 rounded-full border-2 border-white dark:border-gray-900 {index ===
											1
												? '-ml-3'
												: ''}"
										/>
									{/each}

									{#if channelMembers.length === 1}
										<div class="absolute bottom-0 right-0">
											<span class="relative flex size-2">
												{#if channelMembers[0]?.is_active}
													<span
														class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"
													></span>
												{/if}
												<span
													class="relative inline-flex size-2 rounded-full {channelMembers[0]
														?.is_active
														? 'bg-green-500'
														: 'bg-gray-300 dark:bg-gray-700'} border-[1.5px] border-white dark:border-gray-900"
												></span>
											</span>
										</div>
									{/if}
								</div>
							{:else}
								<Users className="size-4 ml-1 mr-0.5" strokeWidth="2" />
							{/if}
						{:else}
							<div class=" size-4.5 justify-center flex items-center">
								{#if isPublicChannel(channel)}
									<Hashtag className="size-3.5" strokeWidth="2.5" />
								{:else}
									<Lock className="size-5" strokeWidth="2" />
								{/if}
							</div>
						{/if}

						<div class=" text-left self-center overflow-hidden w-full line-clamp-1 flex-1">
							{#if channel?.name}
								{channel.name}
							{:else}
								{channel?.users
									?.filter((u) => u.id !== $user?.id)
									.map((u) => u.name)
									.join(', ')}
							{/if}
						</div>
					</div>
				{/if}
			</div>

			<div class="self-start flex flex-none items-center text-gray-600 dark:text-gray-400 gap-1">
				{#if channel}
					<Tooltip content={$i18n.t('Pinned Messages')}>
						<button
							class=" flex cursor-pointer py-1.5 px-1.5 border dark:border-gray-850 border-gray-50 rounded-xl text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
							aria-label="Pinned Messages"
							type="button"
							on:click={() => {
								showChannelPinnedMessagesModal = true;
							}}
						>
							<div class=" flex items-center gap-0.5 m-auto self-center">
								<Pin className=" size-4" strokeWidth="1.5" />
							</div>
						</button>
					</Tooltip>

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

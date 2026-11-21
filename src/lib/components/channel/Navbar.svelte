<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { mobile, showSidebar, user } from '$lib/stores';

	import { slide } from 'svelte/transition';
	import { page } from '$app/stores';
	import { getPageContext } from '$lib/utils/page';

	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import PencilSquare from '../icons/PencilSquare.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Sidebar from '../icons/Sidebar.svelte';
	import Hashtag from '../icons/Hashtag.svelte';
	import Lock from '../icons/Lock.svelte';
	import UserAlt from '../icons/UserAlt.svelte';
	import ChannelInfoModal from './ChannelInfoModal.svelte';
	import Users from '../icons/Users.svelte';
	import Pin from '../icons/Pin.svelte';
	import Search from '../icons/Search.svelte';
	import SearchModal from '../layout/SearchModal.svelte';
	import PinnedMessagesModal from './PinnedMessagesModal.svelte';
	import ChannelMenu from './ChannelMenu.svelte';

	const i18n: any = getContext('i18n');
	const { tab: pageTab } = getPageContext();

	let showChannelPinnedMessagesModal = false;
	let showChannelInfoModal = false;
	let showChannelSearchModal = false;

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
	export let readOnly = false;

	export let onPin = (messageId, pinned) => {};
	export let onUpdate = () => {};
</script>

{#if !readOnly}
	{#if showChannelSearchModal}
		<SearchModal
			bind:show={showChannelSearchModal}
			kind="message"
			scope={`channel:${channel.id}`}
		/>
	{/if}
	<PinnedMessagesModal bind:show={showChannelPinnedMessagesModal} {channel} {onPin} />
	<ChannelInfoModal bind:show={showChannelInfoModal} {channel} {onUpdate} />
{/if}
<nav
	class="sticky top-0 z-30 w-full shrink-0 px-1.5 md:px-3 pt-0.5 pb-1 flex items-center drag-region flex-col"
>
	<div class=" flex max-w-full w-full mx-auto bg-transparent">
		<div class="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center w-full max-w-full">
			{#if $mobile && !pageTab}
				<div
					class="{$showSidebar
						? 'md:hidden'
						: ''} col-start-1 row-start-1 mr-1.5 self-start flex flex-none items-center text-base-600 dark:text-base-400"
				>
					<Tooltip
						content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						interactive={true}
					>
						<button
							id="sidebar-toggle-button"
							class="flex cursor-pointer rounded-lg text-base-500 transition hover:bg-base-50/40 hover:text-base-700 dark:text-base-400 dark:hover:bg-base-800/40 dark:hover:text-base-200"
							aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							on:click={() => {
								showSidebar.set(!$showSidebar);
							}}
						>
							<div class=" self-center p-1.5">
								<Sidebar className="size-4" />
							</div>
						</button>
					</Tooltip>
				</div>
			{/if}

			<div
				class="col-start-2 row-start-1 min-w-0 overflow-hidden max-w-full flex items-center
			{$showSidebar ? 'ml-1' : ''}
			"
			>
				{#if channel}
					<div class="flex min-w-0 items-center gap-1.5">
						{#if channel?.type === 'dm'}
							{#if channel?.users}
								{@const channelMembers = channel.users.filter((u) => u.id !== $user?.id)}
								<div class="flex shrink-0 relative">
									{#each channelMembers.slice(0, 2) as u, index}
										<img
											src={`${WEBUI_API_BASE_URL}/users/${u.id}/profile/image`}
											alt={u.name}
											class=" size-5.5 rounded-full object-cover border border-base-0 dark:border-base-900 {index ===
											1
												? '-ml-2'
												: ''}"
										/>
									{/each}

									{#if channelMembers.length === 1}
										<div class="absolute bottom-0 right-0">
											<span class="relative flex size-2">
												<span
													class="relative inline-flex size-2 rounded-full {channelMembers[0]
														?.is_active
														? 'bg-green-500'
														: 'bg-base-300 dark:bg-base-700'} border-[1.5px] border-base-0 dark:border-base-900"
												></span>
											</span>
										</div>
									{/if}
								</div>
							{:else}
								<Users className="size-4" strokeWidth="1.5" />
							{/if}
						{:else}
							<div class=" size-4 shrink-0 justify-center flex items-center">
								{#if isPublicChannel(channel)}
									<Hashtag className="size-3.5" strokeWidth="1.5" />
								{:else}
									<Lock className="size-3.5" strokeWidth="1.5" />
								{/if}
							</div>
						{/if}

						<div
							class="min-w-0 truncate text-left text-[0.9375rem] font-normal text-base-700 dark:text-base-300"
						>
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
				<slot name="status" />
			</div>

			<div
				class="col-start-3 row-start-1 self-center flex flex-none items-center text-base-600 dark:text-base-400 gap-1 shrink-0"
			>
				<slot name="actions">
					{#if channel}
						<Tooltip content={$i18n.t('Pinned Messages')}>
							<button
								class="flex size-6 items-center justify-center cursor-pointer rounded-lg text-base-500 transition hover:bg-base-50/40 hover:text-base-700 dark:text-base-400 dark:hover:bg-base-800/40 dark:hover:text-base-200"
								aria-label={$i18n.t('Pinned Messages')}
								type="button"
								on:click={() => {
									showChannelPinnedMessagesModal = true;
								}}
							>
								<div class=" flex items-center gap-1 m-auto self-center shrink-0">
									<Pin className=" size-3.5" strokeWidth="1.5" />
								</div>
							</button>
						</Tooltip>

						{#if channel?.user_count !== undefined}
							<Tooltip content={$i18n.t('Users')}>
								<button
									class="flex h-6 items-center cursor-pointer shrink-0 px-1.5 rounded-lg text-base-500 transition hover:bg-base-50/40 hover:text-base-700 dark:text-base-400 dark:hover:bg-base-800/40 dark:hover:text-base-200"
									type="button"
									on:click={() => {
										showChannelInfoModal = true;
									}}
								>
									<div class=" flex items-center gap-1 m-auto self-center shrink-0">
										<UserAlt className=" size-4" strokeWidth="1.5" />

										<span class="sr-only">{$i18n.t('User Count')}</span>
										<div class="text-xs tabular-nums shrink-0">
											{channel.user_count}
										</div>
									</div>
								</button>
							</Tooltip>
						{/if}
						<Tooltip content={$i18n.t('Search')}>
							<button
								class="flex size-6 items-center justify-center cursor-pointer rounded-lg text-base-500 transition hover:bg-base-50/40 hover:text-base-700 dark:text-base-400 dark:hover:bg-base-800/40 dark:hover:text-base-200"
								aria-label={$i18n.t('Search')}
								type="button"
								on:click={() => {
									showChannelSearchModal = true;
								}}
							>
								<Search className="size-3.5" strokeWidth="1.5" />
							</button>
						</Tooltip>

						<ChannelMenu {channel} />
					{/if}
				</slot>
			</div>
			{#if $$slots.subtitle}
				<div class="col-start-2 row-start-2 min-w-0 {$showSidebar ? 'ml-1' : ''}">
					<slot name="subtitle" />
				</div>
			{/if}
		</div>
	</div>
</nav>

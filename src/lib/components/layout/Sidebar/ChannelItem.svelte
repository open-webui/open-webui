<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, tick, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

	import { page } from '$app/stores';
	import { channels, mobile, showSidebar, user } from '$lib/stores';
	import { getUserActiveStatusById } from '$lib/apis/users';
	import { updateChannelById, updateChannelMemberActiveStatusById } from '$lib/apis/channels';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import ChannelModal from './ChannelModal.svelte';
	import Lock from '$lib/components/icons/Lock.svelte';
	import Hashtag from '$lib/components/icons/Hashtag.svelte';
	import Users from '$lib/components/icons/Users.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Emoji from '$lib/components/common/Emoji.svelte';

	export let onUpdate: Function = () => {};

	export let className = '';
	export let channel;

	let showEditChannelModal = false;

	let itemElement;
</script>

<ChannelModal
	bind:show={showEditChannelModal}
	{channel}
	edit={true}
	{onUpdate}
	onSubmit={async ({ name, is_private, access_control, group_ids, user_ids }) => {
		const res = await updateChannelById(localStorage.token, channel.id, {
			name,
			is_private,
			access_control,
			group_ids,
			user_ids
		}).catch((error) => {
			toast.error(error.message);
		});

		if (res) {
			toast.success($i18n.t('Channel updated successfully'));
		}

		onUpdate();
	}}
/>

<div
	id="sidebar-channel-item"
	bind:this={itemElement}
	class=" w-full {className} rounded-xl flex relative group hover:bg-gray-100 dark:hover:bg-gray-900 {$page
		.url.pathname === `/channels/${channel.id}`
		? 'bg-gray-100 dark:bg-gray-900 selected'
		: ''} {channel?.type === 'dm' ? 'px-1 py-[3px]' : 'p-1'}  {channel?.unread_count > 0
		? 'font-medium dark:text-white text-black'
		: ' dark:text-gray-400 text-gray-600'} cursor-pointer select-none"
>
	<a
		class=" w-full flex justify-between"
		href="/channels/{channel.id}"
		on:click={() => {
			console.log(channel);

			if ($channels) {
				channels.set(
					$channels.map((ch) => {
						if (ch.id === channel.id) {
							ch.unread_count = 0;
						}
						return ch;
					})
				);
			}

			if ($mobile) {
				showSidebar.set(false);
			}
		}}
		draggable="false"
	>
		<div class="flex items-center gap-1">
			<div>
				{#if channel?.type === 'dm'}
					{#if channel?.users}
						{@const channelMembers = channel.users.filter((u) => u.id !== $user?.id)}
						<div class="flex ml-[1px] mr-0.5 relative">
							{#each channelMembers.slice(0, 2) as u, index}
								<img
									src={`${WEBUI_API_BASE_URL}/users/${u.id}/profile/image`}
									alt={u.name}
									class=" size-5.5 rounded-full border-2 border-white dark:border-gray-900 {index ===
									1
										? '-ml-2.5'
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
											class="relative inline-flex size-2 rounded-full {channelMembers[0]?.is_active
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
					<div class=" size-4 justify-center flex items-center ml-1">
						{#if channel?.type === 'group' ? !channel?.is_private : channel?.access_control === null}
							<Hashtag className="size-3.5" strokeWidth="2.5" />
						{:else}
							<Lock className="size-[15px]" strokeWidth="2" />
						{/if}
					</div>
				{/if}
			</div>

			<div
				class=" text-left self-center overflow-hidden w-full line-clamp-1 flex-1 pr-1 flex items-center gap-2.5"
			>
				{#if channel?.name}
					<span>
						{channel.name}
					</span>
				{:else}
					<span class="shrink-0">
						{channel?.users
							?.filter((u) => u.id !== $user?.id)
							.map((u) => u.name)
							.join(', ')}
					</span>

					{#if channel?.users?.length === 2}
						{@const dmUser = channel.users.find((u) => u.id !== $user?.id)}

						{#if dmUser?.status_emoji || dmUser?.status_message}
							<span class="flex gap-1.5">
								{#if dmUser?.status_emoji}
									<div class=" self-center shrink-0">
										<Emoji className="size-3.5" shortCode={dmUser?.status_emoji} />
									</div>
								{/if}

								<div class="line-clamp-1 italic">
									{dmUser?.status_message}
								</div>
							</span>
						{/if}
					{/if}
				{/if}
			</div>
		</div>

		<div class="flex items-center">
			{#if channel?.unread_count > 0}
				<div
					class="text-xs py-[1px] px-2 rounded-xl bg-gray-100 text-black dark:bg-gray-800 dark:text-white font-medium"
				>
					{new Intl.NumberFormat($i18n.locale, {
						notation: 'compact',
						compactDisplay: 'short'
					}).format(channel.unread_count)}
				</div>
			{/if}
		</div>
	</a>

	{#if ['dm'].includes(channel?.type)}
		<div
			class="ml-0.5 mr-1 invisible group-hover:visible self-center flex items-center dark:text-gray-300"
		>
			<button
				type="button"
				class="p-0.5 dark:hover:bg-gray-850 rounded-lg touch-auto"
				on:click={async (e) => {
					e.stopImmediatePropagation();
					e.stopPropagation();

					channels.update((chs) =>
						chs.filter((ch) => {
							return ch.id !== channel.id;
						})
					);

					await updateChannelMemberActiveStatusById(localStorage.token, channel.id, false).catch(
						(error) => {
							toast.error(`${error}`);
						}
					);
				}}
			>
				<XMark className="size-3.5" />
			</button>
		</div>
	{:else if $user?.role === 'admin' || channel.user_id === $user?.id}
		<div
			class="ml-0.5 mr-1 invisible group-hover:visible self-center flex items-center dark:text-gray-300"
		>
			<button
				type="button"
				class="p-0.5 dark:hover:bg-gray-850 rounded-lg touch-auto"
				on:click={(e) => {
					e.stopImmediatePropagation();
					e.stopPropagation();
					showEditChannelModal = true;
				}}
			>
				<Cog6 className="size-3.5" />
			</button>
		</div>
	{/if}
</div>

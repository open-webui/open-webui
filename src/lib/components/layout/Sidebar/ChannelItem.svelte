<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, tick, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

	import { page } from '$app/stores';
	import { channels, mobile, showSidebar, user } from '$lib/stores';
	import { updateChannelById } from '$lib/apis/channels';

	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import ChannelModal from './ChannelModal.svelte';
	import Lock from '$lib/components/icons/Lock.svelte';
	import Hashtag from '$lib/components/icons/Hashtag.svelte';

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
	onSubmit={async ({ name, access_control }) => {
		const res = await updateChannelById(localStorage.token, channel.id, {
			name,
			access_control
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
		: ''} px-2.5 py-1 {channel?.unread_count > 0
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
		<div class="flex items-center gap-1 shrink-0">
			<div class=" size-4 justify-center flex items-center">
				{#if channel?.access_control === null}
					<Hashtag className="size-3" strokeWidth="2.5" />
				{:else}
					<Lock className="size-[15px]" strokeWidth="2" />
				{/if}
			</div>

			<div class=" text-left self-center overflow-hidden w-full line-clamp-1 flex-1">
				{channel.name}
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

			{#if $user?.role === 'admin'}
				<div
					class="right-2 invisible group-hover:visible self-center flex items-center dark:text-gray-300"
					on:click={(e) => {
						e.stopPropagation();
						showEditChannelModal = true;
					}}
				>
					<button class="p-0.5 dark:hover:bg-gray-850 rounded-lg touch-auto" on:click={(e) => {}}>
						<Cog6 className="size-3.5" />
					</button>
				</div>
			{/if}
		</div>
	</a>
</div>

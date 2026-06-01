<script lang="ts">
	import { getContext } from 'svelte';
	import dayjs from 'dayjs';
	import calendar from 'dayjs/plugin/calendar';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Loader from '$lib/components/common/Loader.svelte';

	dayjs.extend(calendar);

	const i18n = getContext('i18n');

	export let chatList: Array<{
		id: string;
		title: string;
		updated_at: number;
		user_id?: string;
		user_name?: string;
		time_range?: string;
	}> | null = null;
	export let loading = false;
	export let allLoaded = false;
	export let showUserInfo = false;
	export let shareUrl = false;
	export let emptyMessage = 'No chats found';
	export let onLoadMore: (() => void) | null = null;
	export let onChatClick: ((chatId: string) => void) | null = null;
</script>

<div>
	{#if chatList && chatList.length > 0}
		<div class="flex text-xs font-medium mb-1.5">
			{#if showUserInfo}
				<div class="px-1.5 py-1 w-32">
					{$i18n.t('User')}
				</div>
			{/if}
			<div class="px-1.5 py-1 {showUserInfo ? 'flex-1' : 'basis-3/5'}">
				{$i18n.t('Title')}
			</div>
			<div class="px-1.5 py-1 hidden sm:flex {showUserInfo ? 'w-28' : 'basis-2/5'} justify-end">
				{$i18n.t('Updated at')}
			</div>
		</div>
	{/if}
	<div class="max-h-[22rem] overflow-y-scroll">
		{#if loading && (!chatList || chatList.length === 0)}
			<div class="flex justify-center py-8">
				<Spinner />
			</div>
		{:else if !chatList || chatList.length === 0}
			<div class="text-center text-gray-500 text-sm py-8">
				{$i18n.t(emptyMessage)}
			</div>
		{:else}
			{#each chatList as chat, idx (chat.id)}
				{#if chat.time_range && (idx === 0 || chat.time_range !== chatList[idx - 1]?.time_range)}
					<div
						class="w-full text-xs text-gray-500 dark:text-gray-500 font-medium {idx === 0
							? ''
							: 'pt-5'} pb-2 px-2"
					>
						{$i18n.t(chat.time_range)}
					</div>
				{/if}

				<div
					class="w-full flex items-center rounded-lg text-sm py-2 px-3 hover:bg-gray-50 dark:hover:bg-gray-850"
				>
					{#if showUserInfo && chat.user_id}
						<div class="w-32 shrink-0 flex items-center gap-2">
							<img
								src="{WEBUI_API_BASE_URL}/users/{chat.user_id}/profile/image"
								alt={chat.user_name || 'User'}
								class="size-5 rounded-full object-cover shrink-0"
							/>
							<span class="text-xs text-gray-600 dark:text-gray-400 truncate"
								>{chat.user_name || 'Unknown'}</span
							>
						</div>
					{/if}
					<a
						class={showUserInfo ? 'flex-1' : 'basis-3/5'}
						href={shareUrl ? `/s/${chat.id}` : `/c/${chat.id}`}
						on:click={() => onChatClick?.(chat.id)}
					>
						<div class="text-ellipsis line-clamp-1 w-full">
							{chat.title}
						</div>
					</a>

					<div class="{showUserInfo ? 'w-28' : 'basis-2/5'} flex items-center justify-end">
						<div class="hidden sm:flex text-gray-500 dark:text-gray-400 text-xs">
							{dayjs(chat.updated_at * 1000).calendar(null, {
								sameDay: '[Today] h:mm A',
								lastDay: '[Yesterday] h:mm A',
								lastWeek: 'MMM D',
								sameElse: 'MMM D, YYYY'
							})}
						</div>
					</div>
				</div>
			{/each}

			{#if !allLoaded && onLoadMore}
				<Loader
					on:visible={() => {
						if (!loading) {
							onLoadMore();
						}
					}}
				>
					<div class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2">
						<Spinner className="size-4" />
						<div>{$i18n.t('Loading...')}</div>
					</div>
				</Loader>
			{/if}
		{/if}
	</div>
</div>

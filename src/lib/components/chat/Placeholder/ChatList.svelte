<script lang="ts">
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import { getTimeRange } from '$lib/utils';

	dayjs.extend(localizedFormat);

	export let chats = [];

	let chatList = null;

	const init = async () => {
		if (chats.length === 0) {
			chatList = [];
		} else {
			chatList = chats.map((chat) => ({
				...chat,
				time_range: getTimeRange(chat.updated_at)
			}));
		}
	};

	$: if (chats) {
		init();
	}
</script>

{#if chatList}
	<div class="text-left text-sm w-full mb-3">
		{#if chatList.length === 0}
			<div
				class="text-xs text-gray-500 dark:text-gray-400 text-center px-5 min-h-20 w-full h-full flex justify-center items-center"
			>
				{$i18n.t('No chats found')}
			</div>
		{/if}

		{#each chatList as chat, idx (chat.id)}
			{#if (idx === 0 || (idx > 0 && chat.time_range !== chatList[idx - 1].time_range)) && chat?.time_range}
				<div
					class="w-full text-xs text-gray-500 dark:text-gray-500 font-medium {idx === 0
						? ''
						: 'pt-5'} pb-2 px-2"
				>
					{$i18n.t(chat.time_range)}
					<!-- localisation keys for time_range to be recognized from the i18next parser (so they don't get automatically removed):
							{$i18n.t('Today')}
							{$i18n.t('Yesterday')}
							{$i18n.t('Previous 7 days')}
							{$i18n.t('Previous 30 days')}
							{$i18n.t('January')}
							{$i18n.t('February')}
							{$i18n.t('March')}
							{$i18n.t('April')}
							{$i18n.t('May')}
							{$i18n.t('June')}
							{$i18n.t('July')}
							{$i18n.t('August')}
							{$i18n.t('September')}
							{$i18n.t('October')}
							{$i18n.t('November')}
							{$i18n.t('December')}
							-->
				</div>
			{/if}

			<a
				class=" w-full flex justify-between items-center rounded-lg text-sm py-2 px-3 hover:bg-gray-50 dark:hover:bg-gray-850"
				draggable="false"
				href={`/c/${chat.id}`}
				on:click={() => (show = false)}
			>
				<div class="text-ellipsis line-clamp-1 w-full sm:basis-3/5">
					{chat?.title}
				</div>

				<div class="hidden sm:flex sm:basis-2/5 items-center justify-end">
					<div class=" text-gray-500 dark:text-gray-400 text-xs">
						{dayjs(chat?.updated_at * 1000).calendar()}
					</div>
				</div>
			</a>
		{/each}

		<!-- {#if !allChatsLoaded && loadHandler}
		<Loader
			on:visible={(e) => {
				if (!chatListLoading) {
					loadHandler();
				}
			}}
		>
			<div class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2">
				<Spinner className=" size-4" />
				<div class=" ">Loading...</div>
			</div>
		</Loader>
	{/if} -->
	</div>
{/if}

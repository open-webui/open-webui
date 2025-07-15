<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import SearchInput from './Sidebar/SearchInput.svelte';
	import { getChatList, getChatListBySearchText } from '$lib/apis/chats';
	import Spinner from '../common/Spinner.svelte';

	import dayjs from '$lib/dayjs';
	import calendar from 'dayjs/plugin/calendar';
	import Loader from '../common/Loader.svelte';
	dayjs.extend(calendar);

	export let show = false;
	export let onClose = () => {};

	let query = '';
	let page = 1;

	let chatList = null;

	let chatListLoading = false;
	let allChatsLoaded = false;

	let searchDebounceTimeout;

	let selectedIdx = 0;

	const searchHandler = async () => {
		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}

		page = 1;
		chatList = null;
		if (query === '') {
			chatList = await getChatList(localStorage.token, page);
		} else {
			searchDebounceTimeout = setTimeout(async () => {
				chatList = await getChatListBySearchText(localStorage.token, query, page);
			}, 500);
		}

		if ((chatList ?? []).length === 0) {
			allChatsLoaded = true;
		} else {
			allChatsLoaded = false;
		}
	};

	const loadMoreChats = async () => {
		chatListLoading = true;
		page += 1;

		let newChatList = [];

		if (query) {
			newChatList = await getChatListBySearchText(localStorage.token, query, page);
		} else {
			newChatList = await getChatList(localStorage.token, page);
		}

		// once the bottom of the list has been reached (no results) there is no need to continue querying
		allChatsLoaded = newChatList.length === 0;

		if (newChatList.length > 0) {
			chatList = [...chatList, ...newChatList];
		}

		chatListLoading = false;
	};

	const init = () => {
		searchHandler();
	};

	onMount(() => {
		init();
	});
</script>

<Modal size="md" bind:show>
	<div class="py-2.5 dark:text-gray-300 text-gray-700">
		<div class="px-3.5 pb-1.5">
			<SearchInput
				bind:value={query}
				on:input={searchHandler}
				placeholder={$i18n.t('Search')}
				showClearButton={true}
				onKeydown={(e) => {
					console.log('e', e);

					if (e.code === 'Enter' && (chatList ?? []).length > 0) {
						const item = document.querySelector(`[data-arrow-selected="true"]`);
						if (item) {
							item?.click();
						}

						show = false;
						return;
					} else if (e.code === 'ArrowDown') {
						selectedIdx = Math.min(selectedIdx + 1, (chatList ?? []).length - 1);
					} else if (e.code === 'ArrowUp') {
						selectedIdx = Math.max(selectedIdx - 1, 0);
					} else {
						selectedIdx = 0;
					}

					const item = document.querySelector(`[data-arrow-selected="true"]`);
					item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
				}}
			/>
		</div>

		<!-- <hr class="border-gray-100 dark:border-gray-850 my-1" /> -->

		<div class="flex flex-col overflow-y-auto h-80 scrollbar-hidden px-3 pb-1">
			{#if chatList}
				{#if chatList.length === 0}
					<div class="text-xs text-gray-500 dark:text-gray-400 text-center px-5">
						{$i18n.t('No results found')}
					</div>
				{/if}

				{#each chatList as chat, idx (chat.id)}
					{#if idx === 0 || (idx > 0 && chat.time_range !== chatList[idx - 1].time_range)}
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
						class=" w-full flex justify-between items-center rounded-lg text-sm py-2 px-3 hover:bg-gray-50 dark:hover:bg-gray-850 {selectedIdx ===
						idx
							? 'bg-gray-50 dark:bg-gray-850'
							: ''}"
						href="/c/{chat.id}"
						draggable="false"
						data-arrow-selected={selectedIdx === idx ? 'true' : undefined}
						on:mouseenter={() => {
							selectedIdx = idx;
						}}
						on:click={() => {
							show = false;
							onClose();
						}}
					>
						<div class=" flex-1">
							<div class="text-ellipsis line-clamp-1 w-full">
								{chat?.title}
							</div>
						</div>

						<div class=" pl-3 shrink-0 text-gray-500 dark:text-gray-400 text-xs">
							{dayjs(chat?.updated_at * 1000).calendar()}
						</div>
					</a>
				{/each}

				{#if !allChatsLoaded}
					<Loader
						on:visible={(e) => {
							if (!chatListLoading) {
								loadMoreChats();
							}
						}}
					>
						<div class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2">
							<Spinner className=" size-4" />
							<div class=" ">Loading...</div>
						</div>
					</Loader>
				{/if}
			{:else}
				<div class="w-full h-full flex justify-center items-center">
					<Spinner className="size-5" />
				</div>
			{/if}
		</div>
	</div>
</Modal>

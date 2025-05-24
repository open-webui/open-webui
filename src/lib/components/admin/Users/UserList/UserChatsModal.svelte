<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { getContext, createEventDispatcher } from 'svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	const dispatch = createEventDispatcher();
	dayjs.extend(localizedFormat);

	import { getChatListByUserId, deleteChatById } from '$lib/apis/chats';

	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let user;

	let chats = null;
	let showDeleteConfirmDialog = false;
	let chatToDelete = null;
	let searchValue = '';
	let sortKey = 'updated_at';
	let sortOrder = 'desc';

	function setSortKey(key: 'title' | 'updated_at') {
		if (sortKey === key) {
			sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortOrder = key === 'updated_at' ? 'desc' : 'asc';
		}
	}

	const fetchUserChats = async (userId) => {
		try {
			chats = await getChatListByUserId(localStorage.token, userId);
		} catch (error) {
			toast.error(`${error}`);
			chats = [];
		}
	};

	const resetModalState = () => {
		chats = null;
		searchValue = '';
		sortKey = 'updated_at';
		sortOrder = 'desc';
		chatToDelete = null;
	};

	const deleteChatHandler = async (chatId) => {
		showDeleteConfirmDialog = false;

		await deleteChatById(localStorage.token, chatId).catch((error) => {
			toast.error(`${error}`);
		});

		if (show && user?.id) {
			fetchUserChats(user.id);
		}
	};

	$: if (show && user?.id && chats === null) {
		fetchUserChats(user.id);
	} else if (!show) {
	}
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		if (chatToDelete) {
			deleteChatHandler(chatToDelete);
		}
	}}
	on:cancel={() => {
		chatToDelete = null;
	}}
/>

<Modal size="lg" bind:show>
	<div class=" flex justify-between dark:text-gray-300 px-5 pt-4">
		<div class=" text-lg font-medium self-center capitalize">
			{#if user}
				{$i18n.t("{{user}}'s Chats", { user: user.name })}
			{:else}
				{$i18n.t('User Chats')}
			{/if}
		</div>
		<button
			class="self-center"
			on:click={() => {
				show = false;
			}}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="w-5 h-5"
			>
				<path
					d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
				/>
			</svg>
		</button>
	</div>

	<div class="flex flex-col w-full px-5 pt-2 pb-4 dark:text-gray-200">
		<div class=" flex w-full mt-2 space-x-2">
			<div class="flex flex-1">
				<div class=" self-center ml-1 mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							fill-rule="evenodd"
							d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<input
					class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={searchValue}
					placeholder={$i18n.t('Search Chats')}
				/>
			</div>
		</div>
		<hr class="border-gray-100 dark:border-gray-850 my-2" />

		<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
			{#if chats === null}
				<Spinner />
			{:else if chats.length > 0}
				{@const filteredChats = chats.filter(
					(chat) =>
						searchValue === '' ||
						(chat.title ?? '').toLowerCase().includes(searchValue.toLowerCase())
				)}

				{#if filteredChats.length > 0}
					<div class="text-left text-sm w-full mb-4 max-h-[22rem] overflow-y-scroll">
						<div class="relative overflow-x-auto">
							<table class="w-full text-sm text-left text-gray-600 dark:text-gray-400 table-auto">
								<thead
									class="text-xs text-gray-700 uppercase bg-transparent dark:text-gray-200 border-b-2 dark:border-gray-850"
								>
									<tr>
										<th
											scope="col"
											class="px-3 py-2 cursor-pointer select-none"
											on:click={() => setSortKey('title')}
										>
											{$i18n.t('Title')}
											{#if sortKey === 'title'}
												{sortOrder === 'asc' ? '▲' : '▼'}
											{:else}
												<span class="invisible">▲</span>
											{/if}
										</th>
										<th
											scope="col"
											class="px-3 py-2 hidden md:flex cursor-pointer select-none justify-end"
											on:click={() => setSortKey('updated_at')}
										>
											{$i18n.t('Updated at')}
											{#if sortKey === 'updated_at'}
												{sortOrder === 'asc' ? '▲' : '▼'}
											{:else}
												<span class="invisible">▲</span>
											{/if}
										</th>
										<th scope="col" class="px-3 py-2 text-right" />
									</tr>
								</thead>
								<tbody>
									{#each filteredChats.sort((a, b) => {
										const aValue = a[sortKey];
										const bValue = b[sortKey];

										if (aValue == null && bValue == null) return 0;
										if (aValue == null) return sortOrder === 'asc' ? -1 : 1;
										if (bValue == null) return sortOrder === 'asc' ? 1 : -1;

										if (typeof aValue === 'string' && typeof bValue === 'string') {
											return sortOrder === 'asc' ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
										} else {
											if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
											if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
											return 0;
										}
									}) as chat, idx}
										<tr
											class="bg-transparent {idx !== filteredChats.length - 1 &&
												'border-b'} dark:bg-gray-900 dark:border-gray-850 text-xs"
										>
											<td class="px-3 py-1">
												<a href="/s/{chat.id}" target="_blank">
													<div class=" underline line-clamp-1 max-w-96">
														{chat.title}
													</div>
												</a>
											</td>

											<td class=" px-3 py-1 hidden md:flex h-[2.5rem] justify-end">
												<div class="my-auto shrink-0">
													{dayjs(chat.updated_at * 1000).format('LLL')}
												</div>
											</td>

											<td class="px-3 py-1 text-right">
												<div class="flex justify-end w-full">
													<Tooltip content={$i18n.t('Delete Chat')}>
														<button
															class="self-center w-fit text-sm px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
															on:click={() => {
																chatToDelete = chat.id;
																showDeleteConfirmDialog = true;
															}}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																fill="none"
																viewBox="0 0 24 24"
																stroke-width="1.5"
																stroke="currentColor"
																class="w-4 h-4"
															>
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
																/>
															</svg>
														</button>
													</Tooltip>
												</div>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>
				{:else}
					<div class="text-left text-sm w-full mb-8">
						{$i18n.t('No chats found matching your search.')}
					</div>
				{/if}
			{:else}
				<div class="text-left text-sm w-full mb-8">
					{user?.name ?? 'User'}
					{$i18n.t('has no conversations.')}
				</div>
			{/if}
		</div>
	</div>
</Modal>

<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { getContext, createEventDispatcher } from 'svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	dayjs.extend(localizedFormat);

	const dispatch = createEventDispatcher();

	import {
		archiveChatById,
		deleteChatById,
		getAllArchivedChats,
		getArchivedChatList
	} from '$lib/apis/chats';

	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import UnarchiveAllConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	let chats = [];

	let searchValue = '';
	let showUnarchiveAllConfirmDialog = false;

	let sortField = 'created_at';
	let sortDirection = 'desc';

	const unarchiveChatHandler = async (chatId) => {
		const res = await archiveChatById(localStorage.token, chatId).catch((error) => {
			toast.error(`${error}`);
		});

		chats = await getArchivedChatList(localStorage.token);
		dispatch('change');
	};

	const deleteChatHandler = async (chatId) => {
		const res = await deleteChatById(localStorage.token, chatId).catch((error) => {
			toast.error(`${error}`);
		});

		chats = await getArchivedChatList(localStorage.token);
		dispatch('change');
	};

	const exportChatsHandler = async () => {
		const chatsToExport = await getAllArchivedChats(localStorage.token);
		let blob = new Blob([JSON.stringify(chatsToExport)], {
			type: 'application/json'
		});
		saveAs(blob, `${$i18n.t('archived-chat-export')}-${Date.now()}.json`);
	};

	const unarchiveAllHandler = async () => {
		const chatsToUnarchive = [...chats];
		let success = true;

		for (const chat of chatsToUnarchive) {
			await archiveChatById(localStorage.token, chat.id).catch((err) => {
				console.error(`Failed to unarchive chat ${chat.id}:`, err);
				toast.error($i18n.t('Error unarchiving chat {{title}}', { title: chat.title }));
				success = false;
			});
		}

		chats = await getArchivedChatList(localStorage.token);
		if (success) {
			toast.success($i18n.t('All chats unarchived successfully.'));
		} else {
			toast.warning($i18n.t('Some chats could not be unarchived. Please check the list.'));
		}
		dispatch('change');
	};

	const toggleSort = (field) => {
		if (sortField === field) {
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			sortField = field;
			sortDirection = 'asc';
		}
	};

	$: if (show) {
		(async () => {
			chats = await getArchivedChatList(localStorage.token);
			// Optionally reset sort when modal opens, or keep the last sort state
			// sortField = 'created_at';
			// sortDirection = 'desc';
		})();
	}

	$: sortedChats = [...chats]
		.filter((c) => searchValue === '' || c.title.toLowerCase().includes(searchValue.toLowerCase()))
		.sort((a, b) => {
			let comparison = 0;
			if (sortField === 'title') {
				comparison = a.title.localeCompare(b.title, undefined, { sensitivity: 'base' });
			} else if (sortField === 'created_at') {
				comparison = a.created_at - b.created_at;
			}
			return sortDirection === 'asc' ? comparison : -comparison;
		});
</script>

<UnarchiveAllConfirmDialog
	bind:show={showUnarchiveAllConfirmDialog}
	title={$i18n.t('Confirm Unarchive All')}
	confirmLabel={$i18n.t('Unarchive All')}
	on:confirm={() => {
		unarchiveAllHandler();
	}}
>
	<div class=" text-sm text-gray-500 dark:text-gray-400">
		{$i18n.t('Are you sure you want to unarchive all {{count}} archived chats?', {
			count: chats.length
		})}
	</div>
</UnarchiveAllConfirmDialog>

<Modal size="lg" bind:show on:close={() => (searchValue = '')}>
	<div>
		<div class=" flex justify-between items-center dark:text-gray-300 px-5 pt-4 pb-1">
			<div class="flex items-center text-lg font-medium">
				{$i18n.t('Archived Chats')}
				{#if chats.length > 0}
					<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-100 dark:bg-gray-850" />
					<span class="text-base font-medium text-gray-500 dark:text-gray-300">
						{sortedChats.length}
					</span>
				{/if}
			</div>
			<button
				class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
				aria-label={$i18n.t('Close')}
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
						fill-rule="evenodd"
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		</div>

		<div class="flex flex-col w-full px-5 pb-4 dark:text-gray-200">
			<div class=" flex w-full mt-2 space-x-2">
				<div
					class="flex flex-1 items-center border border-gray-200 dark:border-gray-700 rounded-lg px-2"
				>
					<div class=" self-center mr-2 text-gray-500 dark:text-gray-400">
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
						class=" w-full text-sm py-1 bg-transparent outline-none"
						bind:value={searchValue}
						placeholder={$i18n.t('Search Chats')}
					/>
				</div>
			</div>
			<hr class="border-gray-100 dark:border-gray-850 my-3" />

			{#if chats.length > 0}
				<div class="w-full">
					<div class="text-left text-sm w-full mb-3 max-h-[50vh] overflow-y-auto pr-1">
						<table class="w-full text-sm text-left text-gray-600 dark:text-gray-400 table-auto">
							<thead
								class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-800 dark:text-gray-300 sticky top-0 z-10"
							>
								<tr>
									<th
										scope="col"
										class="px-3 py-2.5 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors rounded-tl-md bg-gray-50 dark:bg-gray-800"
										on:click={() => toggleSort('title')}
									>
										<div class="flex items-center">
											{$i18n.t('Name')}
											{#if sortField === 'title'}
												<span class="ml-1 w-4 h-4">
													{#if sortDirection === 'asc'}
														<ChevronUp />
													{:else}
														<ChevronDown />
													{/if}
												</span>
											{/if}
										</div>
									</th>
									<th
										scope="col"
										class="px-3 py-2.5 hidden md:table-cell cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors bg-gray-50 dark:bg-gray-800"
										on:click={() => toggleSort('created_at')}
									>
										<div class="flex items-center">
											{$i18n.t('Created At')}
											{#if sortField === 'created_at'}
												<span class="ml-1 w-4 h-4">
													{#if sortDirection === 'asc'}
														<ChevronUp />
													{:else}
														<ChevronDown />
													{/if}
												</span>
											{/if}
										</div>
									</th>
									<th
										scope="col"
										class="px-3 py-2.5 text-right rounded-tr-md bg-gray-50 dark:bg-gray-800"
									/>
								</tr>
							</thead>
							<tbody>
								{#each sortedChats as chat (chat.id)}
									<tr
										class="bg-white dark:bg-gray-900 border-b dark:border-gray-800 text-xs hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
									>
										<td class="px-3 py-2.5 w-2/3 font-medium text-gray-900 dark:text-white">
											<a href="/c/{chat.id}" target="_blank" class="hover:underline line-clamp-1">
												{chat.title}
											</a>
										</td>

										<td class=" px-3 py-2.5 hidden md:table-cell">
											<div class="my-auto whitespace-nowrap">
												{dayjs(chat.created_at * 1000).format('LLL')}
											</div>
										</td>

										<td class="px-3 py-2.5 text-right">
											<div class="flex justify-end items-center space-x-1">
												<Tooltip content={$i18n.t('Unarchive Chat')}>
													<button
														class="p-1.5 rounded-md text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
														aria-label={$i18n.t('Unarchive {{title}}', { title: chat.title })}
														on:click={() => {
															unarchiveChatHandler(chat.id);
														}}
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															fill="none"
															viewBox="0 0 24 24"
															stroke-width="1.5"
															stroke="currentColor"
															class="size-4"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																d="M9 8.25H7.5a2.25 2.25 0 0 0-2.25 2.25v9a2.25 2.25 0 0 0 2.25 2.25h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25H15m0-3-3-3m0 0-3 3m3-3V15"
															/>
														</svg>
													</button>
												</Tooltip>

												<Tooltip content={$i18n.t('Delete Chat')}>
													<button
														class="p-1.5 rounded-md text-red-500 dark:text-red-500 hover:bg-red-100 dark:hover:bg-red-900/50 hover:text-red-700 dark:hover:text-red-400 transition-colors"
														aria-label={$i18n.t('Delete {{title}}', { title: chat.title })}
														on:click={() => {
															deleteChatHandler(chat.id);
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
								{:else}
									{#if searchValue !== ''}
										<tr>
											<td colspan="3" class="text-center py-4 text-gray-500 dark:text-gray-400">
												{$i18n.t('No chats found matching your search.')}
											</td>
										</tr>
									{/if}
								{/each}
							</tbody>
						</table>
					</div>

					<div class="flex flex-wrap text-sm font-medium gap-2 mt-2 justify-end w-full">
						<button
							class=" px-3 py-1.5 font-medium text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg transition-colors"
							on:click={() => {
								showUnarchiveAllConfirmDialog = true;
							}}
						>
							{$i18n.t('Unarchive All')}
						</button>

						<button
							class="px-3 py-1.5 font-medium text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg transition-colors"
							on:click={() => {
								exportChatsHandler();
							}}
						>
							{$i18n.t('Export All')}
						</button>
					</div>
				</div>
			{:else if searchValue === ''}
				<div class="text-center text-sm w-full py-8 text-gray-500 dark:text-gray-400">
					{$i18n.t('You have no archived conversations.')}
				</div>
			{/if}
		</div>
	</div>
</Modal>

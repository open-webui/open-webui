<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { getContext, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	import Modal from '$lib/components/common/Modal.svelte';
	import {
		archiveChatById,
		deleteChatById,
		getAllArchivedChats,
		getArchivedChatList
	} from '$lib/apis/chats';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	let searchValue = '';

	let chats = [];

	const unarchiveChatHandler = async (chatId) => {
		const res = await archiveChatById(localStorage.token, chatId).catch((error) => {
			toast.error(error);
		});

		chats = await getArchivedChatList(localStorage.token);

		dispatch('change');
	};

	const deleteChatHandler = async (chatId) => {
		const res = await deleteChatById(localStorage.token, chatId).catch((error) => {
			toast.error(error);
		});

		chats = await getArchivedChatList(localStorage.token);
	};

	const exportChatsHandler = async () => {
		const chats = await getAllArchivedChats(localStorage.token);
		let blob = new Blob([JSON.stringify(chats)], {
			type: 'application/json'
		});
		saveAs(blob, `archived-chat-export-${Date.now()}.json`);
	};

	$: if (show) {
		(async () => {
			chats = await getArchivedChatList(localStorage.token);
		})();
	}
</script>

<Modal size="lg" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-1">
			<div class=" text-lg font-medium self-center">{$i18n.t('Archived Chats')}</div>
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

		<div class="flex flex-col w-full px-5 pb-4 dark:text-gray-200">
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
						class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-none bg-transparent"
						bind:value={searchValue}
						placeholder={$i18n.t('Search Chats')}
					/>
				</div>
			</div>
			<hr class=" dark:border-gray-850 my-2" />
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				{#if chats.length > 0}
					<div class="w-full">
						<div class="text-left text-sm w-full mb-3 max-h-[22rem] overflow-y-scroll">
							<div class="relative overflow-x-auto">
								<table class="w-full text-sm text-left text-gray-600 dark:text-gray-400 table-auto">
									<thead
										class="text-xs text-gray-700 uppercase bg-transparent dark:text-gray-200 border-b-2 dark:border-gray-800"
									>
										<tr>
											<th scope="col" class="px-3 py-2"> {$i18n.t('Name')} </th>
											<th scope="col" class="px-3 py-2 hidden md:flex">
												{$i18n.t('Created At')}
											</th>
											<th scope="col" class="px-3 py-2 text-right" />
										</tr>
									</thead>
									<tbody>
										{#each chats.filter((c) => searchValue === '' || c.title
													.toLowerCase()
													.includes(searchValue.toLowerCase())) as chat, idx}
											<tr
												class="bg-transparent {idx !== chats.length - 1 &&
													'border-b'} dark:bg-gray-900 dark:border-gray-850 text-xs"
											>
												<td class="px-3 py-1 w-2/3">
													<a href="/c/{chat.id}" target="_blank">
														<div class=" underline line-clamp-1">
															{chat.title}
														</div>
													</a>
												</td>

												<td class=" px-3 py-1 hidden md:flex h-[2.5rem]">
													<div class="my-auto">
														{dayjs(chat.created_at * 1000).format($i18n.t('MMMM DD, YYYY HH:mm'))}
													</div>
												</td>

												<td class="px-3 py-1 text-right">
													<div class="flex justify-end w-full">
														<Tooltip content="Unarchive Chat">
															<button
																class="self-center w-fit text-sm px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
																on:click={async () => {
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

														<Tooltip content="Delete Chat">
															<button
																class="self-center w-fit text-sm px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
																on:click={async () => {
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
										{/each}
									</tbody>
								</table>
							</div>
						</div>

						<div class="flex flex-wrap text-sm font-medium gap-1.5 mt-2 m-1">
							<button
								class=" px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-300 dark:outline-gray-800 rounded-3xl"
								on:click={() => {
									exportChatsHandler();
								}}>Export All Archived Chats</button
							>
						</div>
					</div>
				{:else}
					<div class="text-left text-sm w-full mb-8">
						{$i18n.t('You have no archived conversations.')}
					</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>

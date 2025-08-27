<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';

	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	dayjs.extend(localizedFormat);

	import { deleteChatById } from '$lib/apis/chats';

	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import Spinner from '../common/Spinner.svelte';
	import Loader from '../common/Loader.svelte';
	import XMark from '../icons/XMark.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	export let title = 'Chats';
	export let emptyPlaceholder = '';
	export let shareUrl = false;

	export let query = '';

	export let orderBy = 'updated_at';
	export let direction = 'desc'; // 'asc' or 'desc'

	export let chatList = null;
	export let allChatsLoaded = false;
	export let chatListLoading = false;

	let selectedChatId = null;
	let selectedIdx = 0;
	let showDeleteConfirmDialog = false;

	export let onUpdate = () => {};

	export let loadHandler: null | Function = null;
	export let unarchiveHandler: null | Function = null;

	const setSortKey = (key) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = 'asc';
		}
	};

	const deleteHandler = async (chatId) => {
		const res = await deleteChatById(localStorage.token, chatId).catch((error) => {
			toast.error(`${error}`);
		});

		onUpdate();
	};
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		if (selectedChatId) {
			deleteHandler(selectedChatId);
			selectedChatId = null;
		}
	}}
/>

<Modal size="lg" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-1">
			<div class=" text-lg font-medium self-center">{title}</div>
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
						fill-rule="evenodd"
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		</div>

		<div class="flex flex-col w-full px-5 pb-4 dark:text-gray-200">
			<div class=" flex w-full space-x-2 mb-0.5">
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
						bind:value={query}
						placeholder={$i18n.t('Search Chats')}
					/>

					{#if query}
						<div class="self-center pl-1.5 pr-1 translate-y-[0.5px] rounded-l-xl bg-transparent">
							<button
								class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
								on:click={() => {
									query = '';
									selectedIdx = 0;
								}}
							>
								<XMark className="size-3" strokeWidth="2" />
							</button>
						</div>
					{/if}
				</div>
			</div>

			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				{#if chatList}
					<div class="w-full">
						{#if chatList.length > 0}
							<div class="flex text-xs font-medium mb-1.5">
								<button
									class="px-1.5 py-1 cursor-pointer select-none basis-3/5"
									on:click={() => setSortKey('title')}
								>
									<div class="flex gap-1.5 items-center">
										{$i18n.t('Title')}

										{#if orderBy === 'title'}
											<span class="font-normal"
												>{#if direction === 'asc'}
													<ChevronUp className="size-2" />
												{:else}
													<ChevronDown className="size-2" />
												{/if}
											</span>
										{:else}
											<span class="invisible">
												<ChevronUp className="size-2" />
											</span>
										{/if}
									</div>
								</button>
								<button
									class="px-1.5 py-1 cursor-pointer select-none hidden sm:flex sm:basis-2/5 justify-end"
									on:click={() => setSortKey('updated_at')}
								>
									<div class="flex gap-1.5 items-center">
										{$i18n.t('Updated at')}

										{#if orderBy === 'updated_at'}
											<span class="font-normal"
												>{#if direction === 'asc'}
													<ChevronUp className="size-2" />
												{:else}
													<ChevronDown className="size-2" />
												{/if}
											</span>
										{:else}
											<span class="invisible">
												<ChevronUp className="size-2" />
											</span>
										{/if}
									</div>
								</button>
							</div>
						{/if}
						<div class="text-left text-sm w-full mb-3 max-h-[22rem] overflow-y-scroll">
							{#if chatList.length === 0}
								<div
									class="text-xs text-gray-500 dark:text-gray-400 text-center px-5 min-h-20 w-full h-full flex justify-center items-center"
								>
									{$i18n.t('No results found')}
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

								<div
									class=" w-full flex justify-between items-center rounded-lg text-sm py-2 px-3 hover:bg-gray-50 dark:hover:bg-gray-850"
									draggable="false"
								>
									<a
										class=" basis-3/5"
										href={shareUrl ? `/s/${chat.id}` : `/c/${chat.id}`}
										on:click={() => (show = false)}
									>
										<div class="text-ellipsis line-clamp-1 w-full">
											{chat?.title}
										</div>
									</a>

									<div class="basis-2/5 flex items-center justify-end">
										<div class="hidden sm:flex text-gray-500 dark:text-gray-400 text-xs">
											{dayjs(chat?.updated_at * 1000).calendar()}
										</div>

										<div class="flex justify-end pl-2.5 text-gray-600 dark:text-gray-300">
											{#if unarchiveHandler}
												<Tooltip content={$i18n.t('Unarchive Chat')}>
													<button
														class="self-center w-fit px-1 text-sm rounded-xl"
														on:click={async (e) => {
															e.stopImmediatePropagation();
															e.stopPropagation();
															unarchiveHandler(chat.id);
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
											{/if}

											<Tooltip content={$i18n.t('Delete Chat')}>
												<button
													class="self-center w-fit px-1 text-sm rounded-xl"
													on:click={async (e) => {
														e.stopImmediatePropagation();
														e.stopPropagation();
														selectedChatId = chat.id;
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
									</div>
								</div>
							{/each}

							{#if !allChatsLoaded && loadHandler}
								<Loader
									on:visible={(e) => {
										if (!chatListLoading) {
											loadHandler();
										}
									}}
								>
									<div
										class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2"
									>
										<Spinner className=" size-4" />
										<div class=" ">{$i18n.t('Loading...')}</div>
									</div>
								</Loader>
							{/if}
						</div>

						{#if query === ''}
							<slot name="footer"></slot>
						{/if}
					</div>
				{:else}
					<div class="w-full h-full flex justify-center items-center min-h-20">
						<Spinner className="size-5" />
					</div>
				{/if}

				<!-- {#if chats !== null}
					{#if chats.length > 0}
						<div class="w-full">
							<div class="text-left text-sm w-full mb-3 max-h-[22rem] overflow-y-scroll">
								<div class="relative overflow-x-auto">
									<table
										class="w-full text-sm text-left text-gray-600 dark:text-gray-400 table-auto"
									>
										<thead
											class="text-xs text-gray-700 uppercase bg-transparent dark:text-gray-200 border-b-1 border-gray-50 dark:border-gray-850"
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
											{#each chats as chat, idx}
												<tr
													class="bg-transparent {idx !== chats.length - 1 &&
														'border-b'} dark:bg-gray-900 border-gray-50 dark:border-gray-850 text-xs"
												>
													<td class="px-3 py-1 w-2/3">
														<a href="/c/{chat.id}" target="_blank">
															<div class=" hover:underline line-clamp-1">
																{chat.title}
															</div>
														</a>
													</td>

													<td class=" px-3 py-1 hidden md:flex h-[2.5rem]">
														<div class="my-auto">
															{dayjs(chat.created_at * 1000).format('LLL')}
														</div>
													</td>

													<td class="px-3 py-1 text-right">
														<div class="flex justify-end w-full">
															{#if unarchiveHandler}
																<Tooltip content={$i18n.t('Unarchive Chat')}>
																	<button
																		class="self-center w-fit text-sm px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
																		on:click={async () => {
																			unarchiveHandler(chat.id);
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
															{/if}

															<Tooltip content={$i18n.t('Delete Chat')}>
																<button
																	class="self-center w-fit text-sm px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
																	on:click={async () => {
																		deleteHandler(chat.id);
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

							<slot name="footer"></slot>
						</div>
					{:else}
						<div class="text-left text-sm w-full mb-8">
							{emptyPlaceholder || $i18n.t('No chats found.')}
						</div>
					{/if}
				{:else}
					<div class="w-full h-full">
						<Spinner />
					</div>
				{/if} -->
			</div>
		</div>
	</div>
</Modal>
